from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import pytest

from benchmark_harness.broker import (
    BlobStore,
    Broker,
    BrokerError,
    ChatRequest,
    Claims,
    MemoryStore,
    Message,
    Settings,
    issue_token,
    reconcile_run,
    seal_run,
)
from benchmark_harness.budget import BudgetError, BudgetPolicy, PriceTable

SECRET = b"synthetic-test-signing-secret-not-for-production"
NOW = 1800000000


def settings() -> Settings:
    return Settings(
        endpoint="https://synthetic.openai.azure.com",
        deployment="synthetic-deployment",
        model_name="synthetic",
        ledger_url="https://synthetic.blob.core.windows.net",
        ledger_container="ledger",
        api_version="synthetic-api",
        input_limit=1000,
        input_bound_verified=True,
        input_bound_source="synthetic provider context-window fixture",
        output_limit=100,
        prices=PriceTable(
            effective_date=date.today(),
            source="synthetic fixture",
            model_version="v1",
            per_million={
                "input_tokens": Decimal(2),
                "cache_read_tokens": Decimal(1),
                "cache_write_tokens": Decimal(2),
                "output_tokens": Decimal(4),
                "reasoning_tokens": Decimal(4),
            },
        ),
    )


def claims(config: Settings, *, concurrency: int = 1) -> Claims:
    return Claims(
        run_id="synthetic-run",
        expires_at=NOW + 100,
        target_hash=config.target_hash,
        policy=BudgetPolicy(
            budget_usd=Decimal("0.01"),
            max_calls=10,
            max_output_tokens=100,
            max_concurrency=concurrency,
            approval_id="synthetic-fixture",
            price_table_hash=config.prices.table_hash,
        ),
    )


def request() -> ChatRequest:
    return ChatRequest(
        model="synthetic-deployment",
        messages=(Message(role="user", content="synthetic input"),),
        max_completion_tokens=20,
    )


def response() -> dict[str, object]:
    return {
        "model": "synthetic-v1",
        "choices": [{"message": {"role": "assistant", "content": "synthetic"}}],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "prompt_tokens_details": {"cached_tokens": 5},
        },
    }


def test_valid_call_settles_exclusive_cache_and_total_output_cost() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)
    broker = Broker(config, SECRET, store, lambda _: response())
    broker.infer(issue_token(issued, SECRET), "r1", request(), now=NOW)
    ledger = store.documents[issued.run_id]
    assert ledger.state.spent_usd == Decimal("0.000075")
    assert ledger.state.outstanding_usd == 0
    assert len(ledger.traces) == 1
    assert "synthetic input" not in ledger.model_dump_json()
    assert SECRET.decode() not in ledger.model_dump_json()


def test_duplicate_request_never_replays_after_broker_restart() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)
    calls: list[int] = []

    def provider(_: ChatRequest) -> dict[str, object]:
        calls.append(1)
        return response()

    token = issue_token(issued, SECRET)
    Broker(config, SECRET, store, provider).infer(token, "r1", request(), now=NOW)
    with pytest.raises(BrokerError, match="no charged replay"):
        Broker(config, SECRET, store, provider).infer(token, "r1", request(), now=NOW)
    assert len(calls) == 1


def test_target_drift_cannot_reuse_an_existing_run_policy() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)
    Broker(config, SECRET, store, lambda _: response()).infer(
        issue_token(issued, SECRET),
        "r1",
        request(),
        now=NOW,
    )
    changed = config.model_copy(update={"endpoint": "https://other.openai.azure.com"})
    changed_claims = issued.model_copy(update={"target_hash": changed.target_hash})

    def forbidden(_: ChatRequest) -> dict[str, object]:
        raise AssertionError("Configuration drift dispatched")

    with pytest.raises(BrokerError, match="Configuration drift"):
        Broker(changed, SECRET, store, forbidden).infer(
            issue_token(changed_claims, SECRET),
            "r2",
            request(),
            now=NOW,
        )
    assert len(store.documents[issued.run_id].state.reservations) == 1


def test_old_credential_cannot_reset_budget_on_another_ledger() -> None:
    config = settings()
    issued = claims(config)
    changed = config.model_copy(update={"ledger_url": "https://other.blob.core.windows.net"})
    fresh_store = MemoryStore()

    def forbidden(_: ChatRequest) -> dict[str, object]:
        raise AssertionError("Changed ledger reset budget")

    with pytest.raises(BrokerError, match="different configuration"):
        Broker(changed, SECRET, fresh_store, forbidden).infer(
            issue_token(issued, SECRET),
            "r1",
            request(),
            now=NOW,
        )
    assert not fresh_store.documents


def test_unavailable_blob_ledger_never_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("azure.storage.blob", reason="Install the azure extra for SDK fixtures")
    from azure.core.exceptions import HttpResponseError
    from azure.storage import blob as sdk

    class Client:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def get_blob_client(self, *args: object) -> None:
            raise HttpResponseError("synthetic ledger outage")

    monkeypatch.setattr(sdk, "BlobServiceClient", Client)
    config = settings()
    issued = claims(config)
    store = BlobStore("https://synthetic.blob.core.windows.net", "ledger", operator=True)

    def forbidden(_: ChatRequest) -> dict[str, object]:
        raise AssertionError("Unpersisted reservation dispatched")

    with pytest.raises(BrokerError) as result:
        Broker(config, SECRET, store, forbidden).infer(
            issue_token(issued, SECRET),
            "r1",
            request(),
            now=NOW,
        )
    assert result.value.status == 503


def test_unknown_usage_and_cancellation_keep_reservation() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)
    broker = Broker(config, SECRET, store, lambda _: {"model": "synthetic-v1"})
    token = issue_token(issued, SECRET)
    with pytest.raises(BrokerError, match="reservation retained"):
        broker.infer(token, "r1", request(), now=NOW)
    before = store.documents[issued.run_id].state.exposure_usd
    broker.close(issued)
    assert before > 0
    assert store.documents[issued.run_id].state.exposure_usd == before
    with pytest.raises(BrokerError, match="closed"):
        broker.infer(token, "r2", request(), now=NOW)


def test_invalid_expired_or_wrong_target_token_never_dispatches() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)

    def forbidden(_: ChatRequest) -> dict[str, object]:
        raise AssertionError("Unauthorized inference")

    broker = Broker(config, SECRET, store, forbidden)
    with pytest.raises(BrokerError):
        broker.infer(issue_token(issued, b"x" * 32), "r1", request(), now=NOW)
    with pytest.raises(BrokerError):
        broker.infer(issue_token(issued, SECRET), "r1", request(), now=NOW + 100)
    wrong = issued.model_copy(update={"target_hash": "0" * 64})
    with pytest.raises(BrokerError):
        broker.infer(issue_token(wrong, SECRET), "r1", request(), now=NOW)
    assert not store.documents


def test_unknown_cache_count_is_not_zero_when_prices_differ() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)
    value = response()
    value["usage"] = {"prompt_tokens": 20, "completion_tokens": 10}
    broker = Broker(config, SECRET, store, lambda _: value)
    with pytest.raises(BrokerError):
        broker.infer(issue_token(issued, SECRET), "r1", request(), now=NOW)
    assert store.documents[issued.run_id].state.reservations[0].state == "uncertain"


def test_parallel_reservations_cannot_exceed_run_budget() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config, concurrency=10)
    policy = issued.policy.model_copy(update={"budget_usd": Decimal("0.00208")})
    issued = issued.model_copy(update={"policy": policy})
    broker = Broker(config, SECRET, store, lambda _: response())
    token = issue_token(issued, SECRET)

    def attempt(index: int) -> str:
        try:
            broker.infer(token, f"r{index}", request(), now=NOW)
            return "settled"
        except BudgetError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, (1, 2)))
    assert sorted(results) == ["blocked", "settled"]
    assert store.documents[issued.run_id].state.exposure_usd <= policy.budget_usd


def test_invalid_target_is_rejected_before_store_access() -> None:
    config = settings().model_copy(update={"endpoint": "https://unapproved.example"})
    with pytest.raises(BrokerError, match="endpoint"):
        Broker(config, SECRET, MemoryStore(), lambda _: response())


def test_seal_rejects_in_flight_and_preserves_uncertain_exposure() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)
    broker = Broker(config, SECRET, store, lambda _: response())

    def provider(_: ChatRequest) -> dict[str, object]:
        broker.close(issued)
        with pytest.raises(BrokerError, match="In-flight"):
            seal_run(store, issued)
        raise TimeoutError("synthetic provider timeout")

    broker.provider = provider
    with pytest.raises(BrokerError):
        broker.infer(issue_token(issued, SECRET), "r1", request(), now=NOW)
    sealed = seal_run(store, issued)
    assert sealed.sealed
    assert sealed.state.outstanding_usd > 0
    with pytest.raises(BrokerError, match="immutable"):
        reconcile_run(store, issued, "r1", Decimal("0"), "synthetic invoice")


def test_model_drift_keeps_reservation_instead_of_pricing_wrong_model() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)
    value = response()
    value["model"] = "unapproved-version"
    broker = Broker(config, SECRET, store, lambda _: value)
    with pytest.raises(BrokerError):
        broker.infer(issue_token(issued, SECRET), "r1", request(), now=NOW)
    assert store.documents[issued.run_id].state.reservations[0].state == "uncertain"


def test_over_reservation_breaches_and_blocks_future_dispatch() -> None:
    config, store = settings(), MemoryStore()
    issued = claims(config)
    value = response()
    value["usage"] = {
        "prompt_tokens": 1000000,
        "completion_tokens": 10,
        "prompt_tokens_details": {"cached_tokens": 0},
    }
    broker = Broker(config, SECRET, store, lambda _: value)
    token = issue_token(issued, SECRET)
    with pytest.raises(BrokerError, match="exceeded"):
        broker.infer(token, "r1", request(), now=NOW)
    ledger = store.documents[issued.run_id]
    assert ledger.state.breached
    assert ledger.state.spent_usd > issued.policy.budget_usd
    with pytest.raises(BudgetError):
        broker.infer(token, "r2", request(), now=NOW)


def test_blob_lease_persists_dispatch_before_provider_and_across_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("azure.storage.blob", reason="Install the azure extra for SDK fixtures")
    from azure.core.exceptions import ResourceExistsError
    from azure.storage import blob as sdk

    from benchmark_harness.broker import BrokerLedger

    class Download:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def readall(self) -> bytes:
            return self.data

    class Blob:
        def __init__(self) -> None:
            self.data: bytes | None = None
            self.leased = False

        def upload_blob(self, data: str, *, overwrite: bool, **kwargs: object) -> None:
            if not overwrite and self.data is not None:
                raise ResourceExistsError("synthetic existing ledger")
            if overwrite:
                assert self.leased and kwargs.get("lease") is self
            self.data = data.encode()

        def acquire_lease(self, *, lease_duration: int) -> "Blob":
            assert not self.leased and lease_duration == 60
            self.leased = True
            return self

        def download_blob(self, **kwargs: object) -> Download:
            assert self.leased and kwargs.get("lease") is self
            assert self.data is not None
            return Download(self.data)

        def release(self) -> None:
            assert self.leased
            self.leased = False

    persistent = Blob()

    class Client:
        def __init__(self, *args: object, **kwargs: object) -> None:
            assert kwargs["retry_total"] == 0

        def get_blob_client(self, container: str, name: str) -> Blob:
            assert name == "synthetic-run.json" and container == "ledger"
            return persistent

    monkeypatch.setattr(sdk, "BlobServiceClient", Client)
    config = settings()
    issued = claims(config)

    def provider(_: ChatRequest) -> dict[str, object]:
        assert persistent.data is not None and not persistent.leased
        document = BrokerLedger.model_validate_json(persistent.data)
        assert document.state.reservations[0].state == "dispatched"
        return response()

    store = BlobStore("https://synthetic.blob.core.windows.net", "ledger", operator=True)
    token = issue_token(issued, SECRET)
    Broker(config, SECRET, store, provider).infer(token, "r1", request(), now=NOW)
    restarted = BlobStore("https://synthetic.blob.core.windows.net", "ledger", operator=True)
    with pytest.raises(BrokerError, match="no charged replay"):
        Broker(config, SECRET, restarted, provider).infer(token, "r1", request(), now=NOW)
    assert not persistent.leased
