# Cost and budget semantics

Model costs use dated, sourced input/cache-read/cache-write/output rates and
authoritative usage where available. Reasoning/cache fields are not added twice
if already included in billed totals. Unknown prices or usage remain null with
a reason, never zero. Native Copilot credits are a separate currency/channel.

The experiment includes candidate, generation, critic/grader, failed requests and
retries. Reserve a conservative maximum before dispatch, then reconcile known
usage. A timeout/disconnected request may already have incurred cost; preserve
its reservation until reconciled. Restart and duplicate attempts must not reset
the run ledger or silently dispatch another charged request.

Opaque agent engines do not automatically provide a provable USD hard cap.
They require explicit capability labels and bounded opt-in smoke; do not equate
engine cost assertions or Azure budget alerts with pre-dispatch enforcement.

Infrastructure accounting includes VM allocated runtime, OS disks, optional
outbound IP, Container Apps execution/requests, Blob retention, logging and
egress. A deallocated VM may leave billable disks/IP/storage; deleting compute
is not complete cost cleanup. Tagging a TTL is not a scheduled stop.

Actual VM/region/model/rates are intentionally unbound in examples. Retail
pricing is an estimate, not the user's negotiated invoice. Model and cloud
budgets must be approved separately; no zero-cost cloud claim is made.
