"""Experimental, deployment-bound inference gateway; no task execution."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import threading
import time
from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import Field, ValidationError

from benchmark_harness.budget import (
    BudgetError,
    BudgetPolicy,
    LedgerState,
    PriceTable,
    mark_dispatched,
    new_ledger,
    reconcile,
    reserve,
)
from benchmark_harness.contracts import Contract


class BrokerError(ValueError):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


class Message(Contract):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=16384)


class ChatRequest(Contract):
    model: str
    messages: tuple[Message, ...] = Field(min_length=1, max_length=64)
    max_completion_tokens: int = Field(ge=1)
    stream: Literal[False] = False


class Claims(Contract):
    run_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    expires_at: int
    target_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy: BudgetPolicy


class DispatchTrace(Contract):
    request_id: str
    payload_hash: str
    response_hash: str | None = None
    reported_model: str | None = None
    provider_seconds: float | None = None
    status: Literal["settled", "uncertain"]
    cost_basis: Literal["dated_token_price_estimate", "unknown"] = "unknown"
    reason: str | None = None


class BrokerLedger(Contract):
    schema_version: Literal[1] = 1
    policy: BudgetPolicy
    state: LedgerState
    target_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    dispatch_closed: bool = False
    sealed: bool = False
    traces: tuple[DispatchTrace, ...] = ()


class Store(Protocol):
    def update(
        self,
        run_id: str,
        policy: BudgetPolicy,
        transform: Callable[[BrokerLedger], BrokerLedger],
    ) -> BrokerLedger: ...


class MemoryStore:
    """Offline fixture backend; live serve always uses BlobStore."""

    def __init__(self) -> None:
        self.documents: dict[str, BrokerLedger] = {}
        self.lock = threading.RLock()

    def update(
        self,
        run_id: str,
        policy: BudgetPolicy,
        transform: Callable[[BrokerLedger], BrokerLedger],
    ) -> BrokerLedger:
        with self.lock:
            document = self.documents.get(
                run_id, BrokerLedger(policy=policy, state=new_ledger(policy))
            )
            if document.state.policy_hash != new_ledger(policy).policy_hash:
                raise BudgetError("Policy drift: use a new run")
            result = transform(document)
            self.documents[run_id] = result
            return result


class BlobStore:
    def __init__(self, account_url: str, container: str, *, operator: bool = False) -> None:
        from azure.identity import AzureCliCredential, ManagedIdentityCredential
        from azure.storage.blob import BlobServiceClient

        credential = (
            AzureCliCredential()
            if operator
            else ManagedIdentityCredential(client_id=os.environ["AZURE_CLIENT_ID"])
        )
        self.client = BlobServiceClient(
            account_url,
            credential=credential,
            retry_total=0,
            connection_timeout=5,
            read_timeout=15,
        )
        self.container = container
        self.account_url = account_url

    def update(
        self,
        run_id: str,
        policy: BudgetPolicy,
        transform: Callable[[BrokerLedger], BrokerLedger],
    ) -> BrokerLedger:
        from azure.core.exceptions import AzureError

        try:
            return self._update(run_id, policy, transform)
        except (AzureError, OSError, ValidationError) as error:
            raise BrokerError(
                "Durable ledger unavailable; dispatch/accounting status must be inspected",
                503,
            ) from error

    def _update(
        self,
        run_id: str,
        policy: BudgetPolicy,
        transform: Callable[[BrokerLedger], BrokerLedger],
    ) -> BrokerLedger:
        from azure.core.exceptions import ResourceExistsError
        from azure.storage.blob import ContentSettings

        blob = self.client.get_blob_client(self.container, f"{run_id}.json")
        initial = BrokerLedger(policy=policy, state=new_ledger(policy))
        try:
            blob.upload_blob(
                initial.model_dump_json(),
                overwrite=False,
                content_settings=ContentSettings(content_type="application/json"),
            )
        except ResourceExistsError:
            pass
        lease = blob.acquire_lease(lease_duration=60)
        try:
            document = BrokerLedger.model_validate_json(blob.download_blob(lease=lease).readall())
            if document.state.policy_hash != new_ledger(policy).policy_hash:
                raise BudgetError("Policy drift: use a new run")
            result = transform(document)
            blob.upload_blob(
                result.model_dump_json(),
                overwrite=True,
                lease=lease,
                content_settings=ContentSettings(content_type="application/json"),
            )
            return result
        finally:
            lease.release()


class Settings(Contract):
    endpoint: str
    deployment: str
    model_name: str = Field(min_length=1)
    ledger_url: str
    ledger_container: str = Field(
        min_length=3, max_length=63, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    api_version: str
    input_limit: int = Field(ge=1)
    input_bound_verified: Literal[True]
    input_bound_source: str = Field(min_length=1)
    output_limit: int = Field(ge=1)
    prices: PriceTable

    @property
    def target_hash(self) -> str:
        identity = (
            self.endpoint,
            self.deployment,
            self.model_name,
            self.ledger_url,
            self.ledger_container,
            self.api_version,
            self.input_limit,
            self.output_limit,
            self.input_bound_verified,
            self.input_bound_source,
            self.prices.table_hash,
        )
        return hashlib.sha256(json.dumps(identity).encode()).hexdigest()

    def check(self) -> None:
        if self.input_bound_verified is not True or not self.input_bound_source.strip():
            raise BrokerError("The deployment's maximum billable context bound must be verified")
        ledger = urlparse(self.ledger_url)
        if (
            ledger.scheme != "https"
            or not ledger.hostname
            or not ledger.hostname.endswith(".blob.core.windows.net")
            or ledger.username
            or ledger.password
            or ledger.path not in ("", "/")
            or ledger.query
            or ledger.fragment
        ):
            raise BrokerError("Unsupported durable ledger namespace")
        endpoint = urlparse(self.endpoint)
        try:
            port = endpoint.port
        except ValueError as error:
            raise BrokerError("Invalid endpoint port") from error
        if (
            endpoint.scheme != "https"
            or not endpoint.hostname
            or not endpoint.hostname.endswith(".openai.azure.com")
            or endpoint.username
            or endpoint.password
            or endpoint.path not in ("", "/")
            or endpoint.query
            or endpoint.fragment
            or port not in (None, 443)
        ):
            raise BrokerError("Unsupported or unapproved inference endpoint")
        self.prices.estimate(_tokens(0, 0, 0), today=date.today())
        rates = self.prices.per_million
        if rates["input_tokens"] <= 0 or rates["output_tokens"] <= 0:
            raise BrokerError("Nonzero authoritative input/output prices are required")
        if rates["cache_read_tokens"] > rates["input_tokens"]:
            raise BrokerError("Cache price exceeds conservative input reservation")


def _tokens(prompt: int, cached: int, completion: int) -> dict[str, int]:
    return {
        "input_tokens": prompt - cached,
        "cache_read_tokens": cached,
        "cache_write_tokens": 0,
        "output_tokens": completion,
        "reasoning_tokens": 0,
    }


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def issue_token(claims: Claims, secret: bytes) -> str:
    if len(secret) < 32:
        raise BrokerError("Signing secret must contain at least 32 bytes")
    encoded = _b64(claims.model_dump_json().encode())
    signature = hmac.digest(secret, encoded.encode(), "sha256")
    return f"{encoded}.{_b64(signature)}"


def verify_token(token: str, secret: bytes, settings: Settings, now: int) -> Claims:
    if len(secret) < 32 or len(token) > 8192:
        raise BrokerError("Invalid credential", 401)
    try:
        payload, signature = token.split(".")
        supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        expected = hmac.digest(secret, payload.encode(), "sha256")
        if not hmac.compare_digest(supplied, expected):
            raise BrokerError("Invalid credential", 401)
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        claims = Claims.model_validate_json(decoded)
    except (ValueError, binascii.Error, ValidationError) as error:
        raise BrokerError("Invalid credential", 401) from error
    if claims.expires_at <= now or claims.expires_at > now + 3600:
        raise BrokerError("Expired credential or unsupported lifetime", 401)
    if (
        claims.target_hash != settings.target_hash
        or claims.policy.price_table_hash != settings.prices.table_hash
        or claims.policy.provider_accounting != "transparent"
    ):
        raise BrokerError("Credential is bound to a different configuration", 403)
    return claims


def _usage_cost(response: dict[str, object], settings: Settings) -> Decimal:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        raise BrokerError("Authoritative usage is unavailable", 502)
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if type(prompt) is not int or type(completion) is not int:
        raise BrokerError("Authoritative usage is unavailable", 502)
    details = usage.get("prompt_tokens_details")
    cached = details.get("cached_tokens") if isinstance(details, dict) else None
    if cached is None:
        if (
            settings.prices.per_million["cache_read_tokens"]
            != settings.prices.per_million["input_tokens"]
        ):
            raise BrokerError("Cache usage is unknown; reservation retained", 502)
        cached = 0
    if type(cached) is not int or prompt < 0 or completion < 0 or not 0 <= cached <= prompt:
        raise BrokerError("Invalid provider usage", 502)
    return settings.prices.estimate(_tokens(prompt, cached, completion), today=date.today())


class Broker:
    def __init__(
        self,
        settings: Settings,
        secret: bytes,
        store: Store,
        provider: Callable[[ChatRequest], dict[str, object]],
    ) -> None:
        settings.check()
        if isinstance(store, BlobStore) and (
            store.account_url.rstrip("/") != settings.ledger_url.rstrip("/")
            or store.container != settings.ledger_container
        ):
            raise BrokerError("Store does not match the credential-bound ledger namespace")
        if len(secret) < 32:
            raise BrokerError("Signing secret must contain at least 32 bytes")
        self.settings, self.secret, self.store, self.provider = settings, secret, store, provider

    def infer(
        self,
        token: str,
        request_id: str,
        request: ChatRequest,
        *,
        now: int | None = None,
    ) -> dict[str, object]:
        self.settings.check()
        claims = verify_token(
            token, self.secret, self.settings, int(time.time()) if now is None else now
        )
        if not request_id or len(request_id) > 128:
            raise BrokerError("An Idempotency-Key of 1-128 characters is required")
        if request.model != self.settings.deployment:
            raise BrokerError("Only the bound deployment is allowed", 403)
        if request.max_completion_tokens > self.settings.output_limit:
            raise BrokerError("Verified completion-token bound exceeded")
        payload_hash = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        amount = self.settings.prices.estimate(
            _tokens(self.settings.input_limit, 0, request.max_completion_tokens),
            today=date.today(),
        )

        def begin(document: BrokerLedger) -> BrokerLedger:
            document = _bind_target(document, claims)
            if document.dispatch_closed:
                raise BrokerError("Run dispatch is closed", 403)
            existing = next(
                (r for r in document.state.reservations if r.request_id == request_id), None
            )
            if existing is not None:
                raise BrokerError(
                    "Already reserved/dispatched: no charged replay; inspect run evidence", 409
                )
            state = reserve(
                document.state,
                claims.policy,
                request_id,
                amount,
                output_tokens=request.max_completion_tokens,
                payload_hash=payload_hash,
            )
            state = mark_dispatched(state, claims.policy, request_id)
            return document.model_copy(update={"state": state})

        self.store.update(claims.run_id, claims.policy, begin)
        started = time.monotonic()
        try:
            response = self.provider(request)
            reported_model = response.get("model")
            expected_model = f"{self.settings.model_name}-{self.settings.prices.model_version}"
            if reported_model != expected_model:
                raise BrokerError("Provider does not expose the frozen served model version", 502)
            actual = _usage_cost(response, self.settings)
        except (BrokerError, BudgetError, HTTPError, URLError, TimeoutError, OSError) as error:
            reason = f"provider_or_usage_{type(error).__name__}"

            def uncertain(document: BrokerLedger) -> BrokerLedger:
                state = reconcile(document.state, claims.policy, request_id, None, reason=reason)
                trace = DispatchTrace(
                    request_id=request_id,
                    payload_hash=payload_hash,
                    provider_seconds=time.monotonic() - started,
                    status="uncertain",
                    reason=reason,
                )
                return document.model_copy(
                    update={"state": state, "traces": document.traces + (trace,)}
                )

            self.store.update(claims.run_id, claims.policy, uncertain)
            raise BrokerError(
                "Provider result/usage is unknown; reservation retained", 502
            ) from error

        def settle(document: BrokerLedger) -> BrokerLedger:
            state = reconcile(document.state, claims.policy, request_id, actual)
            trace = DispatchTrace(
                request_id=request_id,
                payload_hash=payload_hash,
                response_hash=hashlib.sha256(
                    json.dumps(response, sort_keys=True).encode()
                ).hexdigest(),
                reported_model=str(response.get("model", "unreported")),
                provider_seconds=time.monotonic() - started,
                status="settled",
                cost_basis="dated_token_price_estimate",
            )
            return document.model_copy(
                update={"state": state, "traces": document.traces + (trace,)}
            )

        final = self.store.update(claims.run_id, claims.policy, settle)
        if final.state.breached:
            raise BrokerError("Provider exceeded verified reservation; run is blocked", 502)
        return response

    def close(self, claims: Claims) -> None:
        close_run(self.store, claims)


def close_run(store: Store, claims: Claims) -> BrokerLedger:
    return store.update(
        claims.run_id,
        claims.policy,
        lambda document: _bind_target(document, claims).model_copy(
            update={"dispatch_closed": True}
        ),
    )


def seal_run(store: Store, claims: Claims) -> BrokerLedger:
    def seal(document: BrokerLedger) -> BrokerLedger:
        document = _bind_target(document, claims)
        if not document.dispatch_closed:
            raise BrokerError("Close dispatch before sealing", 409)
        if any(item.state in ("reserved", "dispatched") for item in document.state.reservations):
            raise BrokerError("In-flight dispatch prevents an immutable export", 409)
        return document.model_copy(update={"sealed": True})

    return store.update(claims.run_id, claims.policy, seal)


def reconcile_run(
    store: Store,
    claims: Claims,
    request_id: str,
    actual_usd: Decimal,
    reason: str,
) -> BrokerLedger:
    def apply(document: BrokerLedger) -> BrokerLedger:
        document = _bind_target(document, claims)
        if document.sealed:
            raise BrokerError("Sealed ledger is immutable; preserve the export", 409)
        state = reconcile(document.state, claims.policy, request_id, actual_usd, reason=reason)
        return document.model_copy(update={"state": state})

    return store.update(claims.run_id, claims.policy, apply)


def _bind_target(document: BrokerLedger, claims: Claims) -> BrokerLedger:
    if document.target_hash is not None and document.target_hash != claims.target_hash:
        raise BrokerError("Configuration drift requires a new run", 409)
    return document.model_copy(update={"target_hash": claims.target_hash})


def settings_from_env() -> Settings:
    if os.environ.get("BROKER_CONTEXT_BOUND_VERIFIED") != "true":
        raise BrokerError("Verify the deployment context bound before enabling inference")
    input_price = Decimal(os.environ["BROKER_INPUT_PRICE"])
    output_price = Decimal(os.environ["BROKER_OUTPUT_PRICE"])
    prices = PriceTable(
        effective_date=date.fromisoformat(os.environ["BROKER_PRICE_DATE"]),
        source=os.environ["BROKER_PRICE_SOURCE"],
        model_version=os.environ["BROKER_MODEL_VERSION"],
        per_million={
            "input_tokens": input_price,
            "cache_read_tokens": Decimal(os.environ["BROKER_CACHED_INPUT_PRICE"]),
            "cache_write_tokens": input_price,
            "output_tokens": output_price,
            "reasoning_tokens": output_price,
        },
    )
    return Settings(
        endpoint=os.environ["BROKER_MODEL_ENDPOINT"],
        deployment=os.environ["BROKER_DEPLOYMENT"],
        model_name=os.environ["BROKER_MODEL_NAME"],
        ledger_url=os.environ["BROKER_BLOB_URL"],
        ledger_container=os.environ["BROKER_LEDGER_CONTAINER"],
        api_version=os.environ["BROKER_API_VERSION"],
        input_limit=int(os.environ["BROKER_INPUT_LIMIT"]),
        input_bound_verified=True,
        input_bound_source=os.environ["BROKER_CONTEXT_BOUND_SOURCE"],
        output_limit=int(os.environ["BROKER_OUTPUT_LIMIT"]),
        prices=prices,
    )


def azure_provider(settings: Settings) -> Callable[[ChatRequest], dict[str, object]]:
    from azure.core.exceptions import AzureError
    from azure.identity import ManagedIdentityCredential

    credential = ManagedIdentityCredential(client_id=os.environ["AZURE_CLIENT_ID"])
    url = (
        f"{settings.endpoint.rstrip('/')}/openai/deployments/"
        f"{quote(settings.deployment, safe='')}/chat/completions"
        f"?api-version={quote(settings.api_version, safe='')}"
    )

    def invoke(chat: ChatRequest) -> dict[str, object]:
        try:
            token = credential.get_token("https://cognitiveservices.azure.com/.default").token
        except AzureError as error:
            raise BrokerError("Inference identity could not be obtained", 502) from error
        request = Request(
            url,
            data=chat.model_dump_json(exclude={"model"}).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )

        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(
                self,
                req: Request,
                fp: object,
                code: int,
                msg: str,
                headers: object,
                newurl: str,
            ) -> None:
                return None

        try:
            with build_opener(NoRedirect()).open(request, timeout=90) as response:
                value = json.loads(response.read())
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise BrokerError("Malformed provider JSON; usage is unknown", 502) from error
        if not isinstance(value, dict):
            raise BrokerError("Malformed provider response", 502)
        return {str(key): item for key, item in value.items()}

    return invoke


def serve(broker: Broker, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            self.connection.settimeout(15)
            super().setup()

        def log_message(self, format: str, *args: object) -> None:
            return

        def reply(self, status: int, value: dict[str, object]) -> None:
            content = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self) -> None:
            if self.path != "/health":
                self.reply(404, {"error": "not_found"})
                return
            try:
                broker.settings.check()
            except (BrokerError, BudgetError) as error:
                self.reply(503, {"error": str(error)})
                return
            self.reply(200, {"status": "configured; live capabilities require separate validation"})

        def do_POST(self) -> None:
            if self.path != "/v1/chat/completions":
                self.reply(404, {"error": "not_found"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536:
                    raise BrokerError("Request body must be 1-65536 bytes")
                authorization = self.headers.get("Authorization", "")
                if not authorization.startswith("Bearer "):
                    raise BrokerError("Authentication required", 401)
                verify_token(authorization[7:], broker.secret, broker.settings, int(time.time()))
                chat = ChatRequest.model_validate_json(self.rfile.read(size))
                value = broker.infer(
                    authorization[7:],
                    self.headers.get("Idempotency-Key", ""),
                    chat,
                )
            except BrokerError as error:
                self.reply(error.status, {"error": str(error)})
                return
            except BudgetError as error:
                self.reply(402, {"error": str(error)})
                return
            except TimeoutError:
                self.reply(408, {"error": "Request body deadline exceeded"})
                return
            except (ValidationError, ValueError) as error:
                self.reply(400, {"error": type(error).__name__})
                return
            self.reply(200, value)

    with ThreadingHTTPServer(("0.0.0.0", port), Handler) as server:
        server.serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    server = subcommands.add_parser("serve")
    server.add_argument("--port", type=int, default=8080)
    issuer = subcommands.add_parser("token")
    issuer.add_argument("--run-id", required=True)
    issuer.add_argument("--budget-usd", type=Decimal, required=True)
    issuer.add_argument("--max-calls", type=int, required=True)
    issuer.add_argument("--max-output-tokens", type=int, required=True)
    issuer.add_argument("--max-concurrency", type=int, default=1)
    issuer.add_argument("--approval-id", required=True)
    issuer.add_argument("--claims-output", type=Path, required=True)
    issuer.add_argument("--settings-output", type=Path, required=True)
    issuer.add_argument("--expires-seconds", type=int, choices=range(1, 3601), default=900)
    for command in ("close", "seal", "reconcile"):
        operator = subcommands.add_parser(command)
        operator.add_argument(
            "--claims", type=argparse.FileType("r", encoding="utf-8"), required=True
        )
        if command == "reconcile":
            operator.add_argument("--request-id", required=True)
            operator.add_argument("--actual-usd", type=Decimal, required=True)
            operator.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    if args.command in ("close", "seal", "reconcile"):
        claims = Claims.model_validate_json(args.claims.read())
        args.claims.close()
        store = BlobStore(
            os.environ["BROKER_BLOB_URL"],
            os.environ["BROKER_LEDGER_CONTAINER"],
            operator=True,
        )
        if args.command == "close":
            document = close_run(store, claims)
        elif args.command == "seal":
            document = seal_run(store, claims)
        else:
            document = reconcile_run(store, claims, args.request_id, args.actual_usd, args.reason)
        print(
            json.dumps(
                {
                    "dispatch_closed": document.dispatch_closed,
                    "sealed": document.sealed,
                    "exposure_usd": str(document.state.exposure_usd),
                }
            )
        )
        return 0
    settings = settings_from_env()
    settings.check()
    secret = os.environ["BROKER_SIGNING_SECRET"].encode()
    if args.command == "token":
        policy = BudgetPolicy(
            budget_usd=args.budget_usd,
            max_calls=args.max_calls,
            max_output_tokens=args.max_output_tokens,
            max_concurrency=args.max_concurrency,
            approval_id=args.approval_id,
            price_table_hash=settings.prices.table_hash,
        )
        claims = Claims(
            run_id=args.run_id,
            expires_at=int(time.time()) + args.expires_seconds,
            target_hash=settings.target_hash,
            policy=policy,
        )
        for destination, text in (
            (args.claims_output, claims.model_dump_json(indent=2)),
            (args.settings_output, settings.model_dump_json(indent=2)),
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(text)
        print(issue_token(claims, secret))
    else:
        store = BlobStore(os.environ["BROKER_BLOB_URL"], os.environ["BROKER_LEDGER_CONTAINER"])
        serve(Broker(settings, secret, store, azure_provider(settings)), args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
