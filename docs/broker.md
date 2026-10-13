# Experimental inference broker

This is an Azure OpenAI **text-only, non-streaming chat-completions** broker, not a
general OpenAI-compatible proxy or a verified Copilot BYOK adapter. Real Azure
identity, storage leases, network access and model compatibility require a
separately approved live probe. Offline fixtures do not establish those capabilities.

The trusted broker alone holds an inference identity. Task environments receive
a short-lived HMAC run credential, not that identity, the signing key or Azure
management credentials. Each credential binds a deployment/configuration hash,
dated price-table hash, request count, output/concurrency limits and USD budget.
The Blob account/container namespace is also credential-bound, so moving a
broker to a fresh ledger does not reset an existing token's budget. The public
HTTP surface is `/health` and `/v1/chat/completions` only.

Requests require `Authorization: Bearer <private run credential>` and an
`Idempotency-Key`. The request uses `model`, text `messages`,
`max_completion_tokens` and optional `stream: false`. Tools, images, streaming,
arbitrary endpoints and deployment switching are rejected. An already dispatched
key returns an error, never a second paid call.

## Accounting and evidence

Input reservation covers the deployment's **entire verified maximum billable
context window**, not an operator's desired prompt length. Bind the authoritative
specification with `BROKER_CONTEXT_BOUND_SOURCE`, set `BROKER_INPUT_LIMIT` to that
upper bound and explicitly confirm `BROKER_CONTEXT_BOUND_VERIFIED=true`.
Unsupported context accounting is a live gate, not a guessed token estimator.
Output reservation uses the requested, separately verified hard completion cap.
This intentionally conservative policy can reject a small budget even when a
particular short prompt would cost less.

The live backend is a private Blob ledger, serialized with a lease and no SDK
retry. Reservation plus `dispatched` is persisted **before** inference. Usage
categories exclude cache reads from uncached input; completion includes reasoning
already reported in that total, avoiding double charging. Missing usage, unknown
cache splits, provider timeout or an unexposed/mismatched served version retain
the reservation. The reported model must exactly match the configured family and
version (`BROKER_MODEL_NAME` + `-` + `BROKER_MODEL_VERSION`); other wire formats
are unsupported until separately probed. Preflight requires `NoAutoUpgrade`.
A provider exceeding the reservation blocks further dispatch.
Do not enable live until these upper bounds and usage semantics have been probed.

Traces store hashes, timing, state and reported model, not prompts, responses,
access tokens or the signing secret. The controller still needs its separate
private attempt evidence bundle. `/health` validates configuration only; it does
not assert data-plane authentication or deployment readiness.

## Trusted operator commands

Install the declared SDK dependencies as well as the harness package. Save the
run's unsigned claims privately when issuing its credential. Never send the
claims file or signing secret to a task. `token` needs the configured
`BROKER_*` settings and signing secret; its stdout is a private credential.

```powershell
uv run --frozen --extra azure python -m benchmark_harness.broker close --claims C:\private-run\claims.json
uv run --frozen --extra azure python -m benchmark_harness.broker reconcile --claims C:\private-run\claims.json --request-id attempt-1 --actual-usd 0.003 --reason invoice-reference
uv run --frozen --extra azure python -m benchmark_harness.broker seal --claims C:\private-run\claims.json
```

These commands use the operator's Azure CLI credential and only need
`BROKER_BLOB_URL` and `BROKER_LEDGER_CONTAINER`, not the signing secret.
Reconciliation requires authoritative evidence; cancellation is not a refund.
Closing blocks new dispatch but does not imply all in-flight calls finished.
Sealing additionally refuses `reserved`/`dispatched` entries and makes further
operator reconciliation unavailable. Uncertain liabilities remain in the sealed
export. Export the sealed ledger and complete artifacts, then create the
[external proof receipt](azure.md#证据出口与清理). Privileged operators must not
edit a sealed blob directly.

`token` also requires `--claims-output` and `--settings-output` paths, written
without overwriting existing files. These private documents retain the run policy,
target identity and exact price/context metadata needed to reconstruct the
hashes; neither contains the signing secret. Token-price settlement is explicitly
`dated_token_price_estimate`, not a final Azure invoice. Keep the price source and
later invoice reconciliation evidence with the private run bundle.

## Container template

`environments\broker\Dockerfile` requires an explicit
`PYTHON_IMAGE=python:3.12-slim@sha256:<approved actual digest>` build argument.
Build from the repository root, scan the resulting image, then bind its actual
digest in Bicep. The broker runs as a non-root user. The image has not been
Docker-built in the current Windows environment; an image digest is never
fabricated. Public ingress is authenticated and suitable only for the approved
synthetic pilot; private/customer data requires a separate network profile.
