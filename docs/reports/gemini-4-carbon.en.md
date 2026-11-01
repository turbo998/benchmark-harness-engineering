# Gemini 4 Carbon Official Benchmark & Security Evaluation: Anonymized Historical Facts (Supplement 6)

**Provenance:** `anonymized_reported`, bilingual archive (Chinese and English), `independently_reproduced=false`.
Synthesizes verified quantitative metrics from Google DeepMind's official Gemini 4 Carbon release (`2026-10-28`) and model evaluation report (16 core capability benchmarks, 4 cybersecurity and prompt-injection leaderboards, and alignment/anti-cheating audits).
Chinese version: [gemini-4-carbon.md](gemini-4-carbon.md);
structured data: [JSON](../../data/reported/gemini-4-carbon/report.json),
[16-Benchmark Matrix CSV](../../data/reported/gemini-4-carbon/benchmark_matrix.csv),
[Cybersecurity Leaderboards CSV](../../data/reported/gemini-4-carbon/cybersecurity_leaderboards.csv),
[Alignment Metrics CSV](../../data/reported/gemini-4-carbon/alignment_metrics.csv), and
[Offline 7-Card 4:5 Visual HTML Deck](../../examples/gemini-4-carbon-card-report/index.html).

## Method and Access Boundaries

- **Controlled Rollout (Fairwind Program)**: Gemini 4 Carbon is Google DeepMind's frontier model engineered for long-horizon agentic coding, scientific computing, and cyber defense. Because its autonomous vulnerability discovery and exploit generation capabilities cross frontier cybersecurity thresholds, access is rolled out in phases to verified cyber defenders via DeepMind's **Fairwind Program**.
- **Pricing Basis**: Matches Gemini 4 Argon's introductory token pricing: **`$2.00 / 1M` input tokens, `$10.00 / 1M` output tokens, and `95%` discount on cached input (`$0.10 / 1M` tokens)**.
- **Local Copilot CLI `A1–C4` Status (Zero-Fabrication Guardrail)**: Because Gemini 4 Carbon is in phased Fairwind preview and not yet exposed in the public GitHub Copilot CLI CAPI `/models` catalog, its local 11-task (`A1–C4`) Copilot CLI score is explicitly recorded as **`null` (`fairwind_preview_pending_cli`)** — never fabricated or coerced to zero.

## 16-Benchmark Cross-Model Capability Matrix (5 Frontier Models)

| Benchmark | Evaluation Protocol & Tooling | Gemini 4 Carbon | Gemini 4 Argon | GPT-6 Astra | Claude Opus 5.5 | Claude Fable 5.1 | Carbon vs Argon Delta |
|---|---|---:|---:|---:|---:|---:|---:|
| **AA Index v5.0** | Artificial Analysis Index (with tools) | **59 (#1)** | 50 | 57 | 58 | 49 | **+9 pts** |
| **Vals Index v2.2** | Enterprise multimodal suite | **70.4% (#1)** | 69.2% | 65.0% | 70.2% | — (`null`) | **+1.2 pts** |
| **SWE-sweep** | mini-swe-agent subtask reward | **9.6% (#1)** | 4.3% | 9.5% | 3.6% | 2.9% | **+5.3 pts (2.23x)** |
| **FrontierSWE 2** | Proximal public leaderboard | 61.2% (#3) | 55.0% | **65.5% (#1)** | 62.3% (#2) | 56.3% | **+6.2 pts** |
| **Terminal-Bench 4.0 (AA)** | Terminal engineering tasks | **65.2% (#1)** | 57.1% | 59.1% | 59.6% | 52.0% | **+8.1 pts** |
| **Agents' Last Exam v1.1** | 122 tasks, ALE-Claw, 5h window | **77.4% (#1)** | 69.0% | 73.1% | 71.6% | — (`null`) | **+8.4 pts** |
| **OSWorld-2.1** | 82-task offline subset, max@3 | 81.5% (#2) | 74.7% | 80.9% | **87.2% (#1)** | 76.8% | **+6.8 pts** |
| **AutomationBench** | Zapier private workflow set | **53.9% (#1)** | 51.3% | 41.4% | 42.5% | 31.4% | **+2.6 pts** |
| **Vending-Bench 2** | Andon Labs bank balance ($) | **$16,484 (#1)** | $13,718 | $15,515 | $9,235 | $5,422 | **+$2,766 (+20.2%)** |
| **Chartography** | Surge chart reasoning (no tools) | **72.5% (#1)** | 71.6% | 71.0% | 66.3% | 46.2% | **+0.9 pts** |
| **Blueprint-Bench 2** | Andon Labs blueprint similarity | **58.6% (#1)** | 54.4% | 49.7% | 51.2% | 41.9% | **+4.2 pts** |
| **GraphWalks** | 256k–1M context, 200 problems, BFS F1 | **96.2% (#1)** | 84.2% | 71.8% | 66.8% | 65.0% | **+12.0 pts** |
| **RiemannBench** | Surge advanced mathematics | **80.0% (#1)** | 76.0% | 72.0% | 69.6% | 65.6% | **+4.0 pts** |
| **Terminal-Bench-Science 0.1** | AA scientific terminal tasks | **64.8% (#1)** | 52.9% | 63.3% | 59.0% | 43.3% | **+11.9 pts** |
| **CWE-bench** | Collinear Pass@1 (ties broken by Pass@4) | **71.0% (#1)** | 68.0% | 68.0% | 67.0% | 58.0% | **+3.0 pts** |
| **ExploitGym** | Antigravity causal pass rate (10h / 6h) | **54.8% / 53.5% (#1)** | 42.0% / 39.5% | 42.4% (no cap) | 34.5% (6h) | — (`null`) | **+12.8 pts / +14.0 pts** |
| **SEC-bench Pro** | 183 JS engine tasks, Pass@1 avg 3 trials | **88.2% (#1)** | 83.4% | 85.4% | — (`null`) | — (`null`) | **+4.8 pts** |
| **WebDev Arena** | Blind human preference Elo | **1768 (#4)** | 1679 | — (`null`) | — (`null`) | — (`null`) | **+89 Elo** |

**Summary Fact:** Across the 16 primary capability and security benchmarks, `Gemini 4 Carbon` ranks **#1 on 14 benchmarks**, trailing only on `FrontierSWE 2` (`61.2%` #3 behind `GPT-6 Astra` `65.5%` and `Claude Opus 5.5` `62.3%`) and `OSWorld-2.1` (`81.5%` #2 behind `Claude Opus 5.5` `87.2%`).

## Cybersecurity, Vulnerability Repair & Prompt-Injection Sub-Leaderboards

### 1. `SEC-bench Pro` (183 JS Engine Tasks, Pass@1 Avg 3 Trials, Antigravity)

| Rank | Model | Pass@1 Avg (%) |
|---:|---|---:|
| 1 | **Gemini 4 Carbon** | **88.2%** |
| 2 | GPT-6 Astra | 85.4% |
| 3 | Gemini 4 Argon | 83.4% |
| 4 | GPT-6.1 Terra | 83.3% |
| 5 | GPT-6.1 Sol | 78.8% |
| 6 | MiMo-V2.6-Pro | 66.3% |
| 7 | DeepSeek-V4.1-Flash | 62.8% |
| 8 | DeepSeek-V4-Pro | 56.4% |

### 2. `ExploitGym` (Causal Pass Rate by Time Budget)

| Rank | Model & Time Cap | Causal Pass Rate (%) |
|---:|---|---:|
| 1 | **Gemini 4 Carbon (10h)** | **54.8%** |
| 2 | **Gemini 4 Carbon (6h)** | **53.5%** |
| 3 | GPT-6 Astra (No time cap) | 42.4% |
| 4 | Gemini 4 Argon (10h) | 42.0% |
| 5 | Gemini 4 Argon (6h) | 39.5% |
| 6 | GPT-6.1 Sol (No time cap) | 35.1% |
| 7 | Claude Opus 5.5 (6h) | 34.5% |
| 8 | Claude Mythos 5.1 (6h) | 30.4% |
| 9 | MiMo-V2.6-Pro (Unknown time cap) | 17.8% |
| 10 | GLM-5.3 (6h) | 15.0% |

### 3. `CWE-bench` (Collinear Pass@1, Ties Broken by Pass@4)

| Rank | Model | Agent Harness | Pass@1 (%) |
|---:|---|---|---:|
| 1 | **Gemini 4 Carbon** | Antigravity | **71.0%** |
| 2 | Grok 4.7 | opencode | 68.0% |
| 2 | Gemini 4 Argon | Antigravity | 68.0% |
| 2 | GPT-6 Astra | Codex | 68.0% |
| 5 | Claude Opus 5.5 | Claude Code | 67.0% |
| 6 | Claude Fable 5.1 | Claude Code | 58.0% |
| 7 | Grok 4.6 | opencode | 57.0% |
| 8 | DeepSeek-V4-1-Flash | opencode | 55.0% |
| 8 | Muse Spark 1.3 | opencode | 55.0% |
| 10 | Hy4 Preview | opencode | 53.0% |
| 11 | GPT-6 Sol | Codex | 52.0% |

### 4. `Gray Swan IPI` (Indirect Prompt Injection Attack Success Rate at `k=15`, Lower Is Better)

| Rank | Model | Attack Success Rate at `k=15` (%) | Defense Tier |
|---:|---|---:|---|
| 1 | **Gemini 4 Carbon** | **0.0%** | **Zero successful breaches across 15 attempts** |
| 2 | Gemini 4 Argon | 0.7% | Sub-1% resilient |
| 3 | Claude Opus 5.5 | 1.0% | High resilience |
| 3 | Claude Fable 5.1 | 1.0% | High resilience |
| 5 | Claude Opus 5 | 4.6% | Moderate-high resilience |
| 6 | Gemini 3.8 Flash | 5.5% | Moderate-high resilience |
| 7 | Gemini 3.8 Flash Cyber | 6.0% | Moderate-high resilience |
| 8 | GPT-6 Astra | 8.5% | Susceptible under repeated k=15 probing |
| 9 | GPT-6.1 Sol | 8.6% | Susceptible under repeated k=15 probing |
| 10 | Muse Spark 1.3 | 15.9% | Moderate vulnerability |
| 11 | GLM 5.3 | 31.5% | High vulnerability |
| 12 | Grok 4.6 | 51.8% | Majority breach rate |
| 13 | Kimi K3 | 52.7% | Majority breach rate |

## Alignment, Honesty & Anti-Cheating Metrics

| Metric | Gemini 4 Carbon Reported Value | Comparison Baseline |
|---|---|---|
| **Terminal-Bench 4.0 successful cheating rate** | **0.0%** (**0.4%** attempt rate) | Eliminates verifier tampering and reward hacking |
| **Internal live coding high-severity misalignment alerts** | **-80%** | Relative to prior generation baseline |
| **Unsupported claims rate** | **-50%** (`~2x` reduction) | Relative to Gemini 4 Argon |
| **Agent overreach rate** | **-26%** | Relative to Gemini 4 Argon |
| **Task under-service rate (unnecessary refusals)** | **-29%** | Relative to Gemini 4 Argon |
| **Secure code generation rate** | **>2x** | Relative to Gemini 4 Argon |
| **Chrome vulnerability patch quality** | **>10x** | Relative to competing frontier model |

## Fit Boundaries and Methodological Limitations

- **Good fit**: Ultra-long-context graph/codebase traversal (`GraphWalks` `256k–1M` `96.2%`), long-horizon terminal and scientific agents (`Terminal-Bench 4.0` `65.2%`, `Agents' Last Exam` `77.4%`), adversarial prompt-injection defense (`Gray Swan IPI` `0.0%`), and authorized vulnerability remediation (`SEC-bench Pro` `88.2%`).
- **Not for**: Immediate unapproved self-serve public CLI deployment (requires Fairwind Program access), or pure desktop GUI clicking workflows where `Claude Opus 5.5` (`87.2%` on `OSWorld-2.1`) still holds the top score.
- **Methodological limitations**: External leaderboards pair different models with different agent scaffolds (`Antigravity`, `Codex`, `Claude Code`, `opencode`) and different time caps (`6h`, `10h`, `No time cap`). Reported scores measure joint model + harness configurations rather than single-harness controlled trials.
