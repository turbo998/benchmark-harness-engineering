from pathlib import Path

import pytest

from benchmark_harness.contracts import make_case
from benchmark_harness.samples import (
    accept_cases,
    export_coding,
    template_cases,
    trusted_fixture_check,
    write_dataset,
)
from benchmark_harness.scoring import score_api


def test_original_acceptance_and_negative_variants(workdir: Path) -> None:
    cases = template_cases()
    acceptance = accept_cases(cases, workdir)
    assert len(acceptance["accepted"]) == 9
    assert acceptance["rejected"] == []
    assert acceptance["sandbox_tier"] == "unvalidated"
    for case in cases:
        if case.track == "api":
            assert all(score_api(case, x).functional == 1 for x in case.accepted)
            assert all(score_api(case, x).functional != 1 for x in case.rejected)


def test_seed_language_difficulty_and_no_network_generation() -> None:
    cases = template_cases()
    assert {c.language for c in cases if c.track == "api"} == {"en", "zh"}
    assert {c.difficulty for c in cases if c.track == "coding"} == {"atomic", "medium", "complex"}
    assert cases == template_cases()


def test_independent_verifier_not_exported_to_visible_tree(workdir: Path) -> None:
    export_coding(template_cases(), workdir)
    for difficulty in ("atomic", "medium", "complex"):
        visible = workdir / difficulty / "agent-visible"
        assert sorted(p.name for p in visible.iterdir()) == ["instruction.md", "solution.py"]
        assert (visible / "solution.py").read_text() == ""
        assert (workdir / difficulty / "trusted-verifier" / "verify.py").exists()
        assert "VERIFIER_PASS" not in (visible / "instruction.md").read_text()


def test_reject_a_case_with_bad_oracle(workdir: Path) -> None:
    data = template_cases()[0].model_dump(mode="json", exclude={"case_id"})
    invalid = make_case(**(data | {"accepted": ["wrong"]}))
    report = accept_cases([invalid], workdir)
    assert report["accepted"] == []
    assert "Reference" in report["rejected"][0]["reason"]


def test_no_arbitrary_dataset_code_executed_on_host(workdir: Path) -> None:
    case = next(c for c in template_cases() if c.coding)
    assert case.coding
    with pytest.raises(ValueError, match="Host acceptance"):
        trusted_fixture_check(case, "raise SystemExit(0)", workdir)
    assert not (workdir / "solution.py").exists()


def test_dataset_write_is_frozen(workdir: Path) -> None:
    path = workdir / "cases.jsonl"
    write_dataset(path, template_cases())
    before = path.read_bytes()
    write_dataset(path, template_cases())
    assert before == path.read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        write_dataset(path, template_cases(99))
