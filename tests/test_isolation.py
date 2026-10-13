import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from benchmark_harness.security import (
    SandboxSpec,
    bounded_process,
    docker_command,
    transfer_submission,
)

IMAGE = "python@sha256:" + "a" * 64


def test_no_hidden_verifier_home_socket_privilege_or_network(workdir: Path) -> None:
    visible, hidden = workdir / "visible", workdir / "hidden"
    visible.mkdir()
    hidden.mkdir()
    (visible / "solution.py").write_text("", encoding="utf-8")
    verifier_text = "print('VERIFIER_PASS')"
    (hidden / "verify.py").write_text(verifier_text, encoding="utf-8")
    verifier_hash = hashlib.sha256(verifier_text.encode()).hexdigest()
    agent = docker_command(SandboxSpec(image=IMAGE, role="agent", workspace=visible))
    verifier = docker_command(
        SandboxSpec(
            image=IMAGE,
            role="verifier",
            workspace=visible,
            trusted_verifier=hidden,
            trusted_verifier_hash=verifier_hash,
        )
    )
    assert str(hidden) not in " ".join(agent)
    assert "--network=none" in agent and "--network=none" in verifier
    assert "--read-only" in agent and "--cap-drop=ALL" in agent
    assert "--user=10001:10001" in agent
    assert all(
        x not in " ".join(agent) for x in ["docker.sock", "--privileged", ".azure", ".copilot"]
    )
    assert "target=/verifier,readonly" in " ".join(verifier)
    with pytest.raises(ValueError, match="Agent"):
        docker_command(
            SandboxSpec(image=IMAGE, role="agent", workspace=visible, trusted_verifier=hidden)
        )
    with pytest.raises(ValueError, match="separate"):
        docker_command(
            SandboxSpec(image=IMAGE, role="verifier", workspace=visible, trusted_verifier=visible)
        )
    with pytest.raises(ValueError, match="digest"):
        docker_command(SandboxSpec(image="python:latest", role="agent", workspace=visible))
    (visible / "host-secret.txt").write_text("not allowed", encoding="utf-8")
    with pytest.raises(ValueError, match="only declared"):
        docker_command(SandboxSpec(image=IMAGE, role="agent", workspace=visible))


def test_only_declared_submission_is_transferred(workdir: Path) -> None:
    source = workdir / "agent"
    source.mkdir()
    (source / "solution.py").write_text("pass", encoding="utf-8")
    (source / "secret.txt").write_text("must not transfer", encoding="utf-8")
    destination = workdir / "submission"
    transfer_submission(source, destination)
    assert [p.name for p in destination.iterdir()] == ["solution.py"]
    with pytest.raises(FileExistsError):
        transfer_submission(source, destination)


def test_process_timeout_and_minimal_environment(
    workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "must-not-inherit")
    code, stdout, _ = bounded_process(
        [sys.executable, "-c", "import os;print(os.environ.get('AZURE_CLIENT_SECRET'))"],
        cwd=workdir,
        timeout=5,
    )
    assert code == 0 and stdout.strip() == "None"
    with pytest.raises(subprocess.TimeoutExpired):
        bounded_process(
            [sys.executable, "-c", "import time;time.sleep(60)"], cwd=workdir, timeout=0.1
        )
