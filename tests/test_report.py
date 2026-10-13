import csv
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from benchmark_harness.artifacts import Archive
from benchmark_harness.contracts import Cost, Result, Score, Status
from benchmark_harness.manifest import build_manifest, read_cases, read_manifest
from benchmark_harness.metrics import summarize
from benchmark_harness.report import FIGURES, _figures, _html, generate_report, rescore_saved
from benchmark_harness.runner import run_mock
from benchmark_harness.samples import template_cases


def test_exact_golden_summary_denominators_retry_costs_and_frontier(saved_demo: Path) -> None:
    summary = json.loads((saved_demo / "report" / "summary.json").read_bytes())
    golden = json.loads(
        (Path(__file__).parent / "fixtures" / "mock-summary-golden.json").read_bytes()
    )
    for field in ("planned_trials", "attempted_trials", "total_attempts"):
        assert summary[field] == golden[field]
    for actual, expected in zip(summary["points"], golden["points"], strict=True):
        assert {k: actual[k] for k in expected} == expected
        assert actual["p95_ms"] is None
        assert actual["uncertainty"]["low"] is None
        assert actual["latency_metric"] == ("api_ms" if actual["track"] == "api" else "agent_ms")
    for track, frontier in summary["pareto_by_track"].items():
        assert len(frontier) == 1 and frontier[0].endswith(f":{track}:mock-reference")


def test_offline_html_evidence_and_static_formats(saved_demo: Path) -> None:
    report = saved_demo / "report"
    html = (report / "index.html").read_text(encoding="utf-8")
    assert "SYNTHETIC" in html and "not measured model performance" in html
    assert html.count('src="data:image/svg+xml;base64,') == 5
    assert "<script" not in html
    assert "known_cost_usd" in html and "unknown / pending" in html
    for target in re.findall(r'<a href="([^"]+)"', html):
        assert (report / target).is_file()
    for name in FIGURES:
        assert (report / f"{name}.png").read_bytes().startswith(b"\x89PNG")
        assert b"<svg" in (report / f"{name}.svg").read_bytes()
    with (report / "summary.csv").open(encoding="utf-8", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    points = json.loads((report / "summary.json").read_bytes())["points"]
    for row, point in zip(csv_rows, points, strict=True):
        assert int(row["planned"]) == point["planned"]
        assert float(row["quality"]) == point["quality"]
        assert row["quality_coverage"] == point["quality_coverage"]
        assert row["comparative_quality"] == (
            str(point["comparative_quality"]) if point["comparative_quality"] is not None else ""
        )
        assert row["cost_usd"] == (point["cost_usd"] or "")


def test_regeneration_from_saved_results_exact_and_scores_unchanged(
    saved_demo: Path, workdir: Path
) -> None:
    run = saved_demo / "run"
    before = (saved_demo / "report" / "summary.json").read_bytes()
    generate_report(run, workdir / "report")
    assert before == (workdir / "report" / "summary.json").read_bytes()
    for name in FIGURES:
        assert (saved_demo / "report" / f"{name}.svg").read_bytes() == (
            workdir / "report" / f"{name}.svg"
        ).read_bytes()
    rescored = rescore_saved(run, workdir / "scores.json")
    archived = Archive(run, read_manifest(run / "manifest.json")).load()
    assert [r.score for r in rescored] == [r.score for r in archived]
    assert json.loads((workdir / "scores.json").read_bytes()) == [
        r.model_dump(mode="json") for r in rescored
    ]


def test_pending_reviews_excluded_not_ranked_as_zero(workdir: Path) -> None:
    cases = [template_cases()[0]]
    manifest = build_manifest(cases, repeats=1, score_profile="author-style-70-15-15-v1")
    results = run_mock(manifest, cases, workdir)
    summary = summarize(manifest, cases, results)
    point = next(p for p in summary["points"] if p["candidate_id"] == "mock-reference")
    assert point["quality"] is None and point["macro_functional"] == 1
    assert point["review_pending"] == 1 and point["quality_missing_trials"] == 1
    assert point["success_rate_planned"] == 0 and point["statuses"]["review_pending"] == 1
    assert summary["pareto_by_track"]["api"] == []


def test_partial_easy_review_cannot_compete_with_full_easy_hard_population(workdir: Path) -> None:
    templates = template_cases()
    cases = [templates[0], templates[4]]
    hard_id = cases[1].case_id
    manifest = build_manifest(
        cases,
        repeats=1,
        max_attempts=1,
        score_profile="author-style-70-15-15-v1",
    )
    graded: list[Result] = []
    for row in run_mock(manifest, cases, workdir / "run"):
        partial_candidate = row.candidate_id == "mock-reference"
        pending = partial_candidate and row.case_id == hard_id
        component = 1.0 if partial_candidate else 0.8
        score = Score(
            functional=component,
            compliance=component,
            rubric=None if pending else component,
            composite=None if pending else component,
            profile=manifest.score_profile,
            review="pending" if pending else "machine_reviewed",
            reviewer_version=None if pending else "synthetic-review-fixture-v1",
            missing_reason="Hard task not reviewed" if pending else None,
        )
        status = (
            Status.REVIEW_PENDING
            if pending
            else (Status.PASSED if component == 1 else Status.FAILED)
        )
        graded.append(
            Result.model_validate(
                row.model_dump()
                | {
                    "status": status,
                    "score": score,
                    "error_reason": "Synthetic partial correctness"
                    if status == Status.FAILED
                    else None,
                    "cost": Cost(
                        amount=Decimal(".01") if partial_candidate else Decimal(".02"),
                        provenance="synthetic",
                        reason="Comparative coverage regression fixture",
                    ),
                }
            )
        )
    summary = summarize(manifest, cases, graded)
    partial = next(p for p in summary["points"] if p["candidate_id"] == "mock-reference")
    complete = next(p for p in summary["points"] if p["candidate_id"] == "mock-challenger")
    assert partial["quality"] == 1 and partial["quality_missing_trials"] == 1
    assert partial["comparative_quality"] is None
    assert partial["quality_coverage"] == "partial reviewed mean; excluded from comparison"
    assert complete["quality"] == 0.8 and complete["comparative_quality"] == 0.8
    assert complete["quality_missing_trials"] == 0
    assert summary["pareto_by_track"]["api"] == [complete["point_id"]]
    charts = workdir / "charts"
    charts.mkdir()
    embedded = _figures(summary, charts)
    for name in ("cost-quality", "latency-quality"):
        svg = (charts / f"{name}.svg").read_text(encoding="utf-8")
        assert partial["candidate_id"] not in svg
        assert complete["candidate_id"] in svg
    assert partial["quality_coverage"] in _html(summary, embedded)


def test_unattempted_and_errors_stay_in_planned_denominators() -> None:
    cases = template_cases()
    manifest = build_manifest(cases)
    summary = summarize(manifest, cases, [])
    assert summary["planned_trials"] == 36 and summary["attempted_trials"] == 0
    for point in summary["points"]:
        assert point["macro_functional"] == 0
        assert point["success_rate_planned"] == 0
        assert point["missing_trials"] == point["planned"]
        assert point["cost_usd"] is None
        assert point["micro_assertion_rate"] == 0


def test_result_jsonschema_and_no_measurement_forgery(saved_demo: Path) -> None:
    import jsonschema

    run = saved_demo / "run"
    result = Archive(run, read_manifest(run / "manifest.json")).load()[0]
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "result.schema.json").read_bytes())
    assert schema == Result.model_json_schema(mode="serialization")
    jsonschema.validate(result.model_dump(mode="json"), schema)
    with pytest.raises(ValueError, match="Synthetic"):
        Result.model_validate(
            result.model_dump()
            | {"timing": result.timing.model_dump() | {"provenance": "measured"}}
        )


def test_report_dataset_hash_is_checked(saved_demo: Path) -> None:
    run = saved_demo / "run"
    cases = read_cases(run / "dataset.jsonl")
    assert len(cases) == 9
