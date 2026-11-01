# Nineteen-Model Coding Supplement: Anonymized Historical Facts

**Provenance:** `anonymized_reported`, two source pages (Chinese and English), `independently_reproduced=false`.
On 2026-10-15, Haiku 5.5 and Gemini 4 Argon were added (22 new runs; 209 cumulative non-reference runs across 19 models × 11 tasks).
The new runs used CLI `1.0.98`, while prior batches spanned `1.0.84-3` through `1.0.90-5`.
Structured tables are preserved in [report.json](../../data/reported/coding-nineteen/report.json) and companion CSVs;
Chinese version: [coding-nineteen.md](coding-nineteen.md).

## Method

Retains the same 11 Python standard-library tasks, 1,310 hidden assertions per model,
the 70 functional + 15 compliance + 15 quality rubric, and serial single-run execution.
The 19-row table aggregates runs across multiple historical dates and CLI versions rather than
re-running all 19 models on the same day and environment.
All 17 prior models retain exact zero-drift scores from the 17-model snapshot.
DeepSeek-V4-Flash uses a BYOK configuration whose transport, auth, and cost basis differ from hosted CLI runs.
Reported figures cannot be imported as `measured` or `synthetic` harness results.

## Reported Values

| Model | Overall Mean / 100 | Complex Mean | Hidden Passed / 1310 | Total Cost USD | Total Wall Min | API Rounds |
|---|---:|---:|---:|---:|---:|---:|
| Haiku 4.5 | 93.96 | 89.64 | 1239 | 3.93 | 80.8 | 341 |
| Sonnet 5 | 98.70 | 98.88 | 1310 | 7.87 | 53.2 | 190 |
| Opus 5 | 99.59 | 99.38 | 1310 | 17.41 | 63.3 | 188 |
| Fable 5.1 | 99.77 | 99.62 | 1310 | 14.45 | 55.9 | 142 |
| GPT-6 Astra | 98.82 | 99.75 | 1310 | 9.91 | 32.7 | 62 |
| Kimi K3 | 98.68 | 98.81 | 1305 | 5.58 | 150.5 | 143 |
| Gemini 3.8 Flash | 98.00 | 97.00 | 1276 | 2.83 | 85.4 | 277 |
| MAI-Code-1.1-Flash | 97.70 | 96.61 | 1284 | 0.53 | 56.5 | 192 |
| Grok 4.6 | 98.57 | 98.06 | 1305 | 5.21 | 69.5 | 138 |
| GPT-5.6 Luna | 97.88 | 96.42 | 1293 | 0.39 | 51.0 | 235 |
| GPT-6 Luna | 98.16 | 96.88 | 1279 | 0.17 | 44.6 | 139 |
| Grok 4.7 | 99.21 | 99.33 | 1299 | 12.22 | 181.2 | 143 |
| HydraFusion | 98.45 | 98.75 | 1310 | 3.58 | 24.1 | 85 |
| DeepSeek-V4-Flash | 95.10 | 95.91 | 1250 | 1.95 | 179.0 | 420 |
| Opus 5.5 | 99.68 | 99.62 | 1310 | 5.84 | 31.8 | 92 |
| Sonnet 5.5 | 99.00 | 99.19 | 1310 | 2.89 | 21.7 | 65 |
| GPT-6.1 Sol | 98.86 | 99.38 | 1310 | 1.71 | 27.4 | 60 |
| Haiku 5.5 | 99.24 | 99.22 | 1308 | 0.33 | 35.1 | 94 |
| Gemini 4 Argon | 98.59 | 98.06 | 1310 | 2.82 | 45.2 | 106 |

Rows follow the source batch order rather than a recommended ranking. In this single-trial snapshot,
Haiku 5.5 recorded an overall mean of 99.24 (total 1091.61 / 1100, 1308 / 1310 hidden assertions,
$0.33 total cost, 35.1 wall minutes / 2103.6s, 30.9 inference minutes / 1851.9s, 94 rounds, 453,116 output tokens),
missing only 2 hidden assertions in C4; Gemini 4 Argon recorded 98.59 (total 1084.50 / 1100,
1310 / 1310 hidden assertions, $2.82 total cost, 45.2 wall minutes / 2709.8s, 41.9 inference minutes / 2512.3s,
106 rounds, 116,755 output tokens), becoming the ninth model to pass all 1,310 hidden assertions.

## Revisions and Comparability

Each model-task cell is a single trial (`n = 1`); the source's own repeat check observed ~1 score point
and 2.4x cost variation. Sub-one-point differences are not statistically robust. Subjective quality scoring
accounts for 7 to 12 points per task, and CLI versions, dates, environments, and cache pricing rules vary across batches.

This archive transcribes the reported tables without re-running upstream tasks or claiming independent reproduction.
New experiments should freeze a single cohort manifest and use paired tasks with repeated trials.
