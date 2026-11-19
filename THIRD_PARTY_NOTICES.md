# Third-party notices

The following are research references or runtime dependencies, not vendored
copies. Verify notices against the installed release locks when distributing
a built environment; task datasets and container images may have separate terms.

| Project | Research source | Observed code license |
|---|---|---|
| promptfoo | [repository](https://github.com/promptfoo/promptfoo) | MIT |
| Harbor | [repository](https://github.com/harbor-framework/harbor) | Apache-2.0 |
| Inspect AI | [repository](https://github.com/UKGovernmentBEIS/inspect_ai) | MIT |
| SWE-bench | [repository](https://github.com/SWE-bench/SWE-bench) | MIT |
| Legacy Terminal-Bench | [repository](https://github.com/laude-institute/terminal-bench) | Apache-2.0 |
| Terminal-Bench 4.1 (`harbor-framework/terminal-bench`) | [v4.1.0 release](https://github.com/harbor-framework/terminal-bench/releases/tag/v4.1.0) & [tbench.ai](https://www.tbench.ai/) | Apache-2.0 (aggregate metrics cited; zero task prompts, oracle scripts, or canary GUIDs redistributed) |
| ServImage / Editable Commercial Image Editing Taxonomy | [`arXiv:2604.24023v2`](https://arxiv.org/abs/2604.24023) | Academic paper reference (`BRF/VEQ/CNS` rubric methodology cited; all 12 reference PNGs and 121 outputs in Supplement 11 are newly generated synthetic benchmark assets) |
| Microsoft AI MAI-Image-2.7 & MAI-Image-2.7-Flash | [Microsoft Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/) | Commercial API service (evaluated live under `provenance="measured"`; sanitized endpoint metadata only) |
| Artificial Analysis Image Editing v2.1 & LMArena | [Artificial Analysis](https://artificialanalysis.ai/image/leaderboard/editing) & [LMArena](https://lmarena.ai/) | Public leaderboard citations (`provenance="reported"`, cited for external blind-arena context only) |
| Azure SDK for Python | [repository](https://github.com/Azure/azure-sdk-for-python) | MIT; dependencies retain their own licenses |

No license was established for redistribution of the two satomic repositories
or the Notion articles during the research snapshot. They are linked and
discussed factually, not redistributed. Public accessibility alone is not a
license grant.

No third-party benchmark scores are included as our evaluation results. No
third-party task dataset, copyrighted article image or authenticated browser
snapshot is shipped.

The anonymous historical report archive adds reported factual metric tables, not
new harness evaluation results. Its original summaries do not redistribute source
article prose, original figures, complete task prompts, zipped evidence or weights.
Source-reported model licensing is documented as a historical claim, not a grant
to distribute models or use noncommercial weights commercially.
