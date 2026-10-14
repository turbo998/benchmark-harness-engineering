# Anonymous reported-data archive

These are factual historical report transcriptions, **not measured results produced
by this harness**. Start with the [eight-report index](../../docs/reports/README.md)
or machine-readable [catalog](catalog.json).

Each family has a `report.json` with original summary metadata and reported metric
cells. CSVs contain the same cells plus `report_id`, `provenance` and
`independently_reproduced` columns. Chinese/English numeric task tables were compared;
language variants are source views, never additional runs. The catalog covers thirteen
source pages/card decks across eight report families, not thirteen independent datasets.

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
