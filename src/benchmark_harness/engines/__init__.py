"""Release-specific adapters, not a promise of live readiness."""

from decimal import Decimal
from typing import Any

from pydantic import Field

from benchmark_harness.contracts import Contract, Status, Usage


class EngineObservation(Contract):
    engine: str
    engine_version: str
    native_id: str | None = None
    status: Status
    error_reason: str | None = None
    usage: Usage
    native_cost_usd: Decimal | None = Field(default=None, ge=0)
    cost_reason: str
    latency_ms: float | None = Field(default=None, ge=0)
    input_semantics: str
    output: Any = None


def classify_error(message: str) -> Status:
    lowered = message.lower()
    if any(x in lowered for x in ("unauthorized", "authentication", "401", "403", "autherror")):
        return Status.AUTH_ERROR
    if any(x in lowered for x in ("quota", "rate limit", "429", "ratelimit")):
        return Status.QUOTA_ERROR
    if any(x in lowered for x in ("timeout", "timed out")):
        return Status.TIMEOUT
    if "cancel" in lowered:
        return Status.CANCELLED
    if any(x in lowered for x in ("docker", "environment", "infrastructure", "setup")):
        return Status.INFRASTRUCTURE_ERROR
    return Status.PROVIDER_ERROR


def token(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError("Invalid native token measurement")
    return value
