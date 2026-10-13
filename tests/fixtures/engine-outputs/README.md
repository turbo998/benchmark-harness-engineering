# Adapter contract fixtures

The original hand-authored **synthetic** examples exercise the adapter's consumed
release fields; they are not captured live inference.
They cover success, assertion failure, provider/auth errors, absent usage, partial
logs, and separate-verifier evidence.

Release pins: promptfoo 0.124.0 (npm metadata/package inspected); Harbor 0.24.0
(PyPI metadata and released wheel inspected; wheel SHA-256
`23b7ba616a3aae4eff561ced5e2c51c7186f2981e53a770dea9c689d3969877c`).
Harbor source snapshots in research are evidence pins, not installation versions.
Harbor's release now contains a native `copilot-cli` adapter; this does not prove
isolated auth, broker compatibility, complete usage or budget enforcement.

`promptfoo-observed.json` is different: it retains selected, path/UUID-free fields
from an actual promptfoo 0.124.0 **no-network custom-provider** run. All six original
API fixtures passed; actual paid calls were zero. Windows ARM's missing libsql
binding required an isolated pinned x64 Node/libsql runtime. This verifies the
offline engine invocation/output contract, not live model performance or pricing.
