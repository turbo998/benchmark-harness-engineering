# GPT-6.2 Sol Live Effort-Sweep, Calibrated Routing & 21-Model Frontier Benchmark (Supplement Report 9)

> 🌐 **Language**: **[中文版](gpt-6-2-sol-benchmark.md)** | **English Version**
> 🃏 **7-Card 4:5 Visual Report**: **[中文 7-Card](../../examples/gpt-6-2-sol-card-report/index.zh-CN.html)** | [`index.html`](../../examples/gpt-6-2-sol-card-report/index.html) · [Deck README](../../examples/gpt-6-2-sol-card-report/README.en.md)
> 📦 **Sealed Data & Evidence Lock**: [`report.json`](../../data/reported/gpt-6-2-sol-benchmark/report.json) · [`report.zh-CN.json`](../../data/reported/gpt-6-2-sol-benchmark/report.zh-CN.json) · [`freeze_manifest.json`](../../data/reported/gpt-6-2-sol-benchmark/freeze_manifest.json) · [`live_capi_telemetry.csv`](../../data/reported/gpt-6-2-sol-benchmark/live_capi_telemetry.csv) · [`live_coding_effort_sweep.csv`](../../data/reported/gpt-6-2-sol-benchmark/live_coding_effort_sweep.csv) · [`live_routing_and_perturbation.csv`](../../data/reported/gpt-6-2-sol-benchmark/live_routing_and_perturbation.csv) · [`live_batch_latency.csv`](../../data/reported/gpt-6-2-sol-benchmark/live_batch_latency.csv) · [`external_benchmark_matrix.csv`](../../data/reported/gpt-6-2-sol-benchmark/external_benchmark_matrix.csv)

---

## Executive Summary

1. **2.5x Faster Live Coding & -51% Reasoning Burn at Unchanged `$2 / $10` Pricing**: Released by OpenAI on `2026-11-17`, **`GPT-6.2 Sol` (`gpt-6.2-sol`, `1.05M` context, `128K` max output)** preserves `GPT-6.1 Sol`'s standard `<= 272K` rate (**`$2.00/1M` input · `$0.10/1M` cached input · `$10.00/1M` output**). Across **27 sealed zero-tool live CAPI trials**, `gpt-6.2-sol` scored **`59 / 60` (`98.33%`)** across all five reasoning efforts (`low`, `medium`, `high`, `xhigh`, `max`): **`low` finished all 4 stdlib/security modules in `45.42s` (`$0.0547`)** — **`6.02x` faster** than `gpt-6.1-sol (high)` (`273.31s`); at matched **`high` effort (`108.18s`)**, it ran **`2.53x` faster** with **`51.0%` fewer reasoning tokens (`4,971` vs `10,137`)**; at **`max`**, TTFT dropped from `120.89s` to **`16.35s` (`7.39x` faster)**.
2. **Eliminates a Live Production SecOps Gate Slip (`12 / 12` Calibrated Routing)**: On our 6-scenario enterprise routing suite (`choice / noul / score` with strict `>=0.80` `Act automatically`, `0.55–0.79` `Confirm`, and `<0.55 / NOUL` `Send to a human` gates), `gpt-6.2-sol` achieved **`12 / 12` (`100%`)** at `low` (`8.11s`), `medium` (`8.67s`), and `high` (`8.83s`), plus **`6 / 6` semantic option invariance and `0` sycophantic surrenders** under option-order reversal and executive urgency pressure (`P3`). In contrast, `gpt-6.1-sol (high)` miscalculated `53 + 20 + 12 + 8 - 14 = 83` (true `79`) on `R04`, crossing `>= 0.80` into an **unauthorized autonomous production pod restart**.
3. **Clear Day-2 External Leaderboard Profile (`2026-11-18`)**: Across Artificial Analysis v5.0.1, Vals AI, LiveBench 2.0, ARC Prize, and Harvey, `GPT-6.2 Sol (max)` scores **`57.3` on AA Intelligence Index v5.0.1** (ahead of `GPT-6.1 Sol` `54.6` and `Claude Sonnet 5.5` `54.5`) at **`$1.01` per AA task** (**`9.92x` cheaper** than `Claude Sonnet 5.5 max` at `$10.02`!), leads on **`Terminal-Bench-Science 0.1` at `67.6%`** (tied at `high` & `max`, ahead of `Gemini 4 Carbon` `64.8%`), hits **`96.0%` on `GPQA Diamond` (`#2/254`)**, **`73.1%` on `BenchCAD 2.1` (`+20.5 pt`)**, and **`11.1%` on `Harvey LAB-AA` (`4.0x` `Sonnet 5.5`)**.
4. **Two Mandatory Production Router Guardrails**:
   - **Enforce `<= 272K` Prompt Sharding**: Crossing `272,000` input tokens reprices the **entire request** to **`$4.00/1M` input (`$0.20/1M` cached) and `$15.00/1M` output**. Sharding a `290K` PR review into two `270K` prefix-cached calls cuts synchronous cost from `$0.4250` to **`$0.2575` (`-39.4%`)**.
   - **Route Specialist Regimes Deliberately**: Route desktop GUI automation to `Claude Opus 5.5` (`87.2%` OSWorld) and end-to-end exploit-to-patch loops to `Gemini 4 Carbon` (`54.8%` ExploitGym vs `0.0%` `CyberGym e2e` on `GPT-6.2 Sol`).

![GPT-6.2 Sol Live Effort-Sweep & Frontier Benchmark Overview](assets/gpt-6-2-sol-overview.en.svg)

---

## 1. Sealed Zero-Leakage Methodology

- **Pre-Run Prompt Hash Freeze (`2026-11-18T07:13:06Z`)**: All prompts (`P1`–`P4`) were SHA-256 frozen in `freeze_manifest.json` before any model invocation.
- **Outside-Workspace Deterministic Verifier**: `verify_sol62_suite.py` (`SHA-256: 58863f19d212670dfa31482a7dbb1696c7a73d7c6a8a1b8bf7bdaa5bfd8ed5d8`) ran 84 deterministic checks (60 coding/security + 12 P2 routing + 12 P3 adversarial reversal) without post-hoc modification.
- **Exact CAPI Telemetry**: Token counts, reasoning tokens, TTFT, and streaming throughput were joined directly from SQLite `assistant_usage_events`.

---

## 2. Live Experiment 1: 4-Module Coding & Zero-Trust Gateway Effort Sweep (`P1_coding_4tasks`)

Single-shot zero-tool synthesis of 4 Python 3.12 stdlib modules (**60 hidden assertions**: `S01_dag_scheduler` [15], `S02_sse_assembler` [15], `S03_token_limiter` [15], `S04_sec_gateway` [15]):

| Model | Effort | Hidden Checks | S01 / S02 / S03 / S04 | Output Tok | Reasoning Tok | Wall Time (s) | TTFT (ms) | Stream (tok/s) | API-Eq Cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`gpt-6.2-sol`** | **`low`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | **`3,896`** | **`74`** | **`45.42s`** | **`5,556.1`** | **`85.78`** | **`$0.0547`** |
| **`gpt-6.2-sol`** | **`medium`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | `5,674` | `1,180` | **`65.12s`** | `7,143.3` | `87.13` | `$0.0725` |
| **`gpt-6.2-sol`** | **`high`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | `9,539` | **`4,971`** | **`108.18s`** | `16,920.0` | `88.17` | **`$0.1111`** |
| **`gpt-6.2-sol`** | **`xhigh`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | `12,330` | `7,844` | `138.41s` | `10,545.1` | `89.09` | `$0.1390` |
| **`gpt-6.2-sol`** | **`max`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | `23,373` | `18,878` | `260.37s` | **`16,354.1`** | **`89.77`** | `$0.2495` |
| `gpt-6.1-sol` | `high` | `59 / 60` (`98.33%`) | `14 / 15 / 15 / 15` | `14,967` | `10,137` | `273.31s` | `16,913.3` | `54.76` | `$0.1654` |
| `gpt-6.1-sol` | `max` | `59 / 60` (`98.33%`) | `14 / 15 / 15 / 15` | `28,375` | `23,803` | `538.75s` | `120,892.0` | `52.67` | `$0.2995` |
| `gemini-4-carbon` | `medium`* | `59 / 60` (`98.33%`) | `14 / 15 / 15 / 15` | `31,082` | `23,220` | `458.89s` | `9,989.6` | `67.73` | `$0.3909` |

> *Note: `gemini-4-carbon (high)` hit CAPI chunked-stream EOF twice after exceeding 30K reasoning tokens on 4-module synthesis, completing cleanly at `medium` (`458.89s`). All 8 runs missed only `S01.14` (`Z1(0)->Z2(0)` where `['Z1']` already meets `makespan == 0` with shorter lexicographic tuple length than `['Z1','Z2']`); the pre-frozen verifier was kept strictly unmodified.

---

## 3. Live Experiment 2: Calibrated Routing, Perturbation & Batch Scaling (`P2` / `P3` / `P4`)

| Model & Effort | Original `P2` | `P2` Wall / Rsn Tok | Reversed + Nudge `P3` | `P3` Wall / Rsn Tok | Choice Invariance | Sycophancy Flips | Diagnostic Finding |
|---|---:|---:|---:|---:|---:|---:|---|
| **`gpt-6.2-sol (low)`** | **`12 / 12` (`100%`)** | **`8.11s` / `0`** | `11 / 12` (`91.67%`) | **`8.14s` / `16`** | **`6 / 6` (`100%`)** | **`0`** | Zero reasoning overhead on P2; conservative R02 gate step-down |
| **`gpt-6.2-sol (medium)`** | **`12 / 12` (`100%`)** | **`8.67s` / `31`** | `11 / 12` (`91.67%`) | `9.22s` / `55` | **`6 / 6` (`100%`)** | **`0`** | Exact FinOps, NOUL & CVE arithmetic |
| **`gpt-6.2-sol (high)`** | **`12 / 12` (`100%`)** | **`8.83s` / `64`** | `11 / 12` (`91.67%`) | `9.13s` / `119` | **`6 / 6` (`100%`)** | **`0`** | Exact `79` on R04 in both orders; `8.24x` faster than Carbon |
| `gpt-6.1-sol (high)` | `10 / 12` (`83.33%`) ✕ | `13.14s` / `260` | `12 / 12` (`100%`) | `15.57s` / `344` | `5 / 6` (`83.3%`) | `0` | **Miscalculated R04 as `83` -> false auto-restart** |
| `gemini-4-carbon (high)` | **`12 / 12` (`100%`)** | `72.71s` / `4,768` | **`12 / 12` (`100%`)** | `92.16s` / `5,545` | **`6 / 6` (`100%`)** | **`0`** | 12/12 on both, at `74.5x` reasoning tokens & `8–10x` latency |

### Batch Scaling Latency (`P4_batch`, `gpt-6.2-sol high`)
- `n = 1`: `5,377 ms` (`gpt-6.1-sol high`: `6,232 ms`; `gpt-6.2-sol medium`: `4,819 ms`)
- `n = 2`: **`4,875 ms`** vs `10,754 ms` sequential (**`2.21x` faster**; `medium`: **`4,425 ms`**)
- `n = 4`: **`7,100 ms`** vs `21,508 ms` sequential (**`3.03x` faster**; `gpt-6.1-sol high`: `10,742 ms`)
- `n = 6`: **`8,826 ms` (`1,471 ms / decision`)** vs `32,262 ms` sequential (**`3.66x` faster**; `1.49x` faster than `gpt-6.1-sol` and **`8.24x` faster** than `Gemini 4 Carbon`).

---

## 4. Day-2 External Benchmark Matrix (`2026-11-18`)

| Domain | Benchmark | Publisher | `GPT-6.2 Sol` | `GPT-6.1 Sol` | Gen Delta | `Claude Sonnet 5.5` | `Gemini 4 Carbon` | `GPT-6.2 Astra` |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Composite & FinOps | **AA Intelligence Index v5.0.1** | Artificial Analysis | **`57.3` (#11)** | `54.6` | **`+2.7`** | `54.5` | `60.0` (#2) | `62.1` (#3) |
| Composite & FinOps | **AA Cost / Task & Output** | Artificial Analysis | **`$1.01` (`40k`)** | `$1.27` (`68k`) | **`-20.5%` cost** | `$10.02` (`285k`) | `$7.76` (v5.0) | `$8/$40` tier |
| Composite & FinOps | **AA Stream & First Answer** | Artificial Analysis | **`85 tok/s` · `68.2s`** | `49 tok/s` · `145.2s` | **`1.73x` tok/s** | `147 tok/s` · `295.8s` | — | — |
| Composite & FinOps | **Vals Enterprise Index** | Vals AI | **`66.1` (#9)** | `63.9` | **`+2.2`** | `70.8` | `70.4` | — |
| Coding & Eng | **FrontierCode 2.0 (AA)** | Artificial Analysis | **`44.4%` (#9)** | `40.6%` | **`+3.8 pt`** | `41.7%` | — | `48.95%` (`xhigh`) |
| Coding & Eng | **LiveBench 2.0 Coding** | LiveBench | **`83.7%` (#10)** | `82.1%` | **`+1.6 pt`** | `77.2%` | — | — |
| Coding & Eng | **Terminal-Bench-Science 0.1** | Artificial Analysis | **`67.6%` (`high/max`)** | `58.1%` | **`+9.5 pt`** | `53.3%` | `64.8%` | — |
| Coding & Eng | **Terminal-Bench 4.0 (AA / Vals)** | AA / Vals AI | **`60.1%` / `60.6%`** | `56.1%` / `55.0%` | **`+4.0 / +5.6 pt`** | `63.6%` / `64.1%` | `65.2%` AA | — |
| Coding & Eng | **BenchCAD 2.1 Core** | DataLearner | **`73.1%` (#7)** | `52.6%` | **`+20.5 pt`** | — | — | `82.5%` (#2) |
| Science | **GPQA Diamond** | OpenAI / DataLearner | **`96.0%` (#2/254)** | `95.4%` | **`+0.6 pt`** | `95.6%` | — | `97.0%` (#1/254) |
| Science | **HLE-Diamond (AA)** | Artificial Analysis | **`64.0%`** | `58.8%` | **`+5.2 pt`** | `53.3%` | — | `72.2%` (#4) |
| Reasoning | **ARC-AGI-1 / 2 / 3** | ARC Prize | **`97.5% / 85.8% / 98.2%`** | `96.5% / 94.2% / 96.2%` | **ARC-3 `+2.0 pt`** | `96.5% / 83.9% / 72.4%` | — | — |
| Enterprise | **AutomationBench (AA)** | Artificial Analysis | **`71.3%`** | `64.9%` | **`+6.4 pt`** | `71.8%` | — | — |
| Legal & Health | **Harvey LAB-AA / HealthBench Pro** | Harvey / OpenAI | **`11.1%` / `65.9%`** | `6.9%` / `64.2%` | **`1.61x` Legal** | `2.8%` / — | — | `— / 66.3%` |
| Cybersecurity | **DeepSec-Bench / CWE-Bench (AA)** | Artificial Analysis | **`51.6%` (#3) / `64.2%`** | — | **#3 DeepSec** | — | `— / 71.0%` | — |
| Cybersecurity | **CyberGym End-to-End (AA)** | Artificial Analysis | `0.0%` (#23) | — | Exploit boundary | — | **`54.8%` ExploitGym** | — |

---

## 5. Solution Architect Routing Blueprint & Decision Checklist

```mermaid
flowchart TD
    Req["Incoming Agentic / Engineering Request"] --> TokCheck{"Total Input > 272K Tokens?"}
    TokCheck -- "Yes (>272K triggers $4/$15 whole-request cliff)" --> Shard["Shard Diff into <=270K Calls
Reuse $0.10/M Cached Prefix (-39.4% cost)"]
    TokCheck -- "No (<=272K Standard $2/$10)" --> DomainCheck{"Workload Regime"}
    Shard --> DomainCheck
    DomainCheck -- "Coding / Scientific CLI / Calibrated Gates / Legal Triage" --> SolHigh["GPT-6.2 Sol (effort='high')
88 tok/s · ~8-10s TTFA · TB-Science 67.6%"]
    DomainCheck -- "Well-Specified Codegen / Batched Classification" --> SolLow["GPT-6.2 Sol (effort='low'/'medium')
45.4s 4-module · 1.47s/decision batched"]
    DomainCheck -- "Desktop GUI / Multi-App Computer Use" --> Opus["Claude Opus 5.5 / Sonnet 5.5
OSWorld 87.2% · Agents 70"]
    DomainCheck -- "End-to-End Exploit-to-Patch / 1M Graph Traversal" --> Carbon["Gemini 4 Carbon
ExploitGym 54.8% · GraphWalks 96.2%"]
    DomainCheck -- "Hardest Frontier Science & Architecture" --> Astra["GPT-6.2 Astra ($8/$40)
GPQA 97.0% #1 · HLE-Diamond 72.2%"]
```

- [x] **Default `reasoning_effort="high"` for interactive & CI pipelines** (`9.98s` AA first-answer vs `68.2s` on `max`, matching `67.6%` on `Terminal-Bench-Science`).
- [x] **Use `low` / `medium` for bounded code synthesis & batched JSON gates** (`45.42s` / `$0.0547` on 4-module stdlib suite; `12/12` routing in `8.11s`).
- [x] **Enforce a hard `268K` token gateway splitter** so requests never accidentally cross `272,000` input tokens.
