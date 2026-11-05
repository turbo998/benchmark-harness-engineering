# Benchmark Harness Engineering (`benchmark-harness-engineering`)

[中文版 (README.md)](README.md) | **English**

An offline-first, provenance-sealed evaluation and visual report generation harness for **Coding Agents**, **API/LLM evaluations**, and **Routing/Decision models**.

---

## Key Capabilities

1. **Deterministic Offline Mock Loop (`paid_calls == 0`)**:
   - Sample generation (`generate`), acceptance checks (`accept`), frozen experiment manifests (`plan`), deterministic mock execution (`run`), scoring (`score`), and static SVG/HTML reporting (`report`).
   - Live/paid inference is explicitly refused (`exit code 2`) unless an approved live manifest with budget and dated price table hash is supplied.
2. **7-Card 4:5 Visual Report Deck Generator (`benchmark-harness cards`)**:
   - Renders self-contained `900px × 1125px` (`4:5` portrait) 7-card HTML decks with `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'` and zero external scripts or network requests.
   - Specification: [`docs/research/visual-report-card-format.md`](docs/research/visual-report-card-format.md) and [`docs/research/benchmark-report-system-prompt.md`](docs/research/benchmark-report-system-prompt.md).
   - Reference Decks:
     - **AIPC Edge Decision Model (Kev-0.8B / 4B) SFT, Calibration & Q8_0 GGUF (Supplement 7)**: [`examples/aipc-kev-sft-card-report/index.html`](examples/aipc-kev-sft-card-report/index.html) ([`report.json`](data/reported/routing-aipc-kev-sft/report.json) · [ZH](docs/reports/routing-aipc-kev-sft.md) · [EN](docs/reports/routing-aipc-kev-sft.en.md))
     - **Azure AMD MI300X Large MoE (Muse Spark 816B / Nemotron 3 Ultra 550B / Inkling 975B) BF16 & MXFP4 (Supplement 8)**: [`examples/moe-mi300x-card-report/index.html`](examples/moe-mi300x-card-report/index.html) ([`report.json`](data/reported/moe-mi300x-bf16-mxfp4/report.json) · [ZH](docs/reports/moe-mi300x-bf16-mxfp4.md) · [EN](docs/reports/moe-mi300x-bf16-mxfp4.en.md))
     - **Microsoft Agent Framework (MAF v1.0) vs. 6 Mainstream Frameworks**: [`examples/maf-multi-agent-card-report/index.html`](examples/maf-multi-agent-card-report/index.html) ([`report.json`](data/reported/maf-multi-agent-benchmark/report.json) · [ZH](examples/maf-multi-agent-card-report/test-report.md) · [EN](examples/maf-multi-agent-card-report/test-report.en.md))
     - **Gemini 4 Carbon (Supplement 6)**: [`examples/gemini-4-carbon-card-report/index.html`](examples/gemini-4-carbon-card-report/index.html)
     - **Strands Decider 2B**: [`examples/card-report/index.html`](examples/card-report/index.html)

---

## Historical Benchmark Report Archive (12 Report Families)

The [Ten-Report Index](docs/reports/README.md) and [Structured Reported Archive](data/reported/README.md) preserve anonymized, provenance-tagged transcriptions of historical benchmark evaluations (`provenance="anonymized_reported"`, `independently_reproduced=false`). Bilingual views and 7-card visual decks are indexed under [`data/reported/catalog.json`](data/reported/catalog.json) with arithmetic audits in [`data/reported/consistency.json`](data/reported/consistency.json).

| Report Family | Scope | Reports & Structured Data |
|---|---|---|
| **5-Model Coding Benchmark** | 11 tasks, 55 scored runs | [Report (ZH)](docs/reports/coding-five.md) · [JSON](data/reported/coding-five/report.json) |
| **10-Model Coding Supplement** | +55 runs (110 cumulative) | [Report (ZH)](docs/reports/coding-ten.md) · [JSON](data/reported/coding-ten/report.json) |
| **17-Model Coding Supplement (Supplement 4)** | +22 runs (187 cumulative) | [Report (ZH)](docs/reports/coding-seventeen.md) · [JSON](data/reported/coding-seventeen/report.json) |
| **19-Model Coding Supplement (Supplement 5)** | +22 runs adding `Claude Haiku 5.5` (`99.24`, `#2`, `$0.33`) & `Gemini 4 Argon` (`98.59`, `#12`, `1,310/1,310` hidden assertions) (209 cumulative) | [ZH](docs/reports/coding-nineteen.md) · [EN](docs/reports/coding-nineteen.en.md) · [JSON](data/reported/coding-nineteen/report.json) |
| **Gemini 4 Carbon Evaluation (Supplement 6)** | 16 official frontier benchmarks (`#1` on 14/16), 4 cybersecurity sub-leaderboards (`SEC-bench Pro 88.2%`, `ExploitGym 54.8%`, `CWE-bench 71.0%`, `Gray Swan IPI 0.0%`), alignment metrics; local CLI `A1–C4` pending (`null`) | [ZH](docs/reports/gemini-4-carbon.md) · [EN](docs/reports/gemini-4-carbon.en.md) · [7-Card Deck](examples/gemini-4-carbon-card-report/index.html) · [JSON](data/reported/gemini-4-carbon/report.json) |
| **Jev Routing Integration Notes** | Functional routing walkthrough | [Report (ZH)](docs/reports/routing-jev.md) · [JSON](data/reported/routing-jev/report.json) |
| **Laya / Jev / LLM Routing Comparison** | 20 requests, single pass | [Report (ZH)](docs/reports/routing-laya.md) · [JSON](data/reported/routing-laya/report.json) |
| **Decision-1 Four-Engine Comparison** | 40 requests × 3 repeats (480 decisions) | [Report (ZH)](docs/reports/routing-decision.md) · [JSON](data/reported/routing-decision/report.json) |
| **OpenJev Supplement Comparison** | 120 new decisions + baseline comparison | [Report (ZH)](docs/reports/routing-openjev.md) · [JSON](data/reported/routing-openjev/report.json) |
| **Strands Decider 2B Evaluation** | 7 scenarios (12 decisions), option-reversal robustness & batch latency | [Report (ZH)](docs/reports/routing-strands-decider.md) · [7-Card Deck](examples/card-report/index.html) · [JSON](data/reported/routing-strands-decider/report.json) |
| **AIPC Edge Decision Model (Kev-0.8B / 4B) SFT & GGUF (Supplement 7)** | Counterfactual SFT (`+31.5` to `+51.6 pts`), $T=2.83$ calibration, `Q8_0` GGUF (`775 MiB`, `2.1–2.6 GiB` CPU RAM, `386 ms` on Snapdragon X Elite) | [ZH](docs/reports/routing-aipc-kev-sft.md) · [EN](docs/reports/routing-aipc-kev-sft.en.md) · [7-Card Deck](examples/aipc-kev-sft-card-report/index.html) · [JSON](data/reported/routing-aipc-kev-sft/report.json) |
| **Azure AMD MI300X Large MoE BF16 & MXFP4 Validation (Supplement 8)** | `Muse Spark Open 816B-A42B`, `Nemotron 3 Ultra 550B-A55B`, and `Inkling 975B-A41B` on `Standard_ND96isr_MI300X_v5` (`317.4–348.6 tok/s` BF16; `-68.3%` weight RAM & 1-node `975B` in MXFP4) | [ZH](docs/reports/moe-mi300x-bf16-mxfp4.md) · [EN](docs/reports/moe-mi300x-bf16-mxfp4.en.md) · [7-Card Deck](examples/moe-mi300x-card-report/index.html) · [JSON](data/reported/moe-mi300x-bf16-mxfp4/report.json) |
| **Microsoft Agent Framework (MAF v1.0) Multi-Agent Benchmark** | 6 frameworks, 5 orchestration modes, 3-layer middleware, MCP/A2A v1.0, 7 scenarios (12 decisions), reversal robustness & fan-out latency | [ZH](examples/maf-multi-agent-card-report/test-report.md) · [EN](examples/maf-multi-agent-card-report/test-report.en.md) · [7-Card Deck](examples/maf-multi-agent-card-report/index.html) · [JSON](data/reported/maf-multi-agent-benchmark/report.json) |

---

## Quickstart (Offline Verification)

```bash
uv run benchmark-harness demo --output /tmp/benchmark-demo
uv run benchmark-harness cards data/reported/gemini-4-carbon/report.json --output examples/gemini-4-carbon-card-report/index.html
uv run pytest
```
