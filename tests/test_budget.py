from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmark_harness.budget import (
    TOKEN_CATEGORIES,
    BudgetError,
    BudgetPolicy,
    LedgerState,
    LocalLedger,
    PriceTable,
    cancel,
    mark_dispatched,
    new_ledger,
    reconcile,
    reserve,
)


def policy(**overrides: object) -> BudgetPolicy:
    return BudgetPolicy.model_validate(
        {
            "budget_usd": "1",
            "max_calls": 10,
            "max_output_tokens": 100,
            "max_concurrency": 10,
            "approval_id": "unit-only",
            "price_table_hash": "a" * 64,
        }
        | overrides
    )


def test_reservation_settlement_idempotency_payload_and_retries() -> None:
    p = policy()
    state = new_ledger(p)
    state = reserve(state, p, "attempt-1", Decimal(".3"), output_tokens=50, payload_hash="1" * 64)
    assert state.exposure_usd == Decimal(".3")
    assert (
        reserve(state, p, "attempt-1", Decimal(".3"), output_tokens=50, payload_hash="1" * 64)
        == state
    )
    with pytest.raises(BudgetError, match="payload"):
        reserve(state, p, "attempt-1", Decimal(".3"), output_tokens=50, payload_hash="2" * 64)
    state = mark_dispatched(state, p, "attempt-1")
    with pytest.raises(BudgetError, match="never replay"):
        mark_dispatched(state, p, "attempt-1")
    state = reconcile(state, p, "attempt-1", Decimal(".2"))
    assert reconcile(state, p, "attempt-1", Decimal(".2")) == state
    with pytest.raises(BudgetError):
        reconcile(state, p, "attempt-1", Decimal(".1"))
    state = reserve(state, p, "retry-2", Decimal(".3"), output_tokens=50)
    state = mark_dispatched(state, p, "retry-2")
    state = reconcile(state, p, "retry-2", Decimal(".25"))
    assert state.spent_usd == Decimal(".45")
    assert len(state.events) == 6
    assert len(state.reservations) == 2


def test_uncertain_cancellation_and_restart_keep_reservation(workdir: Path) -> None:
    p = policy()
    ledger = LocalLedger(workdir / "ledger.sqlite", p)
    ledger.update(lambda s: reserve(s, p, "call", Decimal(".8"), output_tokens=50))
    ledger.update(lambda s: mark_dispatched(s, p, "call"))
    ledger.update(lambda s: reconcile(s, p, "call", None, reason="Lost provider reply"))
    state = LocalLedger(workdir / "ledger.sqlite", p).read()
    assert state.outstanding_usd == Decimal(".8") and state.spent_usd == 0
    assert cancel(state, p, "call", confirmed_not_dispatched=True).outstanding_usd == Decimal(".8")
    with pytest.raises(BudgetError):
        reserve(state, p, "next", Decimal(".3"), output_tokens=50)
    released = new_ledger(p)
    released = reserve(released, p, "unsent", Decimal(".8"), output_tokens=50)
    released = cancel(released, p, "unsent", confirmed_not_dispatched=True)
    assert released.exposure_usd == 0


def test_concurrent_atomic_reservations(workdir: Path) -> None:
    p = policy()
    path = workdir / "concurrent.sqlite"
    LocalLedger(path, p)

    def attempt(i: int) -> bool:
        try:
            LocalLedger(path, p).update(
                lambda s: reserve(s, p, str(i), Decimal(".3"), output_tokens=50)
            )
            return True
        except BudgetError:
            return False

    with ThreadPoolExecutor(max_workers=10) as pool:
        successes = list(pool.map(attempt, range(10)))
    assert sum(successes) == 3
    state = LocalLedger(path, p).read()
    assert state.exposure_usd == Decimal(".9")
    assert [e.sequence for e in state.events] == [1, 2, 3]
    assert LedgerState.model_validate_json(state.model_dump_json()) == state


def test_budget_overrun_records_charge_and_halts_new_dispatch() -> None:
    p = policy()
    state = reserve(new_ledger(p), p, "call", Decimal(".2"), output_tokens=50)
    with pytest.raises(BudgetError, match="Dispatch"):
        reconcile(state, p, "call", Decimal(".1"))
    state = mark_dispatched(state, p, "call")
    state = reconcile(state, p, "call", Decimal(".4"))
    assert state.breached and state.spent_usd == Decimal(".4")
    with pytest.raises(BudgetError):
        reserve(state, p, "next", Decimal(".1"), output_tokens=50)


def test_known_settlement_retains_invoice_evidence_and_prior_uncertainty() -> None:
    p = policy()
    state = reserve(new_ledger(p), p, "invoice-call", Decimal(".3"), output_tokens=50)
    state = mark_dispatched(state, p, "invoice-call")
    uncertain = reconcile(state, p, "invoice-call", None, reason="Provider reply lost")
    settled = reconcile(
        uncertain,
        p,
        "invoice-call",
        Decimal(".2"),
        reason="Invoice receipt sha256:" + "b" * 64,
    )
    assert settled.events[:-1] == uncertain.events
    assert settled.events[-2].reason == "Provider reply lost"
    assert settled.events[-1].action == "settle"
    assert settled.events[-1].reason == "Invoice receipt sha256:" + "b" * 64
    assert settled.reservations[0].reason == settled.events[-1].reason
    assert settled.reservations[0].state == "settled"
    assert settled.spent_usd == Decimal(".2") and settled.outstanding_usd == 0
    restored = LedgerState.model_validate_json(settled.model_dump_json())
    assert restored == settled
    assert (
        reconcile(restored, p, "invoice-call", Decimal(".2"), reason=settled.events[-1].reason)
        == restored
    )


@pytest.mark.parametrize("limit", [{"max_calls": 1}, {"max_concurrency": 1}])
def test_policy_limits(limit: dict[str, int]) -> None:
    p = policy(**limit)
    state = reserve(new_ledger(p), p, "first", Decimal(".1"), output_tokens=50)
    with pytest.raises(BudgetError, match="limit"):
        reserve(state, p, "second", Decimal(".1"), output_tokens=50)
    with pytest.raises(BudgetError, match="token"):
        reserve(state, p, "second", Decimal(".1"), output_tokens=101)
    with pytest.raises(BudgetError, match="drift"):
        reserve(state, policy(approval_id="different"), "other", Decimal(".1"), output_tokens=50)


def test_opaque_provider_cannot_claim_dollar_cap() -> None:
    with pytest.raises(ValidationError, match="Opaque"):
        policy(provider_accounting="opaque")
    assert not policy(provider_accounting="opaque", strict_dollar_cap=False).strict_dollar_cap


def test_dated_explicit_exclusive_prices() -> None:
    table = PriceTable(
        effective_date=date(2026, 10, 13),
        source="test-price-fixture-not-real",
        model_version="test-model",
        per_million={k: Decimal("1.25") for k in TOKEN_CATEGORIES},
    )
    assert table.estimate({k: 100 for k in TOKEN_CATEGORIES}, today=date(2026, 10, 13)) == Decimal(
        ".000625"
    )
    for day in (date(2026, 10, 12), date(2027, 10, 13)):
        with pytest.raises(BudgetError, match="stale"):
            table.estimate({k: 100 for k in TOKEN_CATEGORIES}, today=day)
    with pytest.raises(BudgetError):
        table.estimate({"input_tokens": 100}, today=date(2026, 10, 13))
    with pytest.raises(ValidationError):
        PriceTable.model_validate(table.model_dump() | {"per_million": {"input_tokens": "1"}})
