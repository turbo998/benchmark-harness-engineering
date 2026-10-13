from pathlib import Path

import pytest

import benchmark_harness.doctor as doctor_module
from benchmark_harness.contracts import PhaseTiming
from benchmark_harness.security import SandboxSpec, run_container


def test_doctor_only_requests_version_or_help(
    monkeypatch: pytest.MonkeyPatch, workdir: Path
) -> None:
    commands: list[list[str]] = []

    def probe(command: list[str], *, cwd: Path) -> dict[str, object]:
        commands.append(command)
        assert cwd == workdir
        assert command[-1] in {"--version", "--help"}
        return {"available": True, "output": "0.124.0 --prompt --model --output-format"}

    monkeypatch.setattr(doctor_module, "_probe", probe)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda name: name)
    monkeypatch.setattr(doctor_module, "executable", lambda repository: ["node", "fixture.js"])
    result = doctor_module.doctor(workdir)
    assert result["paid_calls"] == 0 and result["cloud_mutations"] == 0
    assert all(command[0] != "az" for command in commands)
    assert result["live_api"].startswith("blocked")


def test_container_timeout_removes_only_owned_named_container(
    monkeypatch: pytest.MonkeyPatch,
    workdir: Path,
) -> None:
    import subprocess

    import benchmark_harness.security as security

    (workdir / "solution.py").write_text("", encoding="utf-8")
    command: list[str] = []
    removals: list[list[str]] = []

    def timeout(args: list[str], *, cwd: Path, timeout: float) -> tuple[int, str, str]:
        command.extend(args)
        raise subprocess.TimeoutExpired(args, timeout)

    monkeypatch.setattr(security.shutil, "which", lambda name: "docker")
    monkeypatch.setattr(security, "bounded_process", timeout)
    monkeypatch.setattr(security.subprocess, "run", lambda args, **kwargs: removals.append(args))
    with pytest.raises(subprocess.TimeoutExpired):
        run_container(
            SandboxSpec(image="python@sha256:" + "a" * 64, role="agent", workspace=workdir)
        )
    name = next(arg.split("=", 1)[1] for arg in command if arg.startswith("--name="))
    assert name.startswith("harness-")
    assert removals == [["docker", "rm", "--force", name]]


def test_phase_clock_constraints() -> None:
    with pytest.raises(ValueError, match="duration"):
        PhaseTiming(
            wall_ms=100,
            started_at="2026-10-13T00:00:00Z",
            finished_at="2026-10-13T00:00:01Z",
            provenance="measured",
            missing_reason="Not captured",
        )
