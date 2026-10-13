"""Read-only, no-inference capability probes. Never installs tools or modifies approval."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from benchmark_harness.agents.copilot import probe_help
from benchmark_harness.artifacts import redact
from benchmark_harness.engines.promptfoo import VERSION, executable, offline_environment
from benchmark_harness.manifest import ENGINE_VERSIONS


def _probe(command: list[str], *, cwd: Path) -> dict[str, Any]:
    env = offline_environment(cwd)
    env["PROMPTFOO_CONFIG_DIR"] = str((cwd / ".engine-probes" / "promptfoo").resolve())
    env["HARBOR_DISABLE_TELEMETRY"] = "1"
    resolved = shutil.which(command[0])
    if resolved and resolved.lower().endswith(".ps1"):
        command = ["powershell", "-NoProfile", "-NonInteractive", "-File", resolved, *command[1:]]
    elif resolved:
        command = [resolved, *command[1:]]
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        return {
            "available": process.returncode == 0,
            "exit_code": process.returncode,
            "output": redact((process.stdout + process.stderr)[:20000]),
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"available": False, "reason": type(error).__name__}


def doctor(repository: Path) -> dict[str, Any]:
    probes: dict[str, Any] = {}
    for tool in ("python", "node", "uv", "docker", "copilot"):
        probes[tool] = (
            _probe([tool, "--version"], cwd=repository)
            if shutil.which(tool)
            else {"available": False, "reason": "Not installed"}
        )
    if probes["copilot"]["available"]:
        help_probe = _probe(["copilot", "--help"], cwd=repository)
        probes["copilot"]["capabilities"] = probe_help(
            probes["copilot"]["output"], help_probe.get("output", "")
        )
    try:
        engine = executable(repository)
        probes["promptfoo"] = _probe(engine + ["--version"], cwd=repository)
        probes["promptfoo"]["expected_version"] = VERSION
        probes["promptfoo"]["version_matches"] = VERSION in probes["promptfoo"].get("output", "")
        probes["promptfoo"]["help"] = _probe(engine + ["eval", "--help"], cwd=repository)
    except RuntimeError as error:
        probes["promptfoo"] = {"available": False, "reason": str(error)}
    harbor_binary = (
        repository
        / "engines"
        / ".venv"
        / ("Scripts" if os.name == "nt" else "bin")
        / ("harbor.exe" if os.name == "nt" else "harbor")
    )
    probes["harbor"] = (
        _probe([str(harbor_binary), "--version"], cwd=repository)
        if harbor_binary.exists()
        else {
            "available": False,
            "reason": "Pinned Harbor not installed; Windows ARM dependency build failed",
        }
    )
    return {
        "paid_calls": 0,
        "cloud_mutations": 0,
        "expected_versions": ENGINE_VERSIONS,
        "probes": probes,
        "offline_mock": "supported",
        "local_sandbox": "unvalidated; Docker execution required",
        "live_api": "blocked: provider integration, dated pricing and explicit approval required",
        "live_copilot": "blocked: isolated auth/BYOK, usage/accounting and Harbor/Docker probes required",
        "azure": "separate parameterized profile; not provisioned by doctor",
    }
