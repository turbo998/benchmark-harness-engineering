# Azure quickstart

This profile is opt-in and synthetic-data-only. It does **not** create a model
deployment or run a paid benchmark by default.

1. Complete the free local demo and freeze your dataset/manifest first.
2. Bind the approved subscription, region, image/SKU, inference deployment,
   protocol/limits, prices, budget, identity permissions and lifecycle owner.
3. Follow [Azure profile](azure.md) for offline/read-only preflight and Bicep
   compilation. Missing values block execution; examples are not ready accounts.
4. Validate what-if, role changes, egress and data-plane capabilities using the
   selected context; obtain separate approval before apply or paid smoke.
5. Export and verify full private evidence before any destructive cleanup.

The trusted broker must be built from this repo and pinned by image digest.
Install its declared SDKs with `uv sync --frozen --dev --extra azure`; invoke
broker commands through `uv run --frozen --extra azure python -m benchmark_harness.broker`.
See [broker accounting and operator commands](broker.md) before issuing credentials.
No public registry name/image availability or live Copilot-to-broker compatibility
is assumed. Do not run untrusted tasks in the broker or put its identity in
the worker. There is no production SLA/private-network/17-model availability
claim.
