"""Versioned, closed contracts. Unknown measurements are never zero-filled."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator


def canonical(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Assertion(Contract):
    name: str = Field(min_length=1)
    kind: Literal["exact", "json_equal", "json_keys", "contains", "regex"]
    expected: Any
    weight: float = Field(gt=0)
    category: Literal["functional", "compliance"] = "functional"

    @model_validator(mode="after")
    def valid_expression(self) -> Self:
        if self.kind in {"contains", "regex"} and not isinstance(self.expected, str):
            raise ValueError("Text assertion requires a string")
        if self.kind == "regex":
            try:
                re.compile(self.expected)
            except re.error as error:
                raise ValueError(f"Invalid regex: {error}") from error
        if self.kind == "json_keys" and (
            not isinstance(self.expected, list)
            or not all(isinstance(x, str) for x in self.expected)
        ):
            raise ValueError("json_keys requires an array of field names")
        return self


class CodingSpec(Contract):
    entrypoint: Literal["solution.py"] = "solution.py"
    instruction: str = Field(min_length=1)
    reference: str
    negatives: tuple[str, ...] = Field(min_length=1)
    verifier: str
    seed_files: dict[str, str]
    verifier_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def verifier_identity(self) -> Self:
        if hashlib.sha256(self.verifier.encode()).hexdigest() != self.verifier_hash:
            raise ValueError("Verifier hash mismatch")
        if any(name != "solution.py" for name in self.seed_files):
            raise ValueError("Only the declared output is agent-visible")
        return self


class Case(Contract):
    schema_version: Literal["1"] = "1"
    case_id: str = Field(pattern=r"^case-[a-f0-9]{64}$")
    track: Literal["api", "coding"]
    title: str = Field(min_length=1)
    language: Literal["en", "zh"]
    difficulty: Literal["atomic", "medium", "complex"]
    prompt: str = Field(min_length=1)
    normalization: Literal["none", "strip", "casefold"] = "strip"
    assertions: tuple[Assertion, ...] = ()
    accepted: tuple[Any, ...] = ()
    rejected: tuple[Any, ...] = ()
    coding: CodingSpec | None = None
    seed: int = Field(ge=0)
    recipe_version: str = "original-template-v1"
    rubric_version: str | None = None

    @model_validator(mode="after")
    def identity_and_oracle(self, info: ValidationInfo) -> Self:
        draft = bool(info.context and info.context.get("draft"))
        if not draft and self.case_id != "case-" + digest(
            self.model_dump(mode="json", exclude={"case_id"})
        ):
            raise ValueError("Case content does not match its stable ID")
        if self.track == "api":
            if not self.assertions or not self.accepted or not self.rejected or self.coding:
                raise ValueError(
                    "API case needs assertions and independent positive/negative fixtures"
                )
            if not any(a.category == "functional" for a in self.assertions):
                raise ValueError("API case needs a functional assertion")
        elif self.coding is None or self.assertions or self.accepted or self.rejected:
            raise ValueError("Coding case must have a separately frozen verifier")
        return self


def make_case(**values: Any) -> Case:
    defaults = {
        "schema_version": "1",
        "normalization": "strip",
        "assertions": (),
        "accepted": (),
        "rejected": (),
        "coding": None,
        "recipe_version": "original-template-v1",
        "rubric_version": None,
    }
    material = defaults | values
    draft = Case.model_validate(
        material | {"case_id": "case-" + "0" * 64},
        context={"draft": True},
    )
    normalized = draft.model_dump(mode="json", exclude={"case_id"})
    return Case.model_validate(normalized | {"case_id": "case-" + digest(normalized)})


class Candidate(Contract):
    candidate_id: str = Field(pattern=r"^[a-zA-Z0-9._-]+$", max_length=64)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    resolved_version: str = Field(min_length=1)
    deployment: str | None = None
    prompt_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    scaffold_version: str
    agent_version: str


class Environment(Contract):
    profile: Literal["local", "azure"]
    os: str = Field(min_length=1)
    region: str = Field(min_length=1)
    image_digest: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    cache_policy: Literal["disabled", "provider_only", "replay"]
    warmup: Literal["cold", "warm", "synthetic"]

    @property
    def cohort(self) -> str:
        return f"{self.profile}:{digest(self)[:16]}"


class Experiment(Contract):
    schema_version: Literal["1"] = "1"
    experiment_id: str = Field(pattern=r"^exp-[a-f0-9]{64}$")
    dataset_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    dataset_revision: str
    case_ids: tuple[Annotated[str, Field(pattern=r"^case-[a-f0-9]{64}$")], ...] = Field(
        min_length=1
    )
    split: Literal["fixture", "pilot", "holdout"]
    generator_version: str
    candidates: tuple[Candidate, ...] = Field(min_length=1)
    environment: Environment
    engine_versions: dict[str, str]
    scorer_version: str
    score_profile: Literal["deterministic-v1", "author-style-70-15-15-v1"]
    repeats: int = Field(ge=1, le=10000)
    order_seed: int = Field(ge=0)
    mode: Literal["mock", "live"]
    retry_owner: Literal["harness"] = "harness"
    max_attempts: int = Field(ge=1, le=10)
    budget_usd: Decimal = Field(ge=0)
    approval_id: str | None = None
    price_table_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def locked(self) -> Self:
        if self.experiment_id != "exp-" + digest(
            self.model_dump(mode="json", exclude={"experiment_id"})
        ):
            raise ValueError("Manifest identity mismatch")
        if len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError("Duplicate case IDs")
        if len({c.candidate_id for c in self.candidates}) != len(self.candidates):
            raise ValueError("Duplicate candidate IDs")
        if not self.engine_versions or not self.scorer_version:
            raise ValueError("Engine and scorer versions are required")
        if self.mode == "live" and (
            not self.approval_id or not self.price_table_hash or self.budget_usd <= 0
        ):
            raise ValueError("Live manifests require approval, dated prices and budget")
        if self.mode == "mock" and self.environment.warmup != "synthetic":
            raise ValueError("Mock cohort must be labelled synthetic")
        return self


class Status(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    PROVIDER_ERROR = "provider_error"
    QUOTA_ERROR = "quota_error"
    AUTH_ERROR = "auth_error"
    CANCELLED = "cancelled"
    INVALID_CASE = "invalid_case"
    REVIEW_PENDING = "review_pending"


class Usage(Contract):
    input_tokens: int | None = Field(default=None, ge=0)
    cache_read_tokens: int | None = Field(default=None, ge=0)
    cache_write_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    provenance: Literal["provider_reported", "engine_reported", "estimated", "missing", "synthetic"]
    reason: str | None = None

    @model_validator(mode="after")
    def missing_reason(self) -> Self:
        fields = (
            "input_tokens",
            "cache_read_tokens",
            "cache_write_tokens",
            "output_tokens",
            "reasoning_tokens",
        )
        if any(getattr(self, f) is None for f in fields) and not self.reason:
            raise ValueError("Missing token categories need a reason")
        if self.provenance == "missing" and any(getattr(self, f) is not None for f in fields):
            raise ValueError("Missing usage cannot contain measurements")
        return self


class Cost(Contract):
    amount: Decimal | None = Field(default=None, ge=0)
    currency: Literal["USD"] = "USD"
    provenance: Literal["measured", "estimated", "missing", "synthetic", "no_charge"]
    reason: str | None = None
    price_date: date | None = None
    price_table_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    scope: Literal["candidate", "generator", "grader", "infrastructure", "total"] = "candidate"

    @model_validator(mode="after")
    def cost_evidence(self) -> Self:
        if self.amount is None and not self.reason:
            raise ValueError("Unknown cost needs a reason")
        if self.provenance == "missing" and self.amount is not None:
            raise ValueError("Missing cost must be null")
        if self.provenance in {"measured", "estimated"} and (
            self.price_date is None or not self.price_table_hash
        ):
            raise ValueError("Priced cost needs dated pricing provenance")
        if self.provenance == "no_charge" and (self.amount != 0 or not self.reason):
            raise ValueError("No-charge cost needs an explicit zero and reason")
        if self.provenance == "synthetic" and not self.reason:
            raise ValueError("Synthetic dollars must be labelled")
        return self


class PhaseTiming(Contract):
    setup_ms: float | None = Field(default=None, ge=0)
    api_ms: float | None = Field(default=None, ge=0)
    ttft_ms: float | None = Field(default=None, ge=0)
    routing_ms: float | None = Field(default=None, ge=0)
    agent_ms: float | None = Field(default=None, ge=0)
    verification_ms: float | None = Field(default=None, ge=0)
    teardown_ms: float | None = Field(default=None, ge=0)
    wall_ms: float = Field(ge=0)
    started_at: datetime
    finished_at: datetime
    provenance: Literal["measured", "synthetic"]
    missing_reason: str

    @model_validator(mode="after")
    def consistent_clock(self) -> Self:
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ValueError("Phase timestamps must carry time zones")
        elapsed = (self.finished_at - self.started_at).total_seconds() * 1000
        if elapsed < 0 or abs(elapsed - self.wall_ms) > 0.001:
            raise ValueError("Wall duration does not match phase timestamps")
        if self.ttft_ms is not None and self.api_ms is not None and self.ttft_ms > self.api_ms:
            raise ValueError("TTFT cannot exceed API response duration")
        return self


class AssertionOutcome(Contract):
    name: str
    category: Literal["functional", "compliance"]
    weight: float = Field(gt=0)
    passed: bool


class Score(Contract):
    functional: float | None = Field(default=None, ge=0, le=1)
    compliance: float | None = Field(default=None, ge=0, le=1)
    rubric: float | None = Field(default=None, ge=0, le=1)
    composite: float | None = Field(default=None, ge=0, le=1)
    profile: Literal["deterministic-v1", "author-style-70-15-15-v1"]
    review: Literal["not_required", "pending", "machine_reviewed", "human_reviewed"]
    reviewer_version: str | None = None
    missing_reason: str | None = None
    assertions: tuple[AssertionOutcome, ...] = ()

    @model_validator(mode="after")
    def separate_review(self) -> Self:
        if self.review == "pending" and self.rubric is not None:
            raise ValueError("Pending rubric is null, not zero")
        if self.review in {"human_reviewed", "machine_reviewed"} and (
            self.rubric is None or not self.reviewer_version
        ):
            raise ValueError("Reviewed rubric needs a value and version")
        if self.profile == "author-style-70-15-15-v1":
            if None in (self.functional, self.compliance, self.rubric):
                if self.composite is not None or not self.missing_reason:
                    raise ValueError("Incomplete weighted profile must remain pending")
            else:
                assert (
                    self.functional is not None
                    and self.compliance is not None
                    and self.rubric is not None
                )
                if (
                    abs(
                        self.composite_or_zero()
                        - (0.7 * self.functional + 0.15 * self.compliance + 0.15 * self.rubric)
                    )
                    > 1e-10
                ):
                    raise ValueError("Composite does not reconcile")
        elif self.composite != self.functional:
            raise ValueError("Deterministic composite must equal functional score")
        return self

    def composite_or_zero(self) -> float:
        return -1.0 if self.composite is None else self.composite


class Artifact(Contract):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size: int = Field(ge=0)

    @model_validator(mode="after")
    def safe_path(self) -> Self:
        if not re.fullmatch(r"[a-zA-Z0-9._/-]+", self.path) or ".." in self.path.split("/"):
            raise ValueError("Artifact path must be a safe relative evidence path")
        if self.path.startswith("/"):
            raise ValueError("Absolute artifact path forbidden")
        return self


class Result(Contract):
    schema_version: Literal["1"] = "1"
    experiment_id: str = Field(pattern=r"^exp-[a-f0-9]{64}$")
    manifest_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    case_id: str = Field(pattern=r"^case-[a-f0-9]{64}$")
    candidate_id: str
    cohort: str
    track: Literal["api", "coding"]
    difficulty: Literal["atomic", "medium", "complex"]
    repeat: int = Field(ge=0)
    attempt: int = Field(ge=1)
    trace_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Status
    error_reason: str | None = None
    data_status: Literal["synthetic", "measured_by_this_project", "third_party_reported"]
    usage: Usage
    cost: Cost
    timing: PhaseTiming
    score: Score
    artifacts: tuple[Artifact, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def result_semantics(self) -> Self:
        failures = set(Status) - {Status.PASSED, Status.REVIEW_PENDING}
        if self.status in failures and not self.error_reason:
            raise ValueError("Failure needs an explicit reason")
        if self.status == Status.REVIEW_PENDING and self.score.review != "pending":
            raise ValueError("review_pending status requires pending review")
        if self.status == Status.PASSED and (
            self.score.functional != 1 or self.score.composite is None
        ):
            raise ValueError("Passed requires complete functional score")
        if self.data_status == "synthetic" and (
            self.timing.provenance != "synthetic"
            or self.cost.provenance not in {"synthetic", "missing", "no_charge"}
        ):
            raise ValueError("Synthetic result cannot claim measured metrics")
        return self
