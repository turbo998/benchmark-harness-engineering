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
