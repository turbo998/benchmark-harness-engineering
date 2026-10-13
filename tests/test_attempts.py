import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmark_harness.artifacts import Archive, redact
from benchmark_harness.contracts import Result, Status, digest
from benchmark_harness.manifest import build_manifest, read_manifest
from benchmark_harness.runner import LiveBlocked, assert_live_gate, run_mock
from benchmark_harness.samples import template_cases


def test_append_only_resume_preserves_attempts_and_charges(saved_demo: Path) -> None:
    run = saved_demo / "run"
    manifest = read_manifest(run / "manifest.json")
    archive = Archive(run, manifest)
    before = {
        p.relative_to(run): p.read_bytes() for p in (run / "attempts").rglob("*") if p.is_file()
    }
    rows = run_mock(manifest, template_cases(), run)
    after = {
        p.relative_to(run): p.read_bytes() for p in (run / "attempts").rglob("*") if p.is_file()
    }
    assert before == after
    assert len(rows) == 41
    assert any(r.attempt == 2 for r in rows)
    assert any(r.status == Status.TIMEOUT for r in rows)
    with pytest.raises(FileExistsError):
        archive.begin(rows[0].case_id, rows[0].candidate_id, rows[0].repeat, rows[0].attempt)


def test_resume_manifest_and_dataset_drift_refused(saved_demo: Path) -> None:
    run = saved_demo / "run"
    with pytest.raises(ValueError, match="drift"):
        run_mock(build_manifest(template_cases(), repeats=3), template_cases(), run)
    with pytest.raises(ValueError, match="Dataset drift"):
        run_mock(read_manifest(run / "manifest.json"), template_cases(99), run)


def test_partial_attempt_is_preserved_cancelled_not_replayed(workdir: Path) -> None:
    cases = [template_cases()[0]]
    manifest = build_manifest(cases, repeats=1)
    archive = Archive(workdir, manifest)
    path = archive.begin(cases[0].case_id, "mock-reference", 0, 1)
    archive.artifact(path, "partial.txt", "partial original log")
    rows = run_mock(manifest, cases, workdir)
    recovered = next(r for r in rows if r.candidate_id == "mock-reference")
    assert recovered.status == Status.CANCELLED and recovered.attempt == 1
    assert recovered.cost.amount is None
    assert (path / "partial.txt").read_text() == "partial original log"
    assert Archive(workdir, manifest).load()


def test_tampered_evidence_or_result_refused(workdir: Path) -> None:
    rows = run_mock(
        build_manifest([template_cases()[0]], repeats=1), [template_cases()[0]], workdir
    )
    row = rows[0]
    (workdir / row.artifacts[0].path).write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        Archive(workdir, read_manifest(workdir / "manifest.json")).load()


def test_result_failure_reason_identity_and_score_constraints(saved_demo: Path) -> None:
    row = Archive(saved_demo / "run", read_manifest(saved_demo / "run" / "manifest.json")).load()[0]
    with pytest.raises(ValidationError, match="reason"):
        Result.model_validate(row.model_dump() | {"status": "provider_error", "error_reason": None})
    with pytest.raises(ValidationError):
        Result.model_validate(row.model_dump() | {"manifest_hash": ""})
    assert row.manifest_hash == digest(read_manifest(saved_demo / "run" / "manifest.json"))


def test_live_modes_never_silently_succeed(workdir: Path) -> None:
    manifest = build_manifest(template_cases())
    with pytest.raises(LiveBlocked):
        assert_live_gate(
            manifest,
            approved=False,
            reserved=False,
            engine_validated=False,
            isolation_validated=False,
            transparent_accounting=False,
        )
    with pytest.raises(ValidationError):
        build_manifest(template_cases(), mode="live")
    request = json.loads(manifest.model_dump_json())
    assert request["mode"] == "mock"


def test_trace_secret_and_home_redaction() -> None:
    raw = r"Authorization: Bearer abcdef api_key=abcdefgh C:\Users\operator\secret /home/user/log"
    sanitized = redact(raw)
    assert "abcdef" not in sanitized
    assert "operator" not in sanitized and "/home/user" not in sanitized
    assert "[REDACTED]" in sanitized
