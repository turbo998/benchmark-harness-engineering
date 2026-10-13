# Benchmark Harness Engineering

An original, reproducible workflow for generating accepted benchmark samples,
preparing isolated environments, comparing model APIs and coding agents, and
rebuilding evidence-backed reports.

## Current readiness

Repository initialization only. Research publication and implementation are in
progress. No benchmark engine integration, local sandbox, Azure deployment or
live model experiment has been validated by this project yet.

## Approved direction

- promptfoo for API evaluations and Harbor for coding-agent tasks, with a thin
  Python layer for experiment contracts, attempts, budgets and reports.
- Deterministic templates and explicit mock data before any paid evaluation.
- Separate local and Azure environment cohorts.
- Parameterized Azure infrastructure with an untrusted VM worker, a separate
  trusted inference broker and private evidence storage.
- Rebuildable JSON/CSV, offline HTML and quality/cost/latency visualizations.

Actual cloud deployments and paid model calls require separately approved
targets, permissions and budgets.

## Provenance boundary

This project publishes original research, templates and tools. External articles,
code, task banks and reported scores are not republished or presented as our
measurements. Source links and fixed versions will accompany the research.

Research starting points:

- [Author's benchmark evidence](https://github.com/satomic/copilot-benchmark)
- [Author's model-router project](https://github.com/satomic/model-router)
- [promptfoo](https://github.com/promptfoo/promptfoo)
- [Harbor](https://github.com/harbor-framework/harbor)
