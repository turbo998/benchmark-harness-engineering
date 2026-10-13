"""Self-contained offline report generation from verified, saved evidence only."""

from __future__ import annotations

import base64
import csv
import html
import json
import os
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

from benchmark_harness.artifacts import Archive
from benchmark_harness.contracts import AssertionOutcome, Result, canonical
from benchmark_harness.manifest import read_cases, read_manifest, verify_dataset
from benchmark_harness.metrics import summarize
from benchmark_harness.scoring import make_score, score_api

FIGURES = (
    "cost-quality",
    "latency-quality",
    "difficulty-heatmap",
    "distributions",
    "score-breakdown",
)


def load_saved(run: Path) -> tuple[Archive, list[Result]]:
    manifest = read_manifest(run / "manifest.json")
    cases = read_cases(run / "dataset.jsonl")
    verify_dataset(manifest, cases)
    archive = Archive(run, manifest)
    if archive.incomplete():
        raise ValueError("Interrupted attempts must be recovered before reporting")
    results = archive.load()
    by_id = {case.case_id: case for case in cases}
    for result in results:
        case = by_id[result.case_id]
        if (result.track, result.difficulty) != (case.track, case.difficulty):
            raise ValueError("Result task metadata drift")
    return archive, results


def rescore_saved(run: Path, output: Path) -> list[Result]:
    """Replay API assertions or frozen verifier attestations, never run saved agent code."""
    if output.resolve().is_relative_to((run / "attempts").resolve()):
        raise ValueError("Regenerated scores must not modify immutable attempt evidence")
    archive, results = load_saved(run)
    by_id = {c.case_id: c for c in read_cases(run / "dataset.jsonl")}
    rescored: list[Result] = []
    for result in results:
        case = by_id[result.case_id]
        if result.status.value not in {"passed", "failed", "review_pending"}:
            rescored.append(result)
            continue
        if case.track == "api":
            response = next(a for a in result.artifacts if a.path.endswith("response.json"))
            score = score_api(
                case,
                json.loads((run / response.path).read_bytes()),
                profile=archive.manifest.score_profile,
            )
        else:
            attestation = next(a for a in result.artifacts if a.path.endswith("verification.json"))
            response = next(a for a in result.artifacts if a.path.endswith("response.json"))
            verification = json.loads((run / attestation.path).read_bytes())
            if case.coding is None or verification["verifier_hash"] != case.coding.verifier_hash:
                raise ValueError("Verifier identity drift")
            if verification["response_artifact_hash"] != response.sha256:
                raise ValueError("Submission attestation drift")
            if type(verification["passed"]) is not bool:
                raise ValueError("Invalid verifier attestation")
            score = make_score(
                (
                    AssertionOutcome(
                        name="independent-verifier",
                        category="functional",
                        weight=1,
                        passed=verification["passed"],
                    ),
                ),
                profile=archive.manifest.score_profile,
            )
        rescored.append(Result.model_validate(result.model_dump() | {"score": score}))
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical([r.model_dump(mode="json") for r in rescored]) + b"\n"
    if output.exists() and output.read_bytes() != payload:
        raise ValueError("Refusing to overwrite different regenerated scores")
    output.write_bytes(payload)
    return rescored


def _figures(summary: dict[str, Any], output: Path) -> dict[str, str]:
    os.environ["MPLCONFIGDIR"] = str((output / ".plot-cache").resolve())
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    plt.rcParams.update({"svg.hashsalt": "benchmark-harness-v1", "font.size": 9})
    image_data: dict[str, str] = {}
    points = summary["points"]
    for figure_name in FIGURES:
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout="constrained")
        for ax, track in zip(axes, ("api", "coding"), strict=True):
            rows = [p for p in points if p["track"] == track]
            labels = [p["candidate_id"] for p in rows]
            ax.set_title(
                f"{track.upper()} — synthetic fixtures"
                if "SYNTHETIC" in summary["label"]
                else track.upper()
            )
            if figure_name == "cost-quality":
                for p in rows:
                    if p["cost_usd"] is not None and p["comparative_quality"] is not None:
                        ax.scatter(float(Decimal(p["cost_usd"])), p["comparative_quality"])
                        ax.annotate(
                            p["candidate_id"],
                            (float(Decimal(p["cost_usd"])), p["comparative_quality"]),
                        )
                frontier = [p for p in rows if p["point_id"] in summary["pareto_by_track"][track]]
                frontier.sort(key=lambda p: Decimal(p["cost_usd"]))
                if frontier:
                    ax.plot(
                        [float(Decimal(p["cost_usd"])) for p in frontier],
                        [p["comparative_quality"] for p in frontier],
                        "--",
                        marker="D",
                        label="Pareto",
                    )
                    ax.legend()
                ax.set_xlabel("All-attempt candidate cost (USD; synthetic in demo)")
                ax.set_ylabel("Macro quality (review-complete only)")
            elif figure_name == "latency-quality":
                for p in rows:
                    if p["latency_ms"] is not None and p["comparative_quality"] is not None:
                        ax.scatter(p["latency_ms"], p["comparative_quality"])
                        ax.annotate(p["candidate_id"], (p["latency_ms"], p["comparative_quality"]))
                ax.set_xlabel("Mean API/agent phase latency (ms; observed finals)")
                ax.set_ylabel("Macro quality (review-complete only)")
            elif figure_name == "difficulty-heatmap":
                levels = ["atomic", "medium", "complex"]
                values = [
                    [p["difficulty"].get(level, float("nan")) for level in levels] for p in rows
                ]
                if rows:
                    image = ax.imshow(values, aspect="auto", vmin=0, vmax=1, cmap="YlGnBu")
                    fig.colorbar(image, ax=ax, label="Functional score incl. planned errors")
                    ax.set_xticks(range(3), levels)
                    ax.set_yticks(range(len(rows)), labels)
                    for i, row in enumerate(values):
                        for j, value in enumerate(row):
                            ax.text(j, i, f"{value:.2f}", ha="center", va="center")
            elif figure_name == "distributions":
                for p in rows:
                    if p["functional_distribution"]:
                        ax.hist(
                            p["functional_distribution"],
                            bins=[-0.01, 0.25, 0.5, 0.75, 1.01],
                            alpha=0.55,
                            label=p["candidate_id"],
                        )
                ax.set_xlabel("Functional score; repetitions are not independent tasks")
                ax.set_ylabel("Planned repeat cells")
                if rows:
                    ax.legend()
            else:
                keys = ("functional", "compliance", "rubric")
                for i, p in enumerate(rows):
                    for j, key in enumerate(keys):
                        value = p["breakdown"].get(key)
                        if value is not None:
                            ax.bar(
                                i + (j - 1) * 0.22, value, width=0.22, label=key if i == 0 else None
                            )
                ax.set_xticks(range(len(labels)), labels, rotation=10)
                ax.set_ylabel("Observed component mean; absent rubric not zero")
                ax.set_ylim(0, 1.1)
                if rows:
                    ax.legend()
        svg = output / f"{figure_name}.svg"
        fig.savefig(svg, metadata={"Date": None, "Creator": "benchmark-harness 0.1.0"})
        fig.savefig(
            output / f"{figure_name}.png", dpi=110, metadata={"Software": "benchmark-harness 0.1.0"}
        )
        plt.close(fig)
        image_data[figure_name] = base64.b64encode(svg.read_bytes()).decode("ascii")
    if (output / ".plot-cache").exists():
        shutil.rmtree(output / ".plot-cache")
    return image_data


def _cell(value: Any) -> str:
    if value is None:
        return "unknown / pending"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _html(summary: dict[str, Any], figures: dict[str, str]) -> str:
    def escape(value: Any) -> str:
        return html.escape(_cell(value))

    headers = [
        "candidate_id",
        "track",
        "planned",
        "attempted_trials",
        "total_attempts",
        "success_rate_planned",
        "macro_functional",
        "quality",
        "quality_coverage",
        "quality_missing_trials",
        "comparative_quality",
        "review_pending",
        "latency_ms",
        "cost_usd",
        "known_cost_usd",
        "missing_cost_attempts",
    ]
    table = "<tr>" + "".join(f"<th>{escape(h)}</th>" for h in headers) + "</tr>"
    evidence = ""
    for point in summary["points"]:
        table += "<tr>" + "".join(f"<td>{escape(point[h])}</td>" for h in headers) + "</tr>"
        links = " ".join(
            f'<a href="evidence/{html.escape(p, quote=True)}">attempt {i + 1}</a>'
            for i, p in enumerate(point["evidence"])
        )
        evidence += (
            f"<h3>{escape(point['candidate_id'])} / {escape(point['track'])}</h3><p>{links}</p>"
        )
        evidence += (
            "<pre>"
            + html.escape(
                json.dumps(
                    {
                        k: point[k]
                        for k in (
                            "statuses",
                            "attempt_statuses",
                            "uncertainty",
                            "cost_provenance",
                            "cost_reason",
                            "cost_missing_reasons",
                            "p95_reason",
                            "phase_means_ms",
                        )
                    },
                    indent=2,
                )
            )
            + "</pre>"
        )
    charts = "".join(
        f'<section><h2>{escape(name)}</h2><img alt="{escape(name)}" '
        f'src="data:image/svg+xml;base64,{data}"><p>Coordinates derive from summary.json points; '
        "missing cost/review points are excluded, never imputed. Partial reviewed quality means "
        "remain descriptive in tables but are excluded from comparative scatters and Pareto. API and coding panels remain "
        "separate. Demo coordinates are synthetic, not measured. Evidence links are below.</p></section>"
        for name, data in figures.items()
    )
    semantics = "".join(
        f"<li><b>{escape(k)}</b>: {escape(v)}</li>" for k, v in summary["semantics"].items()
    )
    embedded = html.escape(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return (
        "<!doctype html><html lang=en><meta charset=utf-8>"
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "img-src data:; style-src 'unsafe-inline'\">"
        "<title>Benchmark harness evidence report</title><style>"
        "body{font:15px system-ui;margin:2rem;max-width:1200px}table{border-collapse:collapse;"
        "display:block;overflow-x:auto}td,th{border:1px solid #ccc;padding:.4rem;text-align:left}"
        "img{max-width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere}"
        ".warning{background:#fff1cf;padding:1rem}</style><body>"
        f"<h1>Benchmark harness report</h1><p class=warning>{escape(summary['label'])}</p>"
        f"<p>Experiment {escape(summary['experiment_id'])}; cohort {escape(summary['cohort'])}. "
        f"Planned {summary['planned_trials']}; attempted trials {summary['attempted_trials']}; "
        f"all attempts {summary['total_attempts']}. Actual inference charge for mock workflow: "
        f"{escape(summary['actual_inference_charges_usd'])} USD.</p>"
        f"<ul>{semantics}</ul><table>{table}</table>{charts}<h2>Evidence</h2>{evidence}"
        f"<details><summary>Exact report data</summary><pre>{embedded}</pre></details></body></html>"
    )


def generate_report(run: Path, output: Path) -> dict[str, Any]:
    if output.resolve().is_relative_to((run / "attempts").resolve()):
        raise ValueError("Reports must not modify immutable attempt evidence")
    archive, results = load_saved(run)
    cases = read_cases(run / "dataset.jsonl")
    summary = summarize(archive.manifest, cases, results)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_bytes(canonical(summary) + b"\n")
    (output / "results.json").write_bytes(
        canonical([r.model_dump(mode="json") for r in results]) + b"\n"
    )
    fields = [
        "candidate_id",
        "track",
        "cohort",
        "planned",
        "attempted_trials",
        "total_attempts",
        "successes",
        "success_rate_planned",
        "macro_functional",
        "quality",
        "quality_coverage",
        "comparative_quality",
        "micro_assertion_rate",
        "micro_weighted_assertion_rate",
        "review_pending",
        "quality_missing_trials",
        "latency_ms",
        "latency_metric",
        "cost_usd",
        "known_cost_usd",
        "missing_cost_attempts",
        "p95_ms",
    ]
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: p[k] for k in fields} for p in summary["points"])
    for path in (run / "attempts").glob("*/*/*/*/*"):
        if path.is_file():
            destination = output / "evidence" / path.relative_to(run)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if path.resolve() == destination.resolve():
                raise ValueError("Report output overlaps run evidence")
            shutil.copyfile(path, destination)
    figures = _figures(summary, output)
    (output / "index.html").write_text(_html(summary, figures), encoding="utf-8")
    return summary
