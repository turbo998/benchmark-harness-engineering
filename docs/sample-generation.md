# Original sample generation and acceptance

`benchmark-harness generate --output samples` is deterministic template generation.
It never calls a model. AI synthesis is explicitly refused until a separately
approved provider, price table and budget reservation path exists.

The starter pack contains:

| Track | Fixtures | Coverage |
|---|---:|---|
| API | 6 | English/Chinese; atomic, medium, complex |
| Coding | 3 | ASCII slug, closed-interval merge, deterministic directed route |

Counts are engineering fixtures/pilot coverage, **not statistically sufficient
ranking evidence**. Seeds, instructions, expected shape/answers, normalization,
assertion weights, references and targeted negative variants are original material.

## API pack

`samples\cases.jsonl` is the combined frozen dataset;
`samples\api\cases.jsonl` is the API-only subset. Each case has independent accepted
and rejected response fixtures. Acceptance requires every reference to pass and
every negative response to fail functional correctness. Wrong answers include
malformed JSON, missing fields, wrong types, wrong sums and rule-order mistakes.
JSON shape compliance is separate from semantic correctness.

Adding free-form cases needs a versioned rubric and independently reviewed
calibration examples. Do not copy the generator's answer into an oracle and call
that independent acceptance.

## Coding boundary

Each difficulty directory is split into:

- `agent-visible`: instruction and initially empty declared `solution.py`.
- `trusted-verifier`: independently authored `verify.py`, never agent-mounted.
- `reference`: known-correct solution for acceptance, never agent-mounted.
- Targeted negative solutions and sealed `case.json`.

Acceptance uses this project's allowlisted, trusted fixture programs on the host:
all reference solutions must pass and every targeted negative must fail.
Arbitrary imported verifier/reference/candidate code is refused on the host.
The verdict records `sandbox_tier=unvalidated` until Docker execution is tested.

A real agent receives only the visible tree. Transfer only a bounded regular
`solution.py` into a fresh verifier submission tree. The verifier is separately
mounted read-only, identified by its frozen SHA-256, and has no network. The model
does not generate, modify or select its verifier. Neither container receives user
home, cloud credentials, another checkout, Docker socket or privileged access.

These public fixtures are not secret benchmark holdouts: a public model may know
their content. Filesystem separation alone is not contamination control. A future
ranking needs separately curated, hidden accepted tasks and leakage review.

## Suggested AI-assisted recipe (not currently executed)

The included original prompts split experiment designer, generator, oracle critic,
evidence reviewer and report writer roles. The generator proposes; the independent
critic rejects ambiguity and checks counterexamples. Freeze accepted and rejected
records before any candidate run. Candidate code and graders cannot regenerate the
test set or make the scorer accept their own answer.

Changing seed/content changes case and dataset hashes. Shuffling preserves IDs.
Use a new output directory for different data; generation refuses to overwrite a
different frozen dataset. `accept` writes an explicit acceptance/rejection receipt.
Only accepted datasets can be scheduled by the mock runner.
