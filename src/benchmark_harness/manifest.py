"""Content-addressed datasets and immutable experiment locks."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from benchmark_harness.contracts import Candidate, Case, Environment, Experiment, canonical, digest

ENGINE_VERSIONS = {"promptfoo": "0.124.0", "harbor": "0.24.0", "harness": "0.1.0"}
SCORER_VERSION = "deterministic-v1"


def read_cases(path: Path) -> list[Case]:
    cases = [
        Case.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise ValueError("Dataset must be nonempty and have unique case IDs")
    return cases


def dataset_hash(cases: list[Case]) -> str:
    cases = [Case.model_validate_json(canonical(case)) for case in cases]
    return digest([c.model_dump(mode="json") for c in sorted(cases, key=lambda c: c.case_id)])


def build_manifest(
    cases: list[Case],
    *,
    repeats: int = 2,
    seed: int = 42,
    profile: str = "local",
    score_profile: str = "deterministic-v1",
    mode: str = "mock",
    candidates: list[Candidate] | None = None,
    max_attempts: int = 2,
    budget_usd: Decimal = Decimal(0),
    approval_id: str | None = None,
    price_table_hash: str | None = None,
    environment: Environment | None = None,
) -> Experiment:
    candidate_rows = candidates or [
        Candidate(
            candidate_id=name,
            provider="mock",
            model=name,
            resolved_version="fixture-v1",
            prompt_hash=digest("original-mock-prompt-v1"),
            scaffold_version="mock-v1",
            agent_version="mock-v1",
        )
        for name in ("mock-reference", "mock-challenger")
    ]
    values: dict[str, Any] = {
        "schema_version": "1",
        "dataset_hash": dataset_hash(cases),
        "dataset_revision": "original-fixtures-v1",
        "case_ids": tuple(sorted(c.case_id for c in cases)),
        "split": "fixture",
        "generator_version": "original-template-v1",
        "candidates": candidate_rows,
        "environment": environment
        or Environment.model_validate(
            {
                "profile": profile,
                "os": "synthetic-linux",
                "region": "synthetic",
                "image_digest": "sha256:" + digest("mock-image-not-a-real-container"),
                "cache_policy": "disabled",
                "warmup": "synthetic",
            }
        ),
        "engine_versions": ENGINE_VERSIONS,
        "scorer_version": SCORER_VERSION,
        "score_profile": score_profile,
        "repeats": repeats,
        "order_seed": seed,
        "mode": mode,
        "retry_owner": "harness",
        "max_attempts": max_attempts,
        "budget_usd": budget_usd,
        "approval_id": approval_id,
        "price_table_hash": price_table_hash,
    }
    values_json = json.loads(
        canonical(
            {
                **values,
                "budget_usd": str(budget_usd),
                "candidates": [c.model_dump(mode="json") for c in candidate_rows],
                "environment": values["environment"].model_dump(mode="json"),
            }
        )
    )
    return Experiment.model_validate(values_json | {"experiment_id": "exp-" + digest(values_json)})


def write_frozen(path: Path, manifest: Experiment) -> None:
    manifest = Experiment.model_validate_json(canonical(manifest))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical(manifest) + b"\n"
    try:
        with path.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        existing = Experiment.model_validate_json(path.read_bytes())
        if canonical(existing) != canonical(manifest):
            raise ValueError("Immutable manifest exists with configuration drift") from None


def read_manifest(path: Path) -> Experiment:
    return Experiment.model_validate_json(path.read_bytes())


def verify_dataset(manifest: Experiment, cases: list[Case]) -> None:
    if dataset_hash(cases) != manifest.dataset_hash or tuple(sorted(c.case_id for c in cases)) != (
        manifest.case_ids
    ):
        raise ValueError("Dataset drift: create a new experiment, do not resume")
