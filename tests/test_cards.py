from pathlib import Path

from typer.testing import CliRunner

from benchmark_harness.cards import generate_cards
from benchmark_harness.cli import app


def test_strands_decider_reported_cards_html_is_self_contained_and_anonymized(
    workdir: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "data" / "reported" / "routing-strands-decider" / "report.json"
    out = workdir / "strands-cards.html"
    meta = generate_cards(source, out)
    assert meta["cards"] == 7
    assert meta["provenance"] == "anonymized_reported"
    content = out.read_text(encoding="utf-8")
    assert content.count('class="report-card"') == 7
    assert "1 / 7" in content and "7 / 7" in content
    assert "One call. Three decisions. ~170 ms." in content
    assert "Reverse the options. Same answer." in content
    assert "Ask in batches, not one by one" in content
    assert "<script" not in content
    assert "Henry" not in content


def test_cli_cards_renders_from_saved_demo_run(workdir: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    run_dir = root / "examples" / "mock-report" / "run"
    runner = CliRunner()
    out = workdir / "run-cards.html"
    res = runner.invoke(app, ["cards", str(run_dir), "--output", str(out)])
    assert res.exit_code == 0, res.output
    html_text = out.read_text(encoding="utf-8")
    assert html_text.count('class="report-card"') == 7
    assert "SYNTHETIC" in html_text
    assert "<script" not in html_text


def test_gemini_4_carbon_reported_cards_and_catalog_integrity(workdir: Path) -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    source = root / "data" / "reported" / "gemini-4-carbon" / "report.json"
    out = workdir / "gemini-4-carbon-cards.html"
    meta = generate_cards(source, out)
    assert meta["cards"] == 7
    assert meta["provenance"] == "anonymized_reported"
    content = out.read_text(encoding="utf-8")
    assert content.count('class="report-card"') == 7
    assert "1 / 7" in content and "7 / 7" in content
    assert "Gemini 4 Carbon" in content
    assert "SEC-bench Pro" in content
    assert "0.0%" in content
    assert "<script" not in content

    catalog = json.loads((root / "data" / "reported" / "catalog.json").read_bytes())
    assert catalog["report_families"] == 10
    assert catalog["source_pages"] == 17
    report_ids = [r["report_id"] for r in catalog["reports"]]
    assert "coding-nineteen" in report_ids
    assert "gemini-4-carbon" in report_ids


def test_maf_multi_agent_benchmark_report_and_cards_integrity() -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    report_path = root / "data" / "reported" / "maf-multi-agent-benchmark" / "report.json"
    html_path = root / "examples" / "maf-multi-agent-card-report" / "index.html"
    zh_md = root / "examples" / "maf-multi-agent-card-report" / "test-report.md"
    en_md = root / "examples" / "maf-multi-agent-card-report" / "test-report.en.md"

    assert report_path.is_file()
    assert html_path.is_file()
    assert zh_md.is_file()
    assert en_md.is_file()

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_data["schema_version"] == 1
    assert report_data["report_id"] == "maf-multi-agent-benchmark"
    assert report_data["provenance"] == "measured"
    assert report_data["independently_reproduced"] is True
    assert report_data["facts"]["scenarios_tested"] == 7
    assert report_data["facts"]["decisions_tested"] == 12
    assert len(report_data["facts"]["framework_cohort"]) == 6
    assert len(report_data["facts"]["scenarios"]) == 12
    assert len(report_data["facts"]["robustness_reversal"]) == 6
    assert len(report_data["facts"]["batch_latency"]) == 4

    html_content = html_path.read_text(encoding="utf-8")
    assert "1 / 7" in html_content and "7 / 7" in html_content
    assert "Content-Security-Policy" in html_content
    assert "<script" not in html_content
