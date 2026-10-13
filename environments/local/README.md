# Local isolation recipe (Docker tier not yet validated)

The base image is pinned to the multi-platform OCI digest retrieved from Docker
Registry on 2026-10-13. Build with `docker build -t harness-local environments/local`;
use the resulting **image digest**, not the mutable tag, in a live manifest.
Docker was unavailable on the implementation host; no sandbox execution is claimed.

`security.docker_command` constructs separate agent/submission and trusted verifier
containers: non-root, read-only root, dropped capabilities, no new privileges,
memory/CPU/PID limits, and **no network**. Neither mounts home, cloud credentials,
the checkout, nor the Docker socket. Only `solution.py` is transferred to the
verifier. The hidden verifier is never mounted in the agent container.

Network-disabled agent execution is useful for offline fixtures only. An authenticated,
allowlisted broker egress design and Copilot/Harbor bridge require separate validation;
this recipe does not pretend to provide live inference. Containers are defense in
depth, not a guarantee for arbitrary malicious code. Run hostile workloads on a
dedicated worker/VM with an appropriate threat model.
