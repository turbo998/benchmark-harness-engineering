# Attribution

This is an original harness and research synthesis, not an official fork,
implementation or endorsement of the referenced authors and frameworks.

Research starting points are two third-party benchmark and routing articles (private workspace URLs and personal author bylines omitted; see [docs/reports/README.md](docs/reports/README.md) for anonymized provenance):

- Seventeen-model supplemental comparison (`anonymized_reported`, [docs/reports/coding-17-models-supplement.md](docs/reports/coding-17-models-supplement.md))
- Model selection and routing latency in GitHub Copilot (`anonymized_reported`, [docs/reports/routing-copilot-auto.md](docs/reports/routing-copilot-auto.md))

Public evidence was inspected in
[satomic/copilot-benchmark](https://github.com/satomic/copilot-benchmark/tree/aa1e0dc31661ff6343433f06fe3bea1e015b8525)
and [satomic/model-router](https://github.com/satomic/model-router/tree/d189bcd681a285a4af0a25d54166346eea2ae7a0).
The fixed versions and individual source paths are recorded in
[evidence.json](docs/research/evidence.json).

The project does not reproduce the articles, screenshots, source/task banks or
complete result archive. Factual measurements are attributed as third-party
reported data, never measurements performed by this harness. The absence of a
verified redistribution license is not interpreted as permission to copy code.

Original fixtures, role prompts, aggregation rules, charts and infrastructure
are authored for this project. Dependency packages retain their own licenses;
the project's MIT license does not relicense them.

The [anonymous report archive](docs/reports/README.md) contains original factual
summaries and transcribed metric cells, labelled `anonymized_reported`, from eight
report families (thirteen language pages / card decks). It is not a republication of those articles,
their complete task banks, images, attachments or code, and is not our measurement.
Source identities/private links are deliberately omitted from this new archive;
earlier research attribution above is retained rather than rewritten or relicensed.

Supplement Report 10 ([docs/reports/terminal-bench-4-1.en.md](docs/reports/terminal-bench-4-1.en.md)
and `data/reported/terminal-bench-4-1/`) synthesizes publicly published aggregate
telemetry from [TERMINAL-BENCH (`tbench.ai`)](https://www.tbench.ai/) and
[`harbor-framework/terminal-bench@v4.1.0`](https://github.com/harbor-framework/terminal-bench/releases/tag/v4.1.0)
(Stanford / Harbor Framework / Laude Institute, Apache-2.0), explicitly marked
`independently_reproduced=false` without redistributing task prompts, oracle
solutions, or benchmark canary strings.

Supplement Report 11 ([docs/reports/mai-image-2-7-commercial-editing-benchmark.en.md](docs/reports/mai-image-2-7-commercial-editing-benchmark.en.md)
and `data/reported/mai-image-2-7-commercial-editing/`) is an original, independently
reproduced commercial image editing evaluation (`provenance="measured"`,
`independently_reproduced=true`) inspired by the academic `ServImage` benchmark
taxonomy (`arXiv:2604.24023v2`) and `Editable` vertical structure, using newly
generated synthetic reference assets frozen via SHA-256 (`freeze_manifest.json`)
and live Microsoft Foundry API runs (`MAI-Image-2.7`, `MAI-Image-2.7-Flash`,
`MAI-Image-2.6`, `FLUX.2`, and OpenAI `gpt-image-2` / `2.5` families). External
blind-arena standings cited for context ([Artificial Analysis Image Editing Arena v2.1](https://artificialanalysis.ai/image/leaderboard/editing)
and [LMArena](https://lmarena.ai/)) are isolated and explicitly labelled
`provenance="reported"`.
