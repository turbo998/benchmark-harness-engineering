from __future__ import annotations

import shutil
import socket
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workdir() -> Iterator[Path]:
    path = ROOT / ".test-work" / uuid4().hex
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Tests must never contact a network or model")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)


@pytest.fixture(scope="session")
def saved_demo() -> Iterator[Path]:
    from benchmark_harness.cli import demo_workflow

    path = ROOT / ".test-work" / "saved-demo"
    demo_workflow(path)
    yield path
    shutil.rmtree(path)
