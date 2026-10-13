# Metrics and report semantics

All figures, CSV columns, JSON points and HTML tables use `metrics.summarize`.
The report does not call an LLM or fetch remote plotting resources.

## Correctness, compliance and review

Functional assertions have declared positive weights; functional score is weighted
passes / functional weight. JSON equality is canonical and type-sensitive:
`true`, `1` and `1.0` are not interchangeable when an integer answer is frozen.
Normalization (`none`, `strip`, `casefold`) is frozen per case.
Compliance assertions are reported independently; coding verifier outcomes are
binary functional evidence, not an invented style/compliance rubric.

The default `deterministic-v1` composite equals functional correctness.
The optional **`author-style-70-15-15-v1`** profile weights functional/compliance/
rubric by 70/15/15. It is a named author-style comparison profile, not a universal
model-quality metric. Missing components yield a null composite. Pending rubric
review is null—not zero—and the result is `review_pending`, not passed.
Independent machine review must carry a reviewer version and is labelled
`machine_reviewed`; it is not human truth. No machine-grader call is made by the demo.

## Denominators and matching

- **Planned:** every case × candidate × repeat cell, including unscheduled cells.
- **Attempted trials:** cells with at least one recorded attempt.
- **Total attempts:** all retries, including prior failed attempts.
- Final outcome selects the highest numbered attempt per cell.
- Success rate is final passed cells / **planned** cells. Failure, infra/provider/
  quota/auth errors, timeout, cancellation and pending review remain visible.
- Macro functional/quality first averages repetitions within each task, then tasks.
  Missing/error cells contribute zero functional correctness; pending independent
  review is excluded from composite quality and explicitly counted.
- Micro assertion rate is passed assertions / all planned assertions, including
  error and missing cells. Weighted micro is also reported; it is not macro score.
- `pass_at_k` is **observed task-any-success over k repeats**, not an unbiased
  population estimator and not one-attempt success.
- Paired differences match task **and repeat** within the same cohort/track.
  Bootstrap resamples task clusters, never treats repeated identical tasks as new
  independent evidence. Intervals are withheld below ten independent tasks;
  ten is a display guard, not a statistical sufficiency guarantee.

The starter pack never reports p95 or reliable rankings. Close differences or a
synthetic Pareto frontier are not evidence of production model superiority.

## Timing and usage

API latency, TTFT, routing, agent elapsed, setup, verification, teardown and wall
duration are separate fields. Timestamps carry time zones and reconcile with wall
duration. Missing phases/categories carry reasons; no null-to-zero filling occurs.
Scatter latency is the track-specific mean of observed final API/agent phases;
all-attempt timings remain in `results.json` and evidence. Failed finals and missing
observations are counted. This is neither successful-only latency nor end-to-end
total experiment time.

Input, cache read, cache write, output and reasoning tokens retain provenance.
Harbor's inclusive input is converted to exclusive uncached input only when cache
count is present. Missing cache/write/reasoning cannot be assumed zero for pricing.
Native engine-reported dollar amounts are preserved as provisional observations,
not magically upgraded to dated authoritative billing.

## Cost, missing data and provenance

Costs use Decimal USD, explicit scope, provenance and either an amount or a null
with reason. Measured/estimated priced costs require a price date/table hash.
No-charge zero requires a reason. Synthetic dollars are visibly synthetic.

Chart cost is the sum of **all recorded candidate attempts**, including retries.
If any charge is missing, total cost is null and excluded from cost–quality/Pareto;
the known subtotal and missing-attempt count remain visible. Unknown usage may
retain an outstanding budget reservation. Candidate-only cost does not include
unrecorded generator/grader/VM/broker/storage/network/residual charges; it must not
be called full experiment TCO.

The mock demo's actual inference charge is **0 USD**. Its nonzero chart coordinates
are deterministic synthetic fixtures, not invoices, price estimates or observations.
`measured_by_this_project`, `synthetic` and `third_party_reported` are distinct.

## Offline output and plotting choice

`report` verifies saved artifact hashes before generating:

- `summary.json` shared points/denominators, frontier and matching statistics.
- `results.json` every normalized attempt, including prior retry charges.
- `summary.csv` reconciled flattened point columns; empty means unknown, not zero.
- Self-contained `index.html` with embedded SVG figures and complete report data.
- Five PNG/SVG pairs: cost–quality/Pareto, latency–quality, difficulty heatmap,
  functional distributions and score breakdown.
- Relative links to copied hashed evidence; no remote script/CDN is needed.

**Directly related implementation deviation:** Matplotlib replaces Plotly/Kaleido
for static PNG/SVG and embedded offline HTML. This avoids a browser/Kaleido runtime
dependency, makes the no-cost Windows workflow reliable, and keeps every figure
calculation in the shared summary layer. There is no live dashboard or fabricated
interactive hover data. Exact byte regeneration is tested in the pinned environment;
different fonts/platforms may render differently without changing the numeric data.
