"""Pure accounting transitions plus a transactional local store.

Blob stores can persist the same LedgerState with ETag/lease compare-and-swap.
An unresolved dispatch retains its reservation through cancellation or restart.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from benchmark_harness.contracts import Contract, digest

TOKEN_CATEGORIES = (
    "input_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
)


class BudgetError(ValueError):
    pass


class PriceTable(Contract):
    currency: Literal["USD"] = "USD"
    effective_date: date
    source: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    per_million: dict[str, Decimal]
    token_semantics: Literal["exclusive_categories"] = "exclusive_categories"

    @model_validator(mode="after")
    def complete(self) -> Self:
        if set(self.per_million) != set(TOKEN_CATEGORIES):
            raise ValueError("Require explicit prices for all non-overlapping token categories")
        if any(not p.is_finite() or p < 0 for p in self.per_million.values()):
            raise ValueError("Prices must be finite and nonnegative")
        return self

    @property
    def table_hash(self) -> str:
        return digest(self)

    def estimate(self, usage: dict[str, int], *, today: date, max_age_days: int = 90) -> Decimal:
        age = (today - self.effective_date).days
        if not 0 <= age <= max_age_days:
            raise BudgetError("Price table is future-dated or stale")
        if set(usage) != set(TOKEN_CATEGORIES) or any(
            type(n) is not int or n < 0 for n in usage.values()
        ):
            raise BudgetError("Conservative reservation requires every exclusive token category")
        return sum(
            (
                Decimal(usage[k]) * self.per_million[k] / Decimal(1_000_000)
                for k in TOKEN_CATEGORIES
            ),
            start=Decimal(0),
        )


class BudgetPolicy(Contract):
    budget_usd: Decimal = Field(gt=0)
    max_calls: int = Field(ge=1)
    max_output_tokens: int = Field(ge=1)
    max_concurrency: int = Field(ge=1)
    approval_id: str = Field(min_length=1)
    price_table_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    strict_dollar_cap: bool = True
    provider_accounting: Literal["transparent", "opaque"] = "transparent"

    @model_validator(mode="after")
    def enforceable(self) -> Self:
        if not self.budget_usd.is_finite():
            raise ValueError("Budget must be finite")
        if self.provider_accounting == "opaque" and self.strict_dollar_cap:
            raise ValueError("Opaque CLI cannot guarantee an exact dollar hard cap")
        return self


class Reservation(Contract):
    request_id: str = Field(min_length=1)
    payload_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    output_tokens: int = Field(ge=0)
    reserved_usd: Decimal = Field(ge=0)
    actual_usd: Decimal | None = Field(default=None, ge=0)
    state: Literal["reserved", "dispatched", "uncertain", "settled", "released"]
    reason: str | None = None

    @model_validator(mode="after")
    def retained_charge(self) -> Self:
        if (self.state == "settled") != (self.actual_usd is not None):
            raise ValueError("Only settled reservations have authoritative actual charges")
        if self.state == "uncertain" and not self.reason:
            raise ValueError("Uncertain charge needs a reason and retained reservation")
        return self


class LedgerEvent(Contract):
    sequence: int = Field(ge=1)
    request_id: str
    action: Literal["reserve", "dispatch", "uncertain", "settle", "release"]
    amount: Decimal | None
    reason: str | None = None


class LedgerState(Contract):
    policy_hash: str
    reservations: tuple[Reservation, ...] = ()
    events: tuple[LedgerEvent, ...] = ()
    breached: bool = False

    @model_validator(mode="after")
    def valid_history(self) -> Self:
        if len({r.request_id for r in self.reservations}) != len(self.reservations):
            raise ValueError("Duplicate ledger request IDs")
        if [e.sequence for e in self.events] != list(range(1, len(self.events) + 1)):
            raise ValueError("Ledger history is not contiguous")
        return self

    @property
    def spent_usd(self) -> Decimal:
        return sum((r.actual_usd or Decimal(0) for r in self.reservations), start=Decimal(0))

    @property
    def outstanding_usd(self) -> Decimal:
        return sum(
            (
                r.reserved_usd
                for r in self.reservations
                if r.state in {"reserved", "dispatched", "uncertain"}
            ),
            start=Decimal(0),
        )

    @property
    def exposure_usd(self) -> Decimal:
        return self.spent_usd + self.outstanding_usd


def new_ledger(policy: BudgetPolicy) -> LedgerState:
    return LedgerState(policy_hash=digest(policy))


def _check(state: LedgerState, policy: BudgetPolicy) -> None:
    if state.policy_hash != digest(policy):
        raise BudgetError("Policy drift: use a new ledger")


def _transition(
    state: LedgerState,
    reservation: Reservation,
    action: str,
    amount: Decimal | None,
    reason: str | None = None,
    *,
    breached: bool = False,
) -> LedgerState:
    rows = tuple(r for r in state.reservations if r.request_id != reservation.request_id)
    event = LedgerEvent.model_validate(
        {
            "sequence": len(state.events) + 1,
            "request_id": reservation.request_id,
            "action": action,
            "amount": amount,
            "reason": reason,
        }
    )
    return LedgerState(
        policy_hash=state.policy_hash,
        reservations=rows + (reservation,),
        events=state.events + (event,),
        breached=state.breached or breached,
    )


def reserve(
    state: LedgerState,
    policy: BudgetPolicy,
    request_id: str,
    amount: Decimal,
    *,
    output_tokens: int,
    payload_hash: str | None = None,
) -> LedgerState:
    _check(state, policy)
    if not amount.is_finite() or amount < 0:
        raise BudgetError("Invalid reservation amount")
    if not 0 <= output_tokens <= policy.max_output_tokens:
        raise BudgetError("Output token limit exceeded")
    existing = next((r for r in state.reservations if r.request_id == request_id), None)
    if existing:
        if (existing.reserved_usd, existing.payload_hash, existing.output_tokens) != (
            amount,
            payload_hash,
            output_tokens,
        ):
            raise BudgetError("Idempotency key reused with a different payload/reservation")
        return state
    active = sum(r.state in {"reserved", "dispatched", "uncertain"} for r in state.reservations)
    if state.breached or state.exposure_usd + amount > policy.budget_usd:
        raise BudgetError("Budget exhausted: refusing new dispatch")
    if len(state.reservations) >= policy.max_calls or active >= policy.max_concurrency:
        raise BudgetError("Call or concurrency limit exceeded")
    return _transition(
        state,
        Reservation(
            request_id=request_id,
            reserved_usd=amount,
            state="reserved",
            output_tokens=output_tokens,
            payload_hash=payload_hash,
        ),
        "reserve",
        amount,
    )


def mark_dispatched(state: LedgerState, policy: BudgetPolicy, request_id: str) -> LedgerState:
    _check(state, policy)
    row = _find(state, request_id)
    if row.state != "reserved":
        raise BudgetError("Dispatch already consumed or released; never replay provider inference")
    return _transition(state, row.model_copy(update={"state": "dispatched"}), "dispatch", None)


def _find(state: LedgerState, request_id: str) -> Reservation:
    for row in state.reservations:
        if row.request_id == request_id:
            return row
    raise BudgetError("Unknown request id")


def reconcile(
    state: LedgerState,
    policy: BudgetPolicy,
    request_id: str,
    actual_usd: Decimal | None,
    *,
    reason: str | None = None,
) -> LedgerState:
    _check(state, policy)
    row = _find(state, request_id)
    if row.state == "released":
        raise BudgetError("Cannot charge a released reservation")
    if row.state == "settled":
        if row.actual_usd != actual_usd:
            raise BudgetError("Conflicting settlement")
        return state
    if row.state == "reserved":
        raise BudgetError("Dispatch must be persisted before provider access")
    if actual_usd is None:
        if not reason:
            raise BudgetError("Unknown usage needs a reason")
        if row.state == "uncertain" and row.reason == reason:
            return state
        return _transition(
            state,
            row.model_copy(update={"state": "uncertain", "reason": reason}),
            "uncertain",
            None,
            reason,
        )
    if not actual_usd.is_finite() or actual_usd < 0:
        raise BudgetError("Invalid charge")
    return _transition(
        state,
        row.model_copy(update={"state": "settled", "actual_usd": actual_usd, "reason": reason}),
        "settle",
        actual_usd,
        reason,
        breached=actual_usd > row.reserved_usd,
    )


def cancel(
    state: LedgerState,
    policy: BudgetPolicy,
    request_id: str,
    *,
    confirmed_not_dispatched: bool,
) -> LedgerState:
    _check(state, policy)
    row = _find(state, request_id)
    if row.state in {"released", "settled"}:
        return state
    if confirmed_not_dispatched and row.state == "reserved":
        return _transition(
            state,
            row.model_copy(update={"state": "released"}),
            "release",
            Decimal(0),
            "Confirmed no provider dispatch",
        )
    if row.state == "reserved":
        state = mark_dispatched(state, policy, request_id)
    return reconcile(state, policy, request_id, None, reason="Cancelled; charge unresolved")


class LocalLedger:
    """SQLite serializes load/transition/write; never replay an uncertain request."""

    def __init__(self, path: Path, policy: BudgetPolicy) -> None:
        self.path = path
        self.policy = policy
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=30)) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY, data TEXT)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO ledger VALUES (1, ?)",
                (new_ledger(policy).model_dump_json(),),
            )
            connection.commit()
        _check(self.read(), policy)

    def read(self) -> LedgerState:
        with closing(sqlite3.connect(self.path, timeout=30)) as connection:
            row = connection.execute("SELECT data FROM ledger WHERE id=1").fetchone()
        if row is None:
            raise BudgetError("Missing persisted ledger")
        return LedgerState.model_validate_json(row[0])

    def update(self, transition: Callable[[LedgerState], LedgerState]) -> LedgerState:
        with closing(sqlite3.connect(self.path, timeout=30, isolation_level=None)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute("SELECT data FROM ledger WHERE id=1").fetchone()
                if row is None:
                    raise BudgetError("Missing ledger")
                previous = LedgerState.model_validate_json(row[0])
                _check(previous, self.policy)
                updated = transition(previous)
                _check(updated, self.policy)
                connection.execute(
                    "UPDATE ledger SET data=? WHERE id=1", (updated.model_dump_json(),)
                )
                connection.execute("COMMIT")
            except BaseException:
                connection.execute("ROLLBACK")
                raise
        return updated
