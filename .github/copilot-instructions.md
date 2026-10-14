# Repository Custom Instructions — `benchmark-harness-engineering`

## 1. Benchmark Report Standard (7-Card 4:5 Visual Deck)

All model benchmark test reports (Routing/Decision models, API models, Coding Agents) produced or archived in this repository must adhere to the **7-Card 4:5 Visual Report Format**:

- **Design & Mapping Specification**: [`docs/research/visual-report-card-format.md`](../docs/research/visual-report-card-format.md)
- **Reusable System Prompt & Schema**: [`docs/research/benchmark-report-system-prompt.md`](../docs/research/benchmark-report-system-prompt.md)
- **HTML Card Generator**: [`src/benchmark_harness/cards.py`](../src/benchmark_harness/cards.py) via `uv run benchmark-harness cards <source> --output <output.html>`
- **Reference Implementation**: [`examples/card-report/index.html`](../examples/card-report/index.html) and [`data/reported/routing-strands-decider/report.json`](../data/reported/routing-strands-decider/report.json)

### 7-Card Deck Structure (`900px × 1125px` / `4:5` Portrait)
1. **`1 / 7` (`HANDS-ON · <TRACK>`)**: Cover headline, 3-column workbench preview, hardware & provenance callout.
2. **`2 / 7` (`SCENARIO: <CASE_NAME>`)**: Single-sample deep dive with quote box, stacked sub-decisions, action pills (`Act automatically` / `Confirm` / `Send to a human`), and horizontal distribution bars.
3. **`3 / 7` (`WHAT I TESTED`)**: 4-column scenario scorecard (`SCENARIO | QUESTION | ANSWER | ACTION`) with `✕` miss markers and threshold-gating takeaways.
4. **`4 / 7` (`UNDER THE HOOD`)**: Dual dark code blocks (`#0F172A`) illustrating JSON contract `↓` rendered prompt or deterministic verifier pipeline.
5. **`5 / 7` (`ROBUSTNESS CHECK`)**: Perturbation / option-reversal / repeat-consistency table (`ORIGINAL | REVERSED/PERTURBED | CHANGE (PTS)`).
6. **`6 / 7` (`LATENCY`)**: Horizontal paired bar chart comparing batched/optimized vs baseline latency across load tiers.
7. **`7 / 7` (`MY TAKE`)**: Dual-column `✅ Good fit` (`#DCFCE7`) vs `⛔ Not for` (`#FEE2E2`) + bottom dark readiness & provenance card.

## 2. Integrity, Provenance & Privacy Guardrails

- **Zero Fabricated Coordinates**: Every chart bar, percentage, and denominator must be derived from sealed `Result` / `summary.json` / `report.json` records. Missing or pending rubric reviews must remain `null` / `pending`, never coerced to `0`.
- **Explicit Provenance**: Distinguish `measured_by_this_project`, `synthetic`, and `anonymized_reported` (`independently_reproduced=false`).
- **Privacy & Sanitization**: Never include personal author names, internal team identifiers, private Notion/cloud URLs, or credentials in `data/reported/**`, `docs/reports/**`, or generated HTML decks.
- **Offline & Quality Gates**: Run `pytest`, `ruff check`, `ruff format --check`, and `mypy` before committing. HTML reports must remain self-contained with CSP `default-src 'none'; style-src 'unsafe-inline'`.
