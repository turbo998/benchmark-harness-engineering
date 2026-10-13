"""Harbor 0.24.0 release-schema adapter; Docker and live tiers require runtime probes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from benchmark_harness.contracts import Status, Usage, canonical
from benchmark_harness.engines import EngineObservation, classify_error, token

VERSION = "0.24.0"
RELEASE_WHEEL_SHA256 = "23b7ba616a3aae4eff561ced5e2c51c7186f2981e53a770dea9c689d3969877c"


def parse_trial(payload: dict[str, Any]) -> EngineObservation:
    for key in ("task_name", "trial_name", "agent_info", "task_checksum"):
        if key not in payload:
            raise ValueError(f"Unsupported Harbor trial schema: missing {key}")
    exception = payload.get("exception_info")
    verifier = payload.get("verifier_result")
    error = None
    if exception:
        error = f"{exception.get('exception_type')}: {exception.get('exception_message')}"
        status = classify_error(error)
    elif verifier and isinstance(verifier.get("rewards"), dict):
        reward = verifier["rewards"].get("reward")
        if not isinstance(reward, (int, float)):
            raise ValueError("Unsupported Harbor reward field")
        status = Status.PASSED if reward == 1 else Status.FAILED
    else:
        error = "Partial trial: no verifier result"
        status = Status.INFRASTRUCTURE_ERROR
    context = payload.get("agent_result") or {}
    if payload.get("step_results") and not context:
        raise ValueError("Multi-step usage requires per-step accounting; not silently flattened")
    total_input = token(context.get("n_input_tokens"))
    cached = token(context.get("n_cache_tokens"))
    if total_input is not None and cached is not None and cached > total_input:
        raise ValueError("Cache input exceeds inclusive input count")
    exclusive_input = (
        total_input - cached if total_input is not None and cached is not None else None
    )
    usage = Usage(
        input_tokens=exclusive_input,
        cache_read_tokens=cached,
        output_tokens=token(context.get("n_output_tokens")),
        provenance="engine_reported" if context else "missing",
        reason="Harbor input includes cache; missing cache prevents subtraction. "
        "Cache-write and reasoning counts are not established.",
    )
    timing = payload.get("agent_execution") or {}
    latency = None
    if timing.get("started_at") and timing.get("finished_at"):
        start = datetime.fromisoformat(timing["started_at"])
        end = datetime.fromisoformat(timing["finished_at"])
        latency = (end - start).total_seconds() * 1000
        if latency < 0:
            raise ValueError("Invalid Harbor phase timestamps")
    cost = context.get("cost_usd")
    return EngineObservation(
        engine="harbor",
        engine_version=VERSION,
        native_id=str(payload.get("id")) if payload.get("id") else None,
        status=status,
        error_reason=error,
        usage=usage,
        native_cost_usd=Decimal(str(cost)) if cost is not None else None,
        cost_reason="Native engine amount retained, no dated price/billing claim",
        latency_ms=latency,
        input_semantics="exclusive_input_after_cache_subtraction",
        output=verifier,
    )


def write_trial_config(task_path: Path, output: Path, *, agent: str = "nop") -> dict[str, Any]:
    if agent not in {"nop", "oracle"}:
        raise RuntimeError(
            "Live agent configuration blocked pending auth/isolation/accounting probes"
        )
    config = {
        "task": {"path": str(task_path)},
        "agent": {"name": agent},
        "environment": {"type": "docker"},
        "verifier": {"override_timeout_sec": 30},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(config) + b"\n")
    return {
        "config": config,
        "engine_version": VERSION,
        "capability": "construction-only; Linux/Docker trial help probe required",
        "live_allowed": False,
        "retry_owner": "harness",
        "framework_max_retries": 0,
        "note": "Use a single-trial invocation, not destructive framework exception retries",
    }
