"""No-cost mock execution and conservative gates for unsupported live tiers."""

from __future__ import annotations

import json
import random
import shutil
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from benchmark_harness.artifacts import Archive
from benchmark_harness.contracts import (
    AssertionOutcome,
    Candidate,
    Case,
    Cost,
    Experiment,
    PhaseTiming,
    Result,
    Status,
    Usage,
    digest,
)
from benchmark_harness.manifest import verify_dataset
from benchmark_harness.samples import accept_cases, trusted_fixture_check, write_dataset
from benchmark_harness.scoring import make_score, score_api, unattempted_score

RETRYABLE = {Status.PROVIDER_ERROR, Status.INFRASTRUCTURE_ERROR, Status.TIMEOUT}
ERRORS = [
    Status.PROVIDER_ERROR,
    Status.QUOTA_ERROR,
    Status.AUTH_ERROR,
    Status.TIMEOUT,
    Status.INFRASTRUCTURE_ERROR,
    Status.CANCELLED,
]


class LiveBlocked(RuntimeError):
    pass


def assert_live_gate(
    manifest: Experiment,
    *,
    approved: bool,
    reserved: bool,
    engine_validated: bool,
    isolation_validated: bool,
    transparent_accounting: bool,
) -> None:
    if manifest.mode != "live" or not approved or not manifest.approval_id:
        raise LiveBlocked("Live execution requires an explicit approved live manifest")
    if not manifest.price_table_hash or not reserved or not transparent_accounting:
        raise LiveBlocked("Dated prices and enforceable pre-reserved accounting required")
    if not engine_validated or not isolation_validated:
        raise LiveBlocked("Live engine/sandbox compatibility has not been validated")


def planned_trials(manifest: Experiment) -> list[tuple[str, Candidate, int]]:
    rows = [
        (case_id, candidate, repeat)
        for case_id in manifest.case_ids
        for repeat in range(manifest.repeats)
        for candidate in manifest.candidates
    ]
    random.Random(manifest.order_seed).shuffle(rows)
    return rows


def _timing(index: int, track: str) -> PhaseTiming:
    latency = float(80 + index * 13)
    started_at = datetime(2026, 10, 13, tzinfo=UTC)
    return PhaseTiming(
        setup_ms=10,
        api_ms=latency if track == "api" else None,
        agent_ms=latency if track == "coding" else None,
        verification_ms=5,
        teardown_ms=2,
        wall_ms=latency + 17,
        started_at=started_at,
        finished_at=started_at + timedelta(milliseconds=latency + 17),
        provenance="synthetic",
        missing_reason="TTFT/routing and the other track's phase are not simulated",
    )


def _mock_response(case: Case, good: bool) -> Any:
    if case.coding is not None:
        return case.coding.reference if good else case.coding.negatives[0]
    return case.accepted[0] if good else case.rejected[0]


def _attempt(
    archive: Archive,
    case: Case,
    candidate: Candidate,
    repeat: int,
    attempt: int,
    index: int,
    scratch: Path,
) -> Result:
    manifest = archive.manifest
    path = archive.begin(case.case_id, candidate.candidate_id, repeat, attempt)
    reference = candidate.candidate_id == "mock-reference"
    selector = (index + repeat) % 10
    status = Status.PASSED
    if not reference and selector < len(ERRORS) and attempt == 1:
        status = ERRORS[selector]
    good = reference or selector % 3 == 0 or attempt > 1
    response = _mock_response(case, good)
    archive.event(path, "dispatched", {"engine": "mock", "paid_call": False})
    response_artifact = archive.artifact(
        path, "response.json", json.dumps(response, ensure_ascii=False, sort_keys=True)
    )
    artifacts = [response_artifact]
    if status in ERRORS:
        score = unattempted_score(
            case, profile=manifest.score_profile, reason=f"Simulated {status}"
        )
    elif case.track == "api":
        score = score_api(case, response, profile=manifest.score_profile)
    else:
        passed = trusted_fixture_check(
            case, str(response), scratch / digest([case.case_id, attempt, good])[:16]
        )
        score = make_score(
            (
                AssertionOutcome(
                    name="independent-verifier",
                    category="functional",
                    weight=1.0,
                    passed=passed,
                ),
            ),
            profile=manifest.score_profile,
        )
        if case.coding is None:
            raise ValueError("Missing verifier")
        artifacts.append(
            archive.artifact(
                path,
                "verification.json",
                json.dumps(
                    {
                        "passed": passed,
                        "verifier_hash": case.coding.verifier_hash,
                        "response_artifact_hash": response_artifact.sha256,
                        "source": "trusted-original-fixture-host-check",
                        "sandbox_tier": "unvalidated",
                    },
                    sort_keys=True,
                ),
            )
        )
    if status == Status.PASSED:
        status = Status.PASSED if score.functional == 1 else Status.FAILED
        if score.composite is None:
            status = Status.REVIEW_PENDING
    missing_cost = not reference and selector == 4
    cost = Cost(
        amount=None if missing_cost else Decimal(index + 1) / Decimal(10000),
        provenance="missing" if missing_cost else "synthetic",
        reason="Simulated opaque/missing usage"
        if missing_cost
        else "Synthetic chart dollars; actual workflow has no inference charges",
    )
    usage = Usage(
        input_tokens=40 + index,
        cache_read_tokens=0,
        cache_write_tokens=0,
        output_tokens=10 + index,
        reasoning_tokens=0,
        provenance="synthetic",
    )
    result = Result(
        experiment_id=manifest.experiment_id,
        manifest_hash=digest(manifest),
        case_id=case.case_id,
        candidate_id=candidate.candidate_id,
        cohort=manifest.environment.cohort,
        track=case.track,
        difficulty=case.difficulty,
        repeat=repeat,
        attempt=attempt,
        trace_id=digest(
            [manifest.experiment_id, case.case_id, candidate.candidate_id, repeat, attempt]
        ),
        status=status,
        error_reason=None
        if status in {Status.PASSED, Status.REVIEW_PENDING}
        else f"Simulated {status}",
        data_status="synthetic",
        usage=usage,
        cost=cost,
        timing=_timing(index, case.track),
        score=score,
        artifacts=tuple(artifacts),
    )
    archive.complete(path, result)
    return result


def _recover_partial(archive: Archive, cases: dict[str, Case]) -> None:
    for path in archive.incomplete():
        request = json.loads((path / "request.json").read_bytes())
        manifest = archive.manifest
        if request["manifest_hash"] != digest(manifest):
            raise ValueError("Incomplete request manifest drift")
        case = cases[request["case_id"]]
        artifact = archive.artifact(
            path, "recovery.txt", "Cancelled after interrupted mock attempt"
        )
        result = Result(
            experiment_id=manifest.experiment_id,
            manifest_hash=digest(manifest),
            case_id=case.case_id,
            candidate_id=request["candidate_id"],
            cohort=manifest.environment.cohort,
            track=case.track,
            difficulty=case.difficulty,
            repeat=request["repeat"],
            attempt=request["attempt"],
            trace_id=digest(request),
            status=Status.CANCELLED,
            error_reason="Interrupted attempt retained; no automatic replay",
            data_status="synthetic",
            usage=Usage(provenance="missing", reason="Interrupted"),
            cost=Cost(provenance="missing", reason="Interrupted mock attempt; no paid dispatch"),
            timing=_timing(0, case.track),
            score=unattempted_score(case, profile=manifest.score_profile, reason="Interrupted"),
            artifacts=(artifact,),
        )
        archive.complete(path, result)


def run_mock(manifest: Experiment, cases: list[Case], output: Path) -> list[Result]:
    if manifest.mode != "mock":
        raise LiveBlocked("run_mock cannot execute live manifests")
    if any(c.provider != "mock" for c in manifest.candidates):
        raise LiveBlocked("Mock execution only supports explicitly mock candidates")
    verify_dataset(manifest, cases)
    archive = Archive(output, manifest)
    write_dataset(output / "dataset.jsonl", cases)
    scratch = output / ".fixture-work"
    try:
        acceptance = accept_cases(cases, scratch / "acceptance")
        if acceptance["rejected"]:
            raise ValueError("Invalid sample acceptance; no experiment scheduled")
        by_id = {c.case_id: c for c in cases}
        _recover_partial(archive, by_id)
        rows = archive.load()
        latest: dict[tuple[str, str, int], Result] = {}
        for row in rows:
            key = (row.case_id, row.candidate_id, row.repeat)
            if key not in latest or row.attempt > latest[key].attempt:
                latest[key] = row
        indices = {case_id: i for i, case_id in enumerate(manifest.case_ids)}
        for case_id, candidate, repeat in planned_trials(manifest):
            key = (case_id, candidate.candidate_id, repeat)
            previous = latest.get(key)
            if previous and (
                previous.status not in RETRYABLE or previous.attempt >= manifest.max_attempts
            ):
                continue
            start = previous.attempt + 1 if previous else 1
            for attempt in range(start, manifest.max_attempts + 1):
                row = _attempt(
                    archive,
                    by_id[case_id],
                    candidate,
                    repeat,
                    attempt,
                    indices[case_id],
                    scratch / "candidate",
                )
                if row.status not in RETRYABLE:
                    break
        return archive.load()
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
