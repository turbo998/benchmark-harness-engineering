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
    assert catalog["report_families"] == 12
    assert catalog["source_pages"] == 21
    report_ids = [r["report_id"] for r in catalog["reports"]]
    assert "coding-nineteen" in report_ids
    assert "gemini-4-carbon" in report_ids
    assert "routing-aipc-kev-sft" in report_ids
    assert "moe-mi300x-bf16-mxfp4" in report_ids


def test_aipc_kev_sft_and_moe_mi300x_reported_cards_and_bilingual_docs(
    workdir: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    for report_id, html_rel, expected_phrase in [
        (
            "routing-aipc-kev-sft",
            Path("examples") / "aipc-kev-sft-card-report" / "index.html",
            "Q8_0 GGUF",
        ),
        (
            "moe-mi300x-bf16-mxfp4",
            Path("examples") / "moe-mi300x-card-report" / "index.html",
            "MI300X",
        ),
    ]:
        source = root / "data" / "reported" / report_id / "report.json"
        out = workdir / f"{report_id}-cards.html"
        meta = generate_cards(source, out)
        assert meta["cards"] == 7
        assert meta["provenance"] == "anonymized_reported"
        content = out.read_text(encoding="utf-8")
        assert content.count('class="report-card"') == 7
        assert "1 / 7" in content and "7 / 7" in content
        assert expected_phrase in content
        assert "<script" not in content
        assert (root / html_rel).is_file()
        assert (root / "docs" / "reports" / f"{report_id}.md").is_file()
        assert (root / "docs" / "reports" / f"{report_id}.en.md").is_file()


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


def test_gpt_6_2_sol_benchmark_report_and_cards_integrity(workdir: Path) -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "reported" / "gpt-6-2-sol-benchmark"
    report_path = data_dir / "report.json"
    zh_report_path = data_dir / "report.zh-CN.json"
    en_html_path = root / "examples" / "gpt-6-2-sol-card-report" / "index.html"
    zh_html_path = root / "examples" / "gpt-6-2-sol-card-report" / "index.zh-CN.html"
    ex_readme_zh = root / "examples" / "gpt-6-2-sol-card-report" / "README.md"
    ex_readme_en = root / "examples" / "gpt-6-2-sol-card-report" / "README.en.md"
    doc_zh = root / "docs" / "reports" / "gpt-6-2-sol-benchmark.md"
    doc_en = root / "docs" / "reports" / "gpt-6-2-sol-benchmark.en.md"
    svg_zh = root / "docs" / "reports" / "assets" / "gpt-6-2-sol-overview.svg"
    svg_en = root / "docs" / "reports" / "assets" / "gpt-6-2-sol-overview.en.svg"

    expected_files = [
        report_path,
        zh_report_path,
        data_dir / "freeze_manifest.json",
        data_dir / "live_capi_telemetry.csv",
        data_dir / "live_coding_effort_sweep.csv",
        data_dir / "live_routing_and_perturbation.csv",
        data_dir / "live_batch_latency.csv",
        data_dir / "external_benchmark_matrix.csv",
        en_html_path,
        zh_html_path,
        ex_readme_zh,
        ex_readme_en,
        doc_zh,
        doc_en,
        svg_zh,
        svg_en,
    ]
    for path in expected_files:
        assert path.is_file(), f"Missing expected artifact: {path}"

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_data["schema_version"] == 1
    assert report_data["report_id"] == "gpt-6-2-sol-benchmark"
    assert report_data["provenance"] == "measured"
    assert report_data["independently_reproduced"] is True
    assert report_data["cards"][6]["dark_box"]["repo"].endswith(
        "data/reported/gpt-6-2-sol-benchmark"
    )

    facts = report_data["facts"]
    assert facts["live_capi_trials"] == 27
    assert facts["coding_assertions_passed"] == 59
    assert facts["coding_assertions_total"] == 60
    assert facts["routing_assertions_passed_sol62"] == 12
    assert facts["routing_assertions_passed_sol61"] == 10
    assert facts["routing_assertions_total"] == 12
    assert facts["choice_questions_reversal_stable"] == 6
    assert facts["choice_questions_total"] == 6

    regenerated_out = workdir / "gpt-6-2-sol-cards.html"
    meta = generate_cards(report_path, regenerated_out)
    assert meta["cards"] == 7
    assert meta["provenance"] == "measured"
    en_html = en_html_path.read_text(encoding="utf-8")
    assert regenerated_out.read_text(encoding="utf-8") == en_html

    zh_html = zh_html_path.read_text(encoding="utf-8")
    forbidden_identifiers = ("Henry", "Qi Chen", "qichen", "notion.so", "C:\\Users")
    for html_doc in (en_html, zh_html):
        assert html_doc.count('class="report-card"') == 7
        assert "1 / 7" in html_doc and "7 / 7" in html_doc
        assert "default-src 'none'; style-src 'unsafe-inline'" in html_doc
        assert "<script" not in html_doc.lower()
        for ident in forbidden_identifiers:
            assert ident not in html_doc


def test_terminal_bench_4_1_report_and_cards_integrity(workdir: Path) -> None:
    import csv
    import json

    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "reported" / "terminal-bench-4-1"
    report_path = data_dir / "report.json"
    zh_report_path = data_dir / "report.zh-CN.json"
    leaderboard_csv = data_dir / "leaderboard_4_1.csv"
    pareto_csv = data_dir / "pareto_frontiers_4_1.csv"
    tasks_csv = data_dir / "tasks_waffle_4_1.csv"
    domain_csv = data_dir / "domain_matrix_4_1.csv"
    versions_csv = data_dir / "version_evolution.csv"
    en_html_path = root / "examples" / "terminal-bench-4-1-card-report" / "index.html"
    zh_html_path = root / "examples" / "terminal-bench-4-1-card-report" / "index.zh-CN.html"
    ex_readme_zh = root / "examples" / "terminal-bench-4-1-card-report" / "README.md"
    ex_readme_en = root / "examples" / "terminal-bench-4-1-card-report" / "README.en.md"
    doc_zh = root / "docs" / "reports" / "terminal-bench-4-1.md"
    doc_en = root / "docs" / "reports" / "terminal-bench-4-1.en.md"
    svg_zh = root / "docs" / "reports" / "assets" / "terminal-bench-4-1-overview.svg"
    svg_en = root / "docs" / "reports" / "assets" / "terminal-bench-4-1-overview.en.svg"

    expected_files = [
        report_path,
        zh_report_path,
        leaderboard_csv,
        pareto_csv,
        tasks_csv,
        domain_csv,
        versions_csv,
        en_html_path,
        zh_html_path,
        ex_readme_zh,
        ex_readme_en,
        doc_zh,
        doc_en,
        svg_zh,
        svg_en,
    ]
    for path in expected_files:
        assert path.is_file(), f"Missing expected artifact: {path}"

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    zh_report_data = json.loads(zh_report_path.read_text(encoding="utf-8"))
    for payload in (report_data, zh_report_data):
        assert payload["schema_version"] == 1
        assert payload["report_id"] == "terminal-bench-4-1"
        assert payload["provenance"] == "anonymized_reported"
        assert payload["independently_reproduced"] is False
        assert len(payload["cards"]) == 7

    facts = report_data["facts"]
    scale = facts["scale"]
    assert scale["leaderboard_runs"] == 65
    assert scale["unique_model_agent_pairs"] == 52
    assert scale["tasks_total"] == 66
    assert scale["total_trials"] == 21450
    assert len(facts["domain_summary"]) == 7
    assert len(facts["commercial_cost_pareto_best_effort"]) == 7

    with leaderboard_csv.open(encoding="utf-8", newline="") as fh:
        lb_rows = list(csv.DictReader(fh))
    assert len(lb_rows) == 65
    assert sum(1 for r in lb_rows if r["is_cost_pareto_best"] == "True") == 7

    with tasks_csv.open(encoding="utf-8", newline="") as fh:
        task_rows = list(csv.DictReader(fh))
    assert len(task_rows) == 66
    assert sum(1 for r in task_rows if int(r["pass_count"]) == 0) == 4
    assert sum(int(r["total_trials"]) for r in task_rows) == 21450

    with domain_csv.open(encoding="utf-8", newline="") as fh:
        domain_rows = list(csv.DictReader(fh))
    assert len(domain_rows) == 20
    assert {
        "Security",
        "ML",
        "Media",
        "Hardware",
        "Software",
        "Science",
        "Operations",
    }.issubset(domain_rows[0])

    with versions_csv.open(encoding="utf-8", newline="") as fh:
        version_rows = list(csv.DictReader(fh))
    assert len(version_rows) == 5

    regenerated_en = workdir / "tb41-en.html"
    meta_en = generate_cards(report_path, regenerated_en)
    assert meta_en["cards"] == 7
    assert meta_en["provenance"] == "anonymized_reported"
    en_html = en_html_path.read_text(encoding="utf-8")
    assert regenerated_en.read_text(encoding="utf-8") == en_html

    regenerated_zh = workdir / "tb41-zh.html"
    meta_zh = generate_cards(zh_report_path, regenerated_zh)
    assert meta_zh["cards"] == 7

    zh_html = zh_html_path.read_text(encoding="utf-8")
    canary_fragments = (
        "26b5c67b-" + "86b8-4dba",
        "NEVER APPEAR IN " + "TRAINING CORPORA",
    )
    forbidden_identifiers = (
        "Henry",
        "Qi Chen",
        "qichen",
        "notion.so",
        "C:\\Users",
        *canary_fragments,
    )
    for html_doc in (en_html, zh_html):
        assert html_doc.count('class="report-card"') == 7
        assert "1 / 7" in html_doc and "7 / 7" in html_doc
        assert "default-src 'none'; style-src 'unsafe-inline'" in html_doc
        assert "<script" not in html_doc.lower()

    for artifact in expected_files:
        text = artifact.read_text(encoding="utf-8")
        for ident in forbidden_identifiers:
            assert ident not in text, f"Forbidden string {ident!r} found in {artifact}"
