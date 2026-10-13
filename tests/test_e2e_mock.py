import json
from pathlib import Path

from typer.testing import CliRunner

from benchmark_harness.cli import app


def test_cli_full_no_cost_workflow(workdir: Path) -> None:
    runner = CliRunner()
    dataset = workdir / "samples" / "cases.jsonl"
    for command in [
        ["generate", "--output", str(workdir / "samples")],
        ["accept", str(dataset), "--output", str(workdir / "acceptance.json")],
        ["plan", str(dataset), "--output", str(workdir / "plan.json"), "--repeats", "1"],
        ["run", str(workdir / "plan.json"), str(dataset), "--output", str(workdir / "run")],
        ["score", str(workdir / "run"), "--output", str(workdir / "scores.json")],
        ["report", str(workdir / "run"), "--output", str(workdir / "report")],
        ["run", str(workdir / "plan.json"), str(dataset), "--output", str(workdir / "run")],
    ]:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, (result.output, result.exception)
    summary = json.loads((workdir / "report" / "summary.json").read_bytes())
    assert summary["actual_inference_charges_usd"] == "0"
    assert summary["planned_trials"] == 18
    assert (workdir / "report" / "index.html").exists()


def test_cli_demo_and_explicit_live_refusal(workdir: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["demo", "--output", str(workdir / "demo")])
    assert result.exit_code == 0, (result.output, result.exception)
    assert json.loads(result.output)["paid_calls"] == 0
    for command in [
        ["generate", "--output", str(workdir / "blocked"), "--mode", "ai"],
        [
            "plan",
            str(workdir / "demo" / "samples" / "cases.jsonl"),
            "--output",
            str(workdir / "blocked-plan.json"),
            "--live",
        ],
        [
            "run",
            str(workdir / "demo" / "plan.json"),
            str(workdir / "demo" / "samples" / "cases.jsonl"),
            "--output",
            str(workdir / "blocked-run"),
            "--live",
        ],
        [
            "engine-smoke",
            "harbor",
            str(workdir / "demo" / "samples" / "cases.jsonl"),
            "--output",
            str(workdir / "blocked-engine"),
        ],
    ]:
        blocked = runner.invoke(app, command)
        assert blocked.exit_code == 2 and "Refused:" in blocked.output
