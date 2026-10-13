"""Conservative container command construction; no host inference credentials."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Literal
from uuid import uuid4

from benchmark_harness.contracts import Contract


class SandboxUnavailable(RuntimeError):
    pass


class SandboxSpec(Contract):
    image: str
    role: Literal["agent", "verifier"]
    workspace: Path
    trusted_verifier: Path | None = None
    trusted_verifier_hash: str | None = None
    timeout_seconds: int = 30


def docker_command(spec: SandboxSpec) -> list[str]:
    if not re.fullmatch(r"[a-zA-Z0-9._/-]+@sha256:[a-f0-9]{64}", spec.image):
        raise ValueError("Container image must be digest-pinned")
    workspace = spec.workspace.resolve()
    if "," in str(workspace) or not workspace.is_dir():
        raise ValueError("Invalid dedicated workspace")
    allowed = {"solution.py", "instruction.md"} if spec.role == "agent" else {"solution.py"}
    entries = list(workspace.iterdir())
    if not entries or any(
        p.name not in allowed or p.is_symlink() or not p.is_file() for p in entries
    ):
        raise ValueError(
            "Workspace must contain only declared regular task files, not a home/checkout"
        )
    if not (workspace / "solution.py").is_file():
        raise ValueError("Declared submission is missing")
    command = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user=10001:10001",
        "--pids-limit=64",
        "--memory=256m",
        "--cpus=1",
        "--tmpfs=/scratch:rw,noexec,nosuid,size=16m",
        "--workdir=/workspace",
        "--env=HOME=/nonexistent",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        "--mount",
        f"type=bind,source={workspace},target=/workspace"
        + (",readonly" if spec.role == "verifier" else ""),
    ]
    if spec.role == "verifier":
        if spec.trusted_verifier is None or not spec.trusted_verifier.is_dir():
            raise ValueError("Verifier requires a separate trusted directory")
        hidden = spec.trusted_verifier.resolve()
        if (
            hidden == workspace
            or hidden.is_relative_to(workspace)
            or workspace.is_relative_to(hidden)
        ):
            raise ValueError("Verifier and submission trees must be separate")
        if any(
            p.name != "verify.py" or p.is_symlink() or not p.is_file() for p in hidden.iterdir()
        ):
            raise ValueError("Unexpected trusted verifier files")
        verifier_file = hidden / "verify.py"
        if not verifier_file.is_file() or hashlib.sha256(
            verifier_file.read_bytes()
        ).hexdigest() != (spec.trusted_verifier_hash):
            raise ValueError("Trusted verifier hash mismatch")
        command.extend(["--mount", f"type=bind,source={hidden},target=/verifier,readonly"])
    elif spec.trusted_verifier is not None:
        raise ValueError("Agent must not receive hidden verifier")
    command.append(spec.image)
    command.extend(
        [
            "python",
            "-I",
            "-B",
            "-c",
            "import sys,runpy;sys.path.insert(0,'/workspace');runpy.run_path('/verifier/verify.py')"
            if spec.role == "verifier"
            else "print('Offline agent sandbox only; live inference blocked')",
        ]
    )
    return command


def transfer_submission(source: Path, destination: Path) -> None:
    """Copy only a bounded regular declared output, never hidden files or symlinks."""
    entry = source / "solution.py"
    if entry.is_symlink() or not entry.is_file() or entry.stat().st_size > 1_000_000:
        raise ValueError("Invalid declared submission")
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "solution.py").open("xb") as stream:
        stream.write(entry.read_bytes())


def stop_process_tree(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        script = (
            f"$root={process.pid}; $all=Get-CimInstance Win32_Process; "
            "function StopTree($id) { "
            "foreach($child in $all | Where-Object ParentProcessId -eq $id) "
            "{ StopTree $child.ProcessId }; Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }; "
            "StopTree $root"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=20,
            check=False,
        )
    else:
        kill_group = vars(os)["killpg"]
        kill_group(process.pid, signal.Signals(9))


def bounded_process(command: list[str], *, cwd: Path, timeout: float) -> tuple[int, str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "PATHEXT",
        }
    }
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        stop_process_tree(process)
        process.communicate(timeout=20)
        raise
    return process.returncode, stdout, stderr


def run_container(spec: SandboxSpec) -> tuple[int, str, str]:
    if shutil.which("docker") is None:
        raise SandboxUnavailable("Docker unavailable; recipe is construction-only")
    command = docker_command(spec)
    name = "harness-" + uuid4().hex
    command.insert(2, "--name=" + name)
    try:
        return bounded_process(command, cwd=spec.workspace, timeout=spec.timeout_seconds)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        subprocess.run(
            ["docker", "rm", "--force", name],
            cwd=spec.workspace,
            capture_output=True,
            timeout=20,
            check=False,
        )
        raise
