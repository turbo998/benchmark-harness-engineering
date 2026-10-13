"""Native Harbor Copilot discovery is not proof of broker or sandbox compatibility."""

import json
import re
from typing import Any

from benchmark_harness.contracts import Status, Usage
from benchmark_harness.engines import classify_error

OBSERVED_VERSION = "1.0.94-3"


def probe_help(version: str, help_text: str) -> dict[str, Any]:
    match = re.search(r"(\d+\.\d+\.\d+(?:-\d+)?)", version)
    features = {
        "prompt": "--prompt" in help_text,
        "model": "--model" in help_text,
        "json_output": "--output-format" in help_text,
    }
    return {
        "observed_version": match.group(1) if match else None,
        "features": features,
        "harbor_release_native_adapter": "copilot-cli (source-verified Harbor 0.24.0 wheel)",
        "bridge": "blocked until installed Harbor help/schema, isolated token/BYOK and live approval",
        "strict_dollar_cap": False,
        "host_credential_forwarding": "prohibited",
        "live_allowed": False,
    }


def parse_events(text: str) -> dict[str, Any]:
    events = []
    malformed = []
    input_tokens: int | None = None
    output_tokens: int | None = None
    terminal: dict[str, Any] | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise ValueError("Not an event object")
        except (ValueError, TypeError):
            malformed.append(line)
            continue
        events.append(event)
        if event["type"] == "usage":
            for category in ("input_tokens", "output_tokens"):
                value = event.get(category)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError("Invalid Copilot usage")
            if event.get("input_tokens") is not None:
                input_tokens = (input_tokens or 0) + event["input_tokens"]
            if event.get("output_tokens") is not None:
                output_tokens = (output_tokens or 0) + event["output_tokens"]
        if event["type"] == "result":
            terminal = event.get("data", event)
    error = next(
        (
            line
            for line in malformed
            if any(
                word in line.lower()
                for word in ("authentication", "unauthorized", "quota", "timeout")
            )
        ),
        None,
    )
    status = classify_error(error) if error else Status.REVIEW_PENDING
    if terminal:
        status = Status.REVIEW_PENDING if terminal.get("exitCode") == 0 else Status.PROVIDER_ERROR
    return {
        "events": events,
        "malformed_lines": malformed,
        "status": status.value,
        "terminal_seen": terminal is not None,
        "usage": Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provenance="engine_reported"
            if input_tokens is not None or output_tokens is not None
            else "missing",
            reason="Missing categories remain unknown; never infer zero from absent JSONL events",
        ).model_dump(mode="json"),
        "cost_usd": None,
        "cost_reason": "Opaque native usage; no dated exact billing",
        "live_allowed": False,
    }
