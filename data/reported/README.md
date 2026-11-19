# Anonymous reported-data archive

These are factual historical report transcriptions, **not measured results produced
by this harness**. Start with the [ten-report index](../../docs/reports/README.md)
or machine-readable [catalog](catalog.json).

Each family has a `report.json` with original summary metadata and reported metric
cells. CSVs contain the same cells plus `report_id`, `provenance` and
`independently_reproduced` columns. Chinese/English numeric task tables were compared;
language variants are source views, never additional runs. The catalog covers twenty-one
source pages/card decks across twelve report families, not twenty-one independent datasets.

## Units and precision

- `task_cost_usd` is USD. `coding-ten/task_cost_credits.csv` is AI credits at the
  source's USD 0.01/credit conversion, not USD.
- Task latency tables are seconds; source usage summaries retain their displayed
  minute or token abbreviations. Do not treat rounded `万`/`k` summaries as exact
  integer token counts.
- Routing latency fields are milliseconds. Correct/decision counts refer to
  subjective expected-route agreement, not downstream task correctness.
- CSV empty cells denote unavailable values; JSON preserves `null`.
  Literal source dashes/labels in transcribed tables remain unavailable source cells,
  not numeric zero. `csv_files` paths are relative to this archive directory.
  A self-hosted zero per-call fee excludes hardware, operations and licensing and is
  not total-cost-of-ownership zero.
- Reused OpenJev comparison rows explicitly identify their earlier measurement
  report. Do not sum duplicated comparison rows or earlier coding baselines as
  independent observations.

`consistency.json` records arithmetic checks and any source-table inconsistencies
without rewriting reported values. Rounding tolerances are explicit.
All records use `anonymized_reported` and `independently_reproduced=false`;
no invoices, full raw trials or reproducibility certification are implied.

Source author/private identifiers, article prose, complete task prompts, original
images, zipped evidence and implementation/model files are excluded. Existing
research references elsewhere in the repository are not rewritten by this archive.
The original summaries were AI-assisted; reported observations are not attributed
to this project's authors as new measurements.

## Standalone Supplement Datasets (Outside the 12 Historical `catalog.json` Families)

- `gpt-6-2-sol-benchmark/`: Sealed live CAPI evaluation (`provenance="measured"`, `independently_reproduced=true`; see [Supplement Report 9](../../docs/reports/gpt-6-2-sol-benchmark.en.md)).
- `maf-multi-agent-benchmark/`: Microsoft Agent Framework v1.0 multi-agent orchestration benchmark (`provenance="measured"`, `independently_reproduced=true`).
- `terminal-bench-4-1/`: Structured aggregate synthesis of public **Terminal-Bench 4.1** telemetry (`tbench.ai` / `harbor-framework/terminal-bench@v4.1.0`, Apache-2.0, snapshot `2026-11-19T03:41:57Z`; `provenance="anonymized_reported"`, `independently_reproduced=false`; see [Supplement Report 10](../../docs/reports/terminal-bench-4-1.en.md)). Contains `leaderboard_4_1.csv` (65 runs), `pareto_frontiers_4_1.csv`, `tasks_waffle_4_1.csv` (66 tasks), `domain_matrix_4_1.csv` (7 domains), `version_evolution.csv`, `report.json`, and `report.zh-CN.json`. Zero raw task instructions, oracle solutions, or canary GUID strings are included.
