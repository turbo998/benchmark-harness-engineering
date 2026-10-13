# Evidence-first methodology

This project is an original harness, not a reproduction of unpublished benchmark
creation scripts. The starter pack is **six API fixtures and three coding fixtures**:
an engineering pilot, not statistically sufficient evidence for choosing a model.
The default workflow calls no model and provisions no cloud resources.

## Roles and acceptance boundary

1. A designer freezes the task, output contract, difficulty, language, seed and recipe.
2. A generator may draft material, but cannot authorize its own oracle.
3. An independent critic checks accepted references and targeted wrong variants.
4. A deterministic controller records attempts, usage, costs and artifacts.
5. Independent rubric review remains separate from executable correctness.
6. Reports derive exclusively from saved, validated results—not LLM-invented numbers.

Template generation is free and reproducible. AI generation, grader calls, model
calls and Azure mutations require separately approved integration/configuration.
The current CLI refuses these unsupported live modes rather than silently mocking them.

The original coding acceptance checks execute only an allowlist of this project's
frozen reference/negative fixture programs on the host. They **do not validate a
Docker sandbox** and refuse arbitrary imported dataset/candidate code. Real agent
submissions require an independently validated container worker. Regeneration of
scores replays saved verifier attestations; it never executes saved candidate code.

## Frozen contracts and identity

`contracts.py` contains closed, typed Pydantic models; `schemas` contains their
serialization JSON Schemas. JSON Schema validates structure; Pydantic additionally
enforces cross-field identities, review/cost semantics and timestamp consistency.
Canonical UTF-8 JSON uses sorted keys, compact separators and no NaN/Infinity.
Case identity is its entire frozen content's SHA-256. Dataset identity sorts by case
ID before hashing, so shuffling does not change it.

Experiment identity binds:

- Dataset revision/hash, case IDs, split and generator/recipe version.
- Candidate/provider/model/deployment/resolved version, prompt hash, agent/scaffold version.
- Engine and scorer versions, scoring profile, repeat count, random order seed.
- Image digest, OS, region, local/Azure profile, warmup and cache policy.
- Retry ownership/limits, budget, approval and price-table identity.

Mock image digests identify a synthetic sentinel, **not a pulled Docker image**.
Local and Azure always have different cohort identities. API and agent latencies
are separate tracks within a cohort; different cache/warmup/image/region profiles
are not pooled. Changing any locked input requires a new experiment.

## Attempts, failures and resume

Every attempt has its own immutable request, numbered events, response/verifier
artifacts, result and SHA-256 receipt. Receipts validate the complete file set.
Archive paths use 16-character case-hash prefixes to accommodate Windows path
limits; full identities remain in records, and prefix collisions are rejected.
The archive is append-only through the application API, not a WORM/signature
guarantee against an operator who can rewrite every file.

Passed, failed, timeout, infrastructure/provider/quota/auth error, cancelled,
invalid case and review pending are distinct states. Errors retain phase timing,
usage provenance, charges and planned denominators. A wrong answer is not retried
until it passes. Only explicitly retryable infrastructure/provider/timeout failures
may be retried by the harness; framework-level destructive retries are not used.
Opaque engine retry behavior blocks live readiness.

Resume verifies the exact manifest and dataset. Completed attempts are untouched.
An interrupted mock request is retained and finalized as cancelled, with unknown
partial usage/cost and no automatic replay. A torn or tampered receipt blocks
reporting; it is not silently reconstructed as trustworthy evidence.

## Paid accounting: reusable policy API

`budget.py` exposes frozen `BudgetPolicy`, `PriceTable`, `Reservation`,
`LedgerEvent` and `LedgerState`, all using Decimal dollars. Pure transitions return
a new state:

```python
state = new_ledger(policy)
state = reserve(
    state, policy, request_id, conservative_usd,
    output_tokens=max_output, payload_hash=request_sha256,
)
state = mark_dispatched(state, policy, request_id)
# Persist state atomically BEFORE sending the request.
state = reconcile(state, policy, request_id, actual_usd, reason=None)
```

`reserve` binds the idempotency key to payload hash, maximum output count and
reservation amount. Matching duplicates return the existing state, **not permission
to replay inference**. `mark_dispatched` consumes dispatch authorization once and
refuses dispatched/uncertain/settled/released requests.

Unknown usage is `reconcile(..., None, reason=...)`; the reservation remains held.
`cancel(..., confirmed_not_dispatched=True)` releases only a still-reserved,
confirmed-unsent request. In-flight cancellation keeps uncertain exposure.
Settlement retains failed/retried charges; a charge above its reservation is
recorded and latches a breach that prevents new reservations.

`PriceTable` requires an effective date, source, exact model version, explicit prices
for all five **exclusive** token categories and checks freshness. Inclusive provider
input/output/reasoning fields must be converted without double counting before
pricing. No real price table is supplied or invented by the mock workflow.

`LocalLedger(path, policy).update(transition)` serializes SQLite
load/transition/write in one transaction; connections close explicitly on Windows.
A Blob-backed broker can reuse `LedgerState.model_dump_json()` /
`LedgerState.model_validate_json()` and the exact same pure transitions under an
ETag/lease compare-and-swap. Serialization alone is not atomic persistence.
Persist dispatch before HTTP access; never replay unresolved requests after restart.
The broker must bind approved models/deployments and enforce protocol, token,
request/concurrency, auth and payload limits separately.

Opaque native CLI usage cannot guarantee an exact dollar hard cap:
`BudgetPolicy(provider_accounting="opaque", strict_dollar_cap=True)` is invalid.
Paid live execution remains blocked until dated pricing, conservative
pre-reservation, approved candidate configuration, retry control and credential/
sandbox isolation are validated.

## Readiness and limits

Validated: original fixture acceptance, typed/frozen contracts, mock attempts,
local durable accounting, deterministic scoring and offline report regeneration.
promptfoo's no-network custom-provider smoke is a separate engine check, not a
live model benchmark. Harbor/Copilot Docker execution, isolated inference auth/
broker compatibility, paid smoke and cloud parity are separate readiness tiers.
No unexecuted tier is described as passed.
