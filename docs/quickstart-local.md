# Local quickstart: no-cost workflow

Requirements: Python 3.12, uv 0.10.6; Node >=22.22 only for optional promptfoo checks.
Run commands from your isolated clone/worktree, not another project's primary checkout.
Installation downloads public dependencies; evaluation/report tests themselves are offline.

```powershell
uv sync --frozen --dev
uv run --frozen benchmark-harness doctor
uv run --frozen benchmark-harness demo --output examples\mock-report
```

Open `examples\mock-report\report\index.html` directly. It is self-contained offline
HTML, clearly labelled synthetic. There are six API and three coding fixtures,
two mock candidates, two repetitions: 36 planned trials and 41 archived attempts,
including five retries. Actual model charges are zero. Synthetic chart dollars
and timings are not measured model performance.

## Individual steps

```powershell
uv run --frozen benchmark-harness generate --output .runs\samples
uv run --frozen benchmark-harness accept .runs\samples\cases.jsonl --output .runs\acceptance.json
uv run --frozen benchmark-harness plan .runs\samples\cases.jsonl --output .runs\plan.json
uv run --frozen benchmark-harness run .runs\plan.json .runs\samples\cases.jsonl --output .runs\run
uv run --frozen benchmark-harness score .runs\run --output .runs\scores.json
uv run --frozen benchmark-harness report .runs\run --output .runs\report
```

Run the identical `run` command again to resume without changing completed evidence.
Different datasets/manifests are refused; use a new experiment/output for drift.
Score/report regenerate saved results and do not invoke a model. `doctor` only
probes version/help; it does not install engines, deploy resources, change approval
configuration, or run inference.

## Release pins and current capability status

| Component | Pin / observed state | What is and is not validated |
|---|---|---|
| Harness | 0.1.0 | Offline fixtures, schemas, budget, attempts, scoring/report tests |
| promptfoo | **0.124.0**, npm lock | Actual version/eval help and original no-network provider smoke; no live provider/budget claim |
| Harbor | **0.24.0**, separate uv lock | Released wheel's task/trial/usage schema inspected and parser/config fixtures tested; installed Windows ARM CLI blocked by dependency builds |
| Copilot CLI | Observed **1.0.94-3** | No-cost version/help only; paid inference and sandbox/broker auth not validated |
| Harbor Copilot | Native `copilot-cli` present in 0.24.0 wheel | Discovery is source-verified, not assumed from research; integration/BYOK/live blocked |
| Docker | Missing on implementation host | Digest-pinned recipe and isolation/cancellation command tests only; no sandbox execution claimed |
| Azure | Separate parameterized profile | This workflow neither deploys nor tests live cloud inference |

Research source commits are evidence snapshots, **not installation release pins**.
The native Harbor Copilot adapter forwards hosted GitHub-token auth and may have
incomplete token/cost reporting; this does not establish safe broker compatibility.
No fake Copilot bridge success or strict opaque dollar-cap claim is made.

## Optional real promptfoo offline smoke

```powershell
npm ci --prefix engines --ignore-scripts --no-audit --no-fund
uv run --frozen benchmark-harness engine-config promptfoo samples\cases.jsonl --output .runs\engine
uv run --frozen benchmark-harness engine-smoke promptfoo samples\cases.jsonl --output .runs\engine-smoke
```

This uses an original local JS provider that returns frozen accepted fixtures,
with no HTTP/inference code, no inherited provider secrets, no sharing, no result
cache and no provider calls. Native CLI output is parsed, not replaced with fake
success if installation/execution fails. Engine-smoke is separate from the demo.
The harness does not enable native error-retry or resume commands.

**Windows ARM:** promptfoo's libsql 0.5.29 has no ARM Windows binding. The actual
offline smoke was validated using an isolated, pinned x64 Node 24.13.1 portable
runtime and matching x64 libsql binding inside `engines\runtime\node_modules`,
without changing the system runtime or permission settings. Package integrity
pins are in `engines\runtime-pins.json`; binaries/caches are not published.
Without a compatible installed runtime, the command fails explicitly. Linux/x64
or native Windows/x64 normally does not need this optional portable arrangement.
Harbor installation on Windows ARM remains blocked; use a separately validated
Linux Docker worker for its runtime probes, not a host-wide permissive fallback.

`engine-config harbor` is construction-only and `engine-smoke harbor` refuses to
claim execution. All `--live` paths and `generate --mode ai` are refused until their
explicit approval/pricing/accounting/isolation prerequisites are implemented.

## Validation

```powershell
uv run --frozen --extra azure pytest
uv run --frozen --extra azure ruff check src\benchmark_harness tests
uv run --frozen --extra azure ruff format --check src\benchmark_harness tests
uv run --frozen --extra azure mypy src\benchmark_harness
```

CI has no secrets, paid schedule, model invocation or cloud deployment.
The `azure` extra installs pinned SDKs for offline lease/error fixtures and typing;
these checks do not contact Azure. It is not needed for the core demo.
The core includes schema/cross-field rejection, reference/negative acceptance,
atomic budget concurrency/restart, retry/archive/hash/resume, isolation command,
golden metrics, offline chart regeneration and complete CLI E2E checks.
Native engine and Docker/cloud/live tiers are separately labelled rather than
fabricated by the default suite.
