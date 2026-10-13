"""promptfoo 0.124.0: native result parsing and real no-cost custom-provider invocation."""

from __future__ import annotations

import json
import os
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from benchmark_harness.contracts import Case, Status, Usage, canonical
from benchmark_harness.engines import EngineObservation, classify_error, token

VERSION = "0.124.0"
MOCK_PROVIDER = """// Original no-network provider for harness engine smoke tests.
class HarnessMockProvider {
  id() { return 'harness-offline-mock'; }
  async callApi(prompt, context) {
    return { output: context.vars.expected,
             tokenUsage: { prompt: 0, completion: 0, total: 0 },
             cost: 0, metadata: { dataStatus: 'synthetic', actualPaidCalls: 0 } };
  }
}
module.exports = HarnessMockProvider;
"""


def parse_output(payload: dict[str, Any]) -> list[EngineObservation]:
    envelope = payload.get("results")
    rows = envelope.get("results") if isinstance(envelope, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Unsupported promptfoo export shape (expected results.results)")
    observations = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid promptfoo result row")
        response = row.get("response") or {}
        if not isinstance(response, dict):
            raise ValueError("Invalid promptfoo provider response")
        error = row.get("error") or response.get("error")
        if not error and type(row.get("success")) is not bool:
            raise ValueError("Partial result lacks success/error; not assumed successful")
        status = (
            classify_error(str(error))
            if error
            else (Status.PASSED if row["success"] else Status.FAILED)
        )
        raw_usage = response.get("tokenUsage") or {}
        input_tokens = token(raw_usage.get("prompt"))
        output_tokens = token(raw_usage.get("completion"))
        cached = token(raw_usage.get("cached"))
        details = raw_usage.get("completionDetails") or {}
        if not isinstance(details, dict):
            raise ValueError("Invalid promptfoo completion details")
        cache_write = token(details.get("cacheCreationInputTokens"))
        reasoning = token(details.get("reasoning"))
        usage = Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cached,
            cache_write_tokens=cache_write,
            reasoning_tokens=reasoning,
            provenance="engine_reported" if raw_usage else "missing",
            reason="Cache-write/reasoning or other categories not established; native prompt semantics retained"
            if None in (input_tokens, output_tokens, cached, cache_write, reasoning)
            else None,
        )
        cost = response.get("cost")
        observations.append(
            EngineObservation(
                engine="promptfoo",
                engine_version=VERSION,
                native_id=row.get("id"),
                status=status,
                error_reason=str(error)
                if error
                else ("Native assertion failure" if status == Status.FAILED else None),
                usage=usage,
                native_cost_usd=Decimal(str(cost)) if cost is not None else None,
                cost_reason="Native engine-reported amount only; not priced authoritative billing",
                latency_ms=row.get("latencyMs"),
                input_semantics="native_prompt_unverified",
                output=response.get("output"),
            )
        )
    return observations


def write_mock_config(cases: list[Case], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    api = [case for case in cases if case.track == "api"]
    if not api:
        raise ValueError("promptfoo adapter requires API cases")
    (directory / "mock-provider.cjs").write_text(MOCK_PROVIDER, encoding="utf-8")
    tests = []
    for case in api:
        expected = case.accepted[0]
        if not isinstance(expected, str):
            expected = json.dumps(expected, ensure_ascii=False, sort_keys=True)
        tests.append(
            {
                "vars": {"instruction": case.prompt, "expected": expected},
                "metadata": {"case_id": case.case_id, "data_status": "synthetic"},
                "assert": [{"type": "equals", "value": expected}],
            }
        )
    config = {
        "description": "SYNTHETIC no-network harness engine smoke; no measured model performance",
        "prompts": ["{{instruction}}"],
        "providers": ["file://mock-provider.cjs"],
        "tests": tests,
        "evaluateOptions": {"maxConcurrency": 1},
    }
    path = directory / "promptfooconfig.json"
    path.write_bytes(canonical(config) + b"\n")
    return path


def executable(repository: Path) -> list[str]:
    package = repository / "engines" / "node_modules" / "promptfoo"
    if not (package / "package.json").exists():
        raise RuntimeError("promptfoo is not installed; npm ci --prefix engines --ignore-scripts")
    metadata = json.loads((package / "package.json").read_bytes())
    if metadata["version"] != VERSION:
        raise RuntimeError("promptfoo version drift")
    binary = metadata["bin"]["promptfoo"] if isinstance(metadata["bin"], dict) else metadata["bin"]
    portable = (
        repository / "engines" / "runtime" / "node_modules" / "node-win-x64" / "bin" / "node.exe"
    )
    node = str(portable.resolve()) if os.name == "nt" and portable.exists() else "node"
    return [node, str((package / binary).resolve())]


def offline_environment(repository: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "PROMPTFOO_DISABLE_TELEMETRY": "1",
            "PROMPTFOO_DISABLE_UPDATE": "1",
            "PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION": "1",
        }
    )
    runtime_modules = repository / "engines" / "runtime" / "node_modules"
    if runtime_modules.exists():
        env["NODE_PATH"] = str(runtime_modules.resolve())
    return env


def run_offline(cases: list[Case], directory: Path, *, repository: Path) -> dict[str, Any]:
    config = write_mock_config(cases, directory)
    output = directory / "native-output.json"
    command = executable(repository) + [
        "eval",
        "--config",
        str(config.resolve()),
        "--output",
        str(output.resolve()),
        "--no-cache",
        "--max-concurrency",
        "1",
        "--no-share",
        "--no-write",
        "--no-progress-bar",
        "--no-table",
    ]
    inherited = offline_environment(repository)
    env = {
        k: v
        for k, v in inherited.items()
        if k
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "PATHEXT",
            "NODE_PATH",
            "PROMPTFOO_DISABLE_TELEMETRY",
            "PROMPTFOO_DISABLE_UPDATE",
            "PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION",
        }
    }
    env.update(
        {
            "PROMPTFOO_CONFIG_DIR": str((directory / ".promptfoo").resolve()),
        }
    )
    process = subprocess.run(
        command,
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if process.returncode != 0 or not output.exists():
        raise RuntimeError(f"promptfoo offline invocation failed: {process.stderr[-1500:]}")
    payload: dict[str, Any] = json.loads(output.read_bytes())
    observations = parse_output(payload)
    if len(observations) != len([c for c in cases if c.track == "api"]):
        raise ValueError("Engine returned incomplete offline smoke")
    return {
        "command": command,
        "version": VERSION,
        "paid_calls": 0,
        "observations": [o.model_dump(mode="json") for o in observations],
    }
