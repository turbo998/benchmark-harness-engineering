# MAI-Image-2.7 & 2.7-Flash Commercial Image Editing 7-Card Visual Deck (4:5 Portrait)

**English** | **[中文说明](README.md)**

This directory contains the self-contained 7-Card `4:5` portrait visual benchmark decks for the **MAI-Image-2.7 & MAI-Image-2.7-Flash Commercial Image Editing Benchmark** (independent reproduction and extension of the Editable suite grounded in `ServImage`, `arXiv:2604.24023v2`), backed by **121 live Microsoft Foundry GlobalStandard API runs** (`8 models × 12 scenarios = 96 primary runs` + `9 Turn-2 brand consistency runs` + `16 ZH-CN prompt perturbation runs`, `$6.041` measured spend):

- **English Canonical Deck**: [`index.html`](index.html)
- **Chinese Localized Deck**: [`index.zh-CN.html`](index.zh-CN.html)
- **Companion Bilingual Technical Reports**: [`../../docs/reports/mai-image-2-7-commercial-editing-benchmark.en.md`](../../docs/reports/mai-image-2-7-commercial-editing-benchmark.en.md) (English) / [`../../docs/reports/mai-image-2-7-commercial-editing-benchmark.md`](../../docs/reports/mai-image-2-7-commercial-editing-benchmark.md) (Chinese)
- **Sealed Datasets & CSVs**: [`../../data/reported/mai-image-2-7-commercial-editing/`](../../data/reported/mai-image-2-7-commercial-editing/)
- **Interactive Side-by-Side Visual Comparison Studio**: [English Studio](https://turbo998.github.io/workshops/benchmarks/mai-image-2-7-commercial-edit-bench.en.html) · [中文 Studio](https://turbo998.github.io/workshops/benchmarks/mai-image-2-7-commercial-edit-bench.html) · [Companion Gallery Source (`generative-visual-lab`)](https://github.com/turbo998/generative-visual-lab/tree/main/demos/commercial-image-edit-benchmark-studio)

## 7-Card Deck Structure (`#card-1` .. `#card-7`)

1. **`1 / 7` · `HANDS-ON · MULTIMODAL COMMERCIAL IMAGE EDITING`**: Tied `#1` Brief Execution (`BRF = 4.17/5.00`) and `MAI-Image-2.7-Flash` `41.67` accepted deliverables per `$1` (`3.8x` `gpt-image-2.5-sunburst`, `8.7x` `FLUX.2-flex`) workbench overview.
2. **`2 / 7` · `SCENARIO: S11 NATIVE RGBA TRANSPARENT CUTOUT`**: Single-call native 4-channel `RGBA` cutout deep dive (`100.0%` border alpha purity vs `FLUX.2` painted fake RGB checkerboards and prior-gen `MAI-Image-2.6` HTTP 400).
3. **`3 / 7` · `WHAT I TESTED`**: Complete 12-scenario `1024×1024` commercial scorecard with measured latency, non-edit SSIM, blinded `BRF/VEQ/CNS` rubric scores, and `Act automatically / Confirm / Send to a human` workflow gates.
4. **`4 / 7` · `UNDER THE HOOD`**: Multi-provider API normalization (MAI multipart, OpenAI Images, BFL FLUX JSON), SHA-256 pre-frozen inputs, and deterministic SSIM/Alpha verifier + blinded VLM judge pipeline.
5. **`5 / 7` · `ROBUSTNESS CHECK`**: 16-run Simplified Chinese vs English prompt perturbation matrix (`MAI-Image-2.7` & `Flash` hold `4/4` `100%` acceptance; `FLUX.2-pro` drops `-66.6 pts` on Chinese portrait retouching).
6. **`6 / 7` · `LATENCY & TWO-TIER PIPELINE`**: Round-trip median latency across 4 commercial tracks (`20.69s` on `Flash`, `2.0x` faster than OpenAI) and the `$0.045` two-tier `Flash ($0.010) -> 2.7 ($0.035)` studio workflow.
7. **`7 / 7` · `MY TAKE`**: Production routing fit (`✅ Good fit` vs `⛔ Not for` unmasked raw calls) alongside external blind arena context (`Artificial Analysis Image Editing v2.1` `#1` global at `1,215 Elo`).

## Provenance, Privacy & Offline CSP Lock

- **Provenance**: Primary measurements carry `provenance: "measured"` (`independently_reproduced: true`, 121 live Foundry API runs with SHA-256 manifest); external leaderboard references are explicitly tagged `provenance: "reported"`.
- **Sanitization**: Endpoints are sanitized to `<foundry-resource>`; zero internal Azure resource names, subscription/tenant GUIDs, private URLs, or personal author identifiers appear in any file.
- **Strict CSP**: Enforces `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">` with zero `<script>` tags, zero external fonts, and zero network requests.
