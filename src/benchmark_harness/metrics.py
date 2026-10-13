"""Shared metrics; partial quality means remain descriptive, never comparative."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from benchmark_harness.contracts import Case, Experiment, Result, Status
from benchmark_harness.statistics import clustered_interval, matched_comparison, pareto_frontier


def latest_attempts(results: list[Result]) -> dict[tuple[str, str, int], Result]:
    latest: dict[tuple[str, str, int], Result] = {}
    for row in results:
        key = (row.case_id, row.candidate_id, row.repeat)
        if key not in latest or row.attempt > latest[key].attempt:
            latest[key] = row
    return latest


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def summarize(manifest: Experiment, cases: list[Case], results: list[Result]) -> dict[str, Any]:
    latest = latest_attempts(results)
    points: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    pairs: dict[tuple[str, str], dict[tuple[str, int], float | None]] = {}
    for candidate in manifest.candidates:
        for track in ("api", "coding"):
            tasks = [c for c in cases if c.track == track]
            if not tasks:
                continue
            ids = {c.case_id for c in tasks}
            cells = [
                latest.get((case.case_id, candidate.candidate_id, repeat))
                for case in tasks
                for repeat in range(manifest.repeats)
            ]
            present = [r for r in cells if r is not None]
            attempts = [
                r for r in results if r.candidate_id == candidate.candidate_id and r.case_id in ids
            ]
            all_costs = [r.cost.amount for r in attempts if r.cost.amount is not None]
            known_sum = sum(all_costs, start=Decimal(0))
            missing_cost = sum(r.cost.amount is None for r in attempts)
            reasons = sorted(
                {
                    r.cost.reason
                    for r in attempts
                    if r.cost.amount is None and r.cost.reason is not None
                }
            )
            functional_by_task: dict[str, list[float]] = defaultdict(list)
            quality_by_task: dict[str, list[float]] = defaultdict(list)
            paired: dict[tuple[str, int], float | None] = {}
            breakdown: dict[str, list[float]] = defaultdict(list)
            difficulty: dict[str, list[float]] = defaultdict(list)
            assertion_passes = 0
            assertion_total = 0
            assertion_weight_passed = 0.0
            assertion_weight_total = 0.0
            for case in tasks:
                for repeat in range(manifest.repeats):
                    row = latest.get((case.case_id, candidate.candidate_id, repeat))
                    functional = row.score.functional if row else 0.0
                    if functional is not None:
                        functional_by_task[case.case_id].append(functional)
                        difficulty[case.difficulty].append(functional)
                    quality = (
                        row.score.composite
                        if row and row.score.review != "pending"
                        else (0.0 if row is None else None)
                    )
                    paired[(case.case_id, repeat)] = quality
                    if quality is not None:
                        quality_by_task[case.case_id].append(quality)
                    if row:
                        for key in ("functional", "compliance", "rubric"):
                            value = getattr(row.score, key)
                            if value is not None:
                                breakdown[key].append(value)
                        outcomes = row.score.assertions
                        assertion_passes += sum(a.passed for a in outcomes)
                        assertion_total += len(outcomes)
                        assertion_weight_passed += sum(a.weight for a in outcomes if a.passed)
                        assertion_weight_total += sum(a.weight for a in outcomes)
                    else:
                        assertion_total += len(case.assertions) or 1
                        assertion_weight_total += sum(a.weight for a in case.assertions) or 1
            planned = len(cells)
            successes = sum(r.status == Status.PASSED for r in present)
            p95_reason = "Fixture/pilot pack: p95 and ranking are not reported"
            task_pass_any = [
                any(
                    latest.get((c.case_id, candidate.candidate_id, r)) is not None
                    and latest[(c.case_id, candidate.candidate_id, r)].status == Status.PASSED
                    for r in range(manifest.repeats)
                )
                for c in tasks
            ]
            metric = "api_ms" if track == "api" else "agent_ms"
            latencies = [
                getattr(r.timing, metric) for r in present if getattr(r.timing, metric) is not None
            ]
            point_id = f"{manifest.environment.cohort}:{track}:{candidate.candidate_id}"
            quality = _mean([statistics.mean(v) for v in quality_by_task.values()])
            quality_missing_trials = sum(
                r is not None and (r.score.composite is None or r.score.review == "pending")
                for r in cells
            )
            point = {
                "point_id": point_id,
                "candidate_id": candidate.candidate_id,
                "track": track,
                "cohort": manifest.environment.cohort,
                "profile": manifest.environment.profile,
                "data_status": sorted({r.data_status for r in attempts}),
                "planned": planned,
                "attempted_trials": len(present),
                "total_attempts": len(attempts),
                "missing_trials": planned - len(present),
                "statuses": {s.value: sum(r.status == s for r in present) for s in Status},
                "attempt_statuses": dict(Counter(r.status.value for r in attempts)),
                "successes": successes,
                "success_rate_planned": successes / planned,
                "macro_functional": _mean(
                    [statistics.mean(v) for v in functional_by_task.values()]
                ),
                "quality": quality,
                "quality_missing_trials": quality_missing_trials,
                "quality_coverage": "partial reviewed mean; excluded from comparison"
                if quality_missing_trials
                else "complete planned quality population",
                "comparative_quality": quality if not quality_missing_trials else None,
                "review_pending": sum(r.score.review == "pending" for r in present),
                "micro_assertion_rate": assertion_passes / assertion_total
                if assertion_total
                else None,
                "micro_weighted_assertion_rate": assertion_weight_passed / assertion_weight_total
                if assertion_weight_total
                else None,
                "assertions_passed": assertion_passes,
                "assertions_planned": assertion_total,
                "pass_at_k": statistics.mean(task_pass_any),
                "k": manifest.repeats,
                "latency_ms": _mean(latencies),
                "latency_metric": metric,
                "latency_observed": len(latencies),
                "latency_missing": planned - len(latencies),
                "phase_means_ms": {
                    phase: _mean(
                        [
                            getattr(r.timing, phase)
                            for r in present
                            if getattr(r.timing, phase) is not None
                        ]
                    )
                    for phase in (
                        "setup_ms",
                        "api_ms",
                        "ttft_ms",
                        "routing_ms",
                        "agent_ms",
                        "verification_ms",
                        "teardown_ms",
                        "wall_ms",
                    )
                },
                "cost_usd": str(known_sum) if not missing_cost and attempts else None,
                "known_cost_usd": str(known_sum),
                "missing_cost_attempts": missing_cost,
                "cost_missing_reasons": reasons,
                "cost_scopes": sorted({r.cost.scope for r in attempts}),
                "cost_provenance": sorted({r.cost.provenance for r in attempts}),
                "cost_reason": "All attempts including retries; null if any charge is unknown. "
                "Does not include unrecorded infrastructure/generator/grader charges.",
                "p95_ms": None,
                "p95_reason": p95_reason,
                "uncertainty": clustered_interval(quality_by_task, seed=manifest.order_seed),
                "difficulty": {k: _mean(v) for k, v in sorted(difficulty.items())},
                "functional_distribution": [x for v in functional_by_task.values() for x in v],
                "breakdown": {k: _mean(v) for k, v in sorted(breakdown.items())},
                "evidence": [r.artifacts[0].path for r in attempts],
            }
            points.append(point)
            pairs[(track, candidate.candidate_id)] = paired
    for track in ("api", "coding"):
        names = [c.candidate_id for c in manifest.candidates if (track, c.candidate_id) in pairs]
        for i, left in enumerate(names):
            for right in names[i + 1 :]:
                comparisons.append(
                    {
                        "cohort": manifest.environment.cohort,
                        "track": track,
                        "left": left,
                        "right": right,
                        **matched_comparison(
                            pairs[(track, left)], pairs[(track, right)], seed=manifest.order_seed
                        ),
                    }
                )
    frontier: dict[str, list[str]] = {}
    for track in ("api", "coding"):
        frontier[track] = pareto_frontier(
            [
                {
                    "point_id": p["point_id"],
                    "cost_usd": Decimal(p["cost_usd"]) if p["cost_usd"] else None,
                    "quality": p["comparative_quality"],
                }
                for p in points
                if p["track"] == track
            ]
        )
    return {
        "schema_version": "1",
        "experiment_id": manifest.experiment_id,
        "cohort": manifest.environment.cohort,
        "score_profile": manifest.score_profile,
        "label": "SYNTHETIC engineering fixtures — not measured model performance or a ranking"
        if manifest.mode == "mock"
        else "Measured pilot; review provenance and readiness",
        "actual_inference_charges_usd": "0" if manifest.mode == "mock" else None,
        "planned_trials": len(manifest.case_ids) * len(manifest.candidates) * manifest.repeats,
        "attempted_trials": len(latest),
        "total_attempts": len(results),
        "points": points,
        "pareto_by_track": frontier,
        "matched_comparisons": comparisons,
        "semantics": {
            "denominator": "All planned case/candidate/repeat cells; missing/error cells remain in denominators",
            "quality": "Macro task mean; missing independent review excluded explicitly, not assigned zero. "
            "Partial reviewed means are descriptive only; comparative scatters/Pareto require complete review coverage.",
            "micro": "Assertion passes / planned assertions, including error and missing cells",
            "cost": "Known subtotal is not total cost; missing charges remain null; retry charges included",
            "latency": "Track-specific mean of observed final attempts; failures and phase missing counts retained",
            "cohorts": "Never pool local/Azure, OS/region/cache/warmup/image or API/agent latency cohorts",
            "uncertainty": "Task-cluster bootstrap; repeats matched by task and repeat; small packs have no interval",
        },
    }
