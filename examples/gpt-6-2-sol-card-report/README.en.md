# GPT-6.2 Sol 7-Card 4:5 Visual Benchmark Deck (Supplement Report 9)

> 🌐 **Language**: **[中文说明](README.md)** | **English README**

This directory contains the self-contained 7-card `4:5` portrait visual benchmark decks (`900px × 1125px`, `provenance="measured"`, `independently_reproduced=true`) for **Supplement Report 9: GPT-6.2 Sol Live Effort-Sweep, Calibrated Routing & 21-Model Frontier Benchmark (`2026-11-18`)**.

## Contents

- [`index.html`](index.html): English 7-Card `4:5` visual report deck rendered deterministically byte-for-byte by `benchmark_harness.cards` from [`../../data/reported/gpt-6-2-sol-benchmark/report.json`](../../data/reported/gpt-6-2-sol-benchmark/report.json).
- [`index.zh-CN.html`](index.zh-CN.html): Chinese (`zh-CN`) 7-Card `4:5` visual report deck with relative top navigation and embedded [`../../data/reported/gpt-6-2-sol-benchmark/report.zh-CN.json`](../../data/reported/gpt-6-2-sol-benchmark/report.zh-CN.json).
- Full Bilingual Technical Reports:
  - Chinese (`zh-CN`): [`../../docs/reports/gpt-6-2-sol-benchmark.md`](../../docs/reports/gpt-6-2-sol-benchmark.md)
  - English (`en`): [`../../docs/reports/gpt-6-2-sol-benchmark.en.md`](../../docs/reports/gpt-6-2-sol-benchmark.en.md)
- Sealed Data & Telemetry Directory: [`../../data/reported/gpt-6-2-sol-benchmark/`](../../data/reported/gpt-6-2-sol-benchmark/) (`report.json`, `report.zh-CN.json`, `freeze_manifest.json`, and 5 live/external CSV tables).

## Offline Viewing & Deterministic Regeneration

Both HTML decks enforce `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'` with zero external requests and zero `<script>` tags, so they can be opened directly offline in any browser.

To regenerate `index.html` from the repository root:

```bash
uv run benchmark-harness cards data/reported/gpt-6-2-sol-benchmark/report.json --output examples/gpt-6-2-sol-card-report/index.html
```
