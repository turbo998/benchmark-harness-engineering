"""Console workflow; the default and demo never invoke a model."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Annotated, Any

import typer

from benchmark_harness.cards import generate_cards
from benchmark_harness.contracts import Case, Experiment, Result
from benchmark_harness.doctor import doctor as run_doctor
from benchmark_harness.engines import harbor, promptfoo
from benchmark_harness.manifest import build_manifest, read_cases, read_manifest, write_frozen
from benchmark_harness.report import generate_report, rescore_saved
from benchmark_harness.runner import LiveBlocked, run_mock
from benchmark_harness.samples import (
    accept_cases,
    export_coding,
    template_cases,
    write_acceptance,
    write_dataset,
)

app = typer.Typer(no_args_is_help=True, help="Offline-default evidence-first benchmark harness.")
OUTPUT = Annotated[Path, typer.Option(help="Dedicated output path under your workspace")]


def _print(value: Any) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2))


def _fail(error: Exception) -> None:
    typer.echo(f"Refused: {error}", err=True)
    raise typer.Exit(2)


@app.command()
def doctor(repository: Path = Path(".")) -> None:
    """Only version/help probes; no downloads, inference, deployment or paid calls."""
    _print(run_doctor(repository.resolve()))


@app.command("generate")
def generate(output: OUTPUT, seed: int = 42, mode: str = "template") -> None:
    """Generate original fixtures, never paid AI synthesis."""
    if mode != "template":
        _fail(LiveBlocked("AI generation requires separately approved provider/budget integration"))
    try:
        cases = template_cases(seed)
        write_dataset(output / "cases.jsonl", cases)
        write_dataset(output / "api" / "cases.jsonl", [c for c in cases if c.track == "api"])
        export_coding(cases, output / "coding")
    except ValueError as error:
        _fail(error)
    _print({"cases": len(cases), "paid_calls": 0, "scope": "engineering fixtures"})


@app.command("accept")
def accept(dataset: Path, output: OUTPUT) -> None:
    """Check original references/negative fixtures (trusted host check, not Docker validation)."""
    scratch = output.parent / ".acceptance-work"
    try:
        cases = read_cases(dataset)
        acceptance = accept_cases(cases, scratch)
        output.parent.mkdir(parents=True, exist_ok=True)
        write_acceptance(output, acceptance)
        _print(acceptance)
        if acceptance["rejected"]:
            raise typer.Exit(2)
    except ValueError as error:
        _fail(error)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


@app.command("plan")
def plan(
    dataset: Path,
    output: OUTPUT,
    repeats: int = 2,
    seed: int = 42,
    profile: str = "local",
    score_profile: str = "deterministic-v1",
    live: bool = False,
) -> None:
    """Freeze an immutable mock manifest. Live manifests require external reviewed configuration."""
    if live:
        _fail(
            LiveBlocked(
                "CLI live planning blocked: bind candidate/prices/approval and sandbox first"
            )
        )
    try:
        manifest = build_manifest(
            read_cases(dataset),
            repeats=repeats,
            seed=seed,
            profile=profile,
            score_profile=score_profile,
        )
        write_frozen(output, manifest)
    except ValueError as error:
        _fail(error)
    _print({"experiment_id": manifest.experiment_id, "mode": manifest.mode})


@app.command("run")
def run(manifest: Path, dataset: Path, output: OUTPUT, live: bool = False) -> None:
    """Execute/resume matching mock manifests; preserve all attempts and retry charges."""
    if live:
        _fail(LiveBlocked("Live engine tier has not passed isolation/accounting probes"))
    try:
        results = run_mock(read_manifest(manifest), read_cases(dataset), output)
    except (ValueError, LiveBlocked) as error:
        _fail(error)
    _print({"attempts": len(results), "paid_calls": 0, "data_status": "synthetic"})


@app.command("score")
def score(run_directory: Path, output: OUTPUT) -> None:
    """Regenerate assertions/attestations from hashed evidence; never execute saved candidate code."""
    try:
        results = rescore_saved(run_directory, output)
    except ValueError as error:
        _fail(error)
    _print({"rescored_attempts": len(results), "paid_calls": 0})


@app.command("report")
def report(run_directory: Path, output: OUTPUT) -> None:
    """Rebuild JSON/CSV/self-contained HTML/PNG/SVG from saved evidence, offline."""
    try:
        summary = generate_report(run_directory, output)
    except ValueError as error:
        _fail(error)
    _print(
        {
            "label": summary["label"],
            "planned_trials": summary["planned_trials"],
            "total_attempts": summary["total_attempts"],
        }
    )


@app.command("cards")
def cards(source: Path, output: OUTPUT) -> None:
    """Render a 7-card 4:5 visual benchmark report HTML from a saved run or reported JSON."""
    try:
        result = generate_cards(source, output)
    except ValueError as error:
        _fail(error)
    _print(result)


@app.command("engine-config")
def engine_config(engine: str, dataset: Path, output: OUTPUT) -> None:
    """Generate real promptfoo offline config or construction-only Harbor trial configuration."""
    try:
        if engine == "promptfoo":
            path = promptfoo.write_mock_config(read_cases(dataset), output)
            _print({"config": path.name, "live_allowed": False})
        elif engine == "harbor":
            _print(harbor.write_trial_config(Path("task"), output / "trial.json"))
        else:
            raise ValueError("Supported engines: promptfoo, harbor")
    except (ValueError, RuntimeError) as error:
        _fail(error)


@app.command("engine-smoke")
def engine_smoke(engine: str, dataset: Path, output: OUTPUT, repository: Path = Path(".")) -> None:
    """Real no-network promptfoo custom-provider smoke, never a live candidate evaluation."""
    try:
        if engine != "promptfoo":
            raise LiveBlocked("Harbor Docker runtime is unvalidated; no pretend engine success")
        result = promptfoo.run_offline(
            read_cases(dataset), output.resolve(), repository=repository.resolve()
        )
        (output / "smoke.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        _print({"engine": engine, "version": result["version"], "paid_calls": 0})
    except (ValueError, RuntimeError) as error:
        _fail(error)


def demo_workflow(
    output: Path, *, repeats: int = 2, score_profile: str = "deterministic-v1"
) -> dict[str, Any]:
    cases: list[Case] = template_cases()
    write_dataset(output / "samples" / "cases.jsonl", cases)
    export_coding(cases, output / "samples" / "coding")
    scratch = output / ".acceptance-work"
    try:
        acceptance = accept_cases(cases, scratch)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
    write_acceptance(output / "acceptance.json", acceptance)
    if acceptance["rejected"]:
        raise ValueError("Demo sample acceptance failed")
    manifest: Experiment = build_manifest(cases, repeats=repeats, score_profile=score_profile)
    write_frozen(output / "plan.json", manifest)
    results: list[Result] = run_mock(manifest, cases, output / "run")
    rescore_saved(output / "run", output / "scores.json")
    summary = generate_report(output / "run", output / "report")
    return {
        "label": summary["label"],
        "cases": len(cases),
        "attempts": len(results),
        "paid_calls": 0,
        "report": str(output / "report" / "index.html"),
    }


@app.command()
def demo(output: OUTPUT) -> None:
    """Complete the original fixture → acceptance → frozen plan → mock → score/report workflow."""
    try:
        _print(demo_workflow(output))
    except ValueError as error:
        _fail(error)


@app.command("export-schemas")
def export_schemas(output: OUTPUT) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name, model in (("case", Case), ("experiment", Experiment), ("result", Result)):
        (output / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(mode="serialization"), ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    app()
