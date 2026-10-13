import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmark_harness.contracts import (
    Case,
    Cost,
    Experiment,
    Score,
    Usage,
    canonical,
    digest,
    make_case,
)
from benchmark_harness.manifest import build_manifest, dataset_hash, write_frozen
from benchmark_harness.samples import template_cases


def test_case_identity_order_and_content() -> None:
    cases = template_cases()
    assert dataset_hash(cases) == dataset_hash(list(reversed(cases)))
    assert [c.case_id for c in cases] == [c.case_id for c in template_cases()]
    assert cases[0].case_id != template_cases(43)[0].case_id
    data = cases[0].model_dump()
    with pytest.raises(ValidationError, match="stable ID"):
        Case.model_validate(data | {"prompt": "drift"})
    with pytest.raises(ValidationError):
        Case.model_validate(data | {"case_id": ""})


def test_case_hash_uses_validated_numeric_representation() -> None:
    case = make_case(
        track="api",
        title="Original minimal fixture",
        language="en",
        difficulty="atomic",
        prompt="Return 1",
        seed=0,
        accepted=["1"],
        rejected=["2"],
        assertions=[{"name": "exact", "kind": "exact", "expected": "1", "weight": 1}],
    )
    assert case.assertions[0].weight == 1.0
    assert Case.model_validate_json(case.model_dump_json()) == case


def test_frozen_manifest_drift_and_cohorts(workdir: Path) -> None:
    cases = template_cases()
    manifest = build_manifest(cases)
    azure = build_manifest(cases, profile="azure")
    assert manifest.experiment_id != azure.experiment_id
    assert manifest.environment.cohort != azure.environment.cohort
    path = workdir / "plan.json"
    write_frozen(path, manifest)
    before = path.read_bytes()
    write_frozen(path, manifest)
    assert before == path.read_bytes()
    with pytest.raises(ValueError, match="drift"):
        write_frozen(path, azure)
    with pytest.raises(ValidationError, match="identity"):
        Experiment.model_validate(manifest.model_dump() | {"repeats": 9})


@pytest.mark.parametrize(
    "extra",
    [
        {"mode": "live"},
        {"scorer_version": ""},
        {"engine_versions": {}},
        {"case_ids": ()},
        {"repeats": 0},
        {"budget_usd": "-1"},
    ],
)
def test_invalid_manifest_fields(extra: dict[str, object]) -> None:
    manifest = build_manifest(template_cases()).model_dump(mode="json")
    manifest.update(extra)
    manifest["experiment_id"] = "exp-" + digest(
        {k: v for k, v in manifest.items() if k != "experiment_id"}
    )
    with pytest.raises(ValidationError):
        Experiment.model_validate(manifest)


def test_live_manifest_requires_approval_prices() -> None:
    with pytest.raises(ValidationError, match="approval"):
        build_manifest(template_cases(), mode="live")
    # No inference is implied by a valid contract.
    manifest = build_manifest(
        template_cases(),
        mode="live",
        budget_usd=Decimal("1"),
        approval_id="test-approved",
        price_table_hash="a" * 64,
    )
    assert manifest.mode == "live"


@pytest.mark.parametrize(
    "values",
    [
        {"provenance": "missing"},
        {"provenance": "missing", "amount": "0", "reason": "not reported"},
        {"provenance": "measured", "amount": "1"},
        {"provenance": "estimated", "amount": "1", "price_date": "2026-10-13"},
        {"provenance": "no_charge", "amount": "1", "reason": "claimed free"},
        {"provenance": "synthetic", "amount": "1"},
        {"provenance": "synthetic", "amount": "-1", "reason": "invalid"},
    ],
)
def test_cost_requires_provenance(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Cost.model_validate(values)


def test_decimal_and_unknown_cost() -> None:
    cost = Cost(amount=Decimal("0.000000123"), provenance="synthetic", reason="fixture")
    assert Decimal(json.loads(canonical(cost))["amount"]) == Decimal("0.000000123")
    unknown = Cost(provenance="missing", reason="not reported")
    assert unknown.amount is None
    assert unknown.amount != Decimal(0)


def test_usage_unknown_categories_not_zero() -> None:
    with pytest.raises(ValidationError):
        Usage(provenance="missing")
    with pytest.raises(ValidationError):
        Usage(input_tokens=0, provenance="missing", reason="absent")
    assert Usage(provenance="missing", reason="absent").input_tokens is None


def test_mutated_nested_versions_cannot_be_frozen(workdir: Path) -> None:
    manifest = build_manifest(template_cases())
    manifest.engine_versions["promptfoo"] = "drift"
    with pytest.raises(ValidationError, match="identity"):
        write_frozen(workdir / "invalid.json", manifest)
    assert not (workdir / "invalid.json").exists()


def test_score_bounds_and_pending_review() -> None:
    values = {
        "functional": 1,
        "compliance": 1,
        "rubric": None,
        "composite": None,
        "profile": "author-style-70-15-15-v1",
        "review": "pending",
        "missing_reason": "Independent review not performed",
    }
    pending = Score.model_validate(values)
    assert pending.rubric is None and pending.composite is None
    for patch in ({"functional": 1.1}, {"rubric": 0}, {"composite": 0}, {"missing_reason": None}):
        with pytest.raises(ValidationError):
            Score.model_validate(values | patch)
    reviewed = Score.model_validate(
        values
        | {
            "rubric": 0.5,
            "composite": 0.925,
            "review": "machine_reviewed",
            "reviewer_version": "blind-rubric-v1",
        }
    )
    assert reviewed.review == "machine_reviewed"


def test_schema_files_reconcile_and_serialized_validation() -> None:
    import jsonschema

    root = Path(__file__).resolve().parents[1]
    for name, model, instance in [
        ("case", Case, template_cases()[0]),
        ("experiment", Experiment, build_manifest(template_cases())),
    ]:
        stored = json.loads((root / "schemas" / f"{name}.schema.json").read_bytes())
        assert stored == model.model_json_schema(mode="serialization")
        jsonschema.validate(instance.model_dump(mode="json"), stored)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance.model_dump(mode="json") | {"unapproved": True}, stored)
