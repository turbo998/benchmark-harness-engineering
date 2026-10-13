"""Append-only per-attempt bundles. Hash verification precedes scoring/reporting."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from benchmark_harness.contracts import Artifact, Experiment, Result, canonical, digest
from benchmark_harness.manifest import write_frozen


def redact(text: str) -> str:
    text = re.sub(r"(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)[^\s\"']+", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s\"']+", r"\1[REDACTED]", text
    )
    text = re.sub(r"(?i)[A-Z]:\\Users\\[^\\\s\"']+", r"[HOME]", text)
    text = re.sub(r"/(?:home|Users)/[^/\s\"']+", "[HOME]", text)
    return text


def write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


class Archive:
    def __init__(self, root: Path, manifest: Experiment) -> None:
        self.root = root
        self.manifest = manifest
        if len({c[5:21] for c in manifest.case_ids}) != len(manifest.case_ids):
            raise ValueError("Case archive prefix collision; refusing ambiguous evidence paths")
        root.mkdir(parents=True, exist_ok=True)
        write_frozen(root / "manifest.json", manifest)

    def path(self, case_id: str, candidate_id: str, repeat: int, attempt: int) -> Path:
        if case_id not in self.manifest.case_ids or candidate_id not in {
            c.candidate_id for c in self.manifest.candidates
        }:
            raise ValueError("Attempt identity not in frozen manifest")
        if (
            not 0 <= repeat < self.manifest.repeats
            or not 1 <= attempt <= self.manifest.max_attempts
        ):
            raise ValueError("Repeat/attempt out of manifest bounds")
        return self.root / "attempts" / case_id[5:21] / candidate_id / str(repeat) / str(attempt)

    def begin(self, case_id: str, candidate_id: str, repeat: int, attempt: int) -> Path:
        path = self.path(case_id, candidate_id, repeat, attempt)
        path.mkdir(parents=True, exist_ok=False)
        write_once(
            path / "request.json",
            canonical(
                {
                    "experiment_id": self.manifest.experiment_id,
                    "manifest_hash": digest(self.manifest),
                    "case_id": case_id,
                    "candidate_id": candidate_id,
                    "repeat": repeat,
                    "attempt": attempt,
                    "retry_owner": "harness",
                }
            )
            + b"\n",
        )
        self.event(path, "reserved", {"mode": self.manifest.mode})
        return path

    def event(self, path: Path, action: str, detail: dict[str, Any]) -> None:
        count = len(list(path.glob("event-*.json")))
        write_once(
            path / f"event-{count + 1:04}.json",
            canonical(
                {
                    "sequence": count + 1,
                    "action": action,
                    "detail": detail,
                }
            )
            + b"\n",
        )

    def artifact(self, path: Path, name: str, payload: str) -> Artifact:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+\.(?:json|txt|py)", name):
            raise ValueError("Invalid artifact name")
        content = redact(payload).encode("utf-8")
        target = path / name
        write_once(target, content)
        return Artifact(
            path=target.relative_to(self.root).as_posix(),
            sha256=hashlib.sha256(content).hexdigest(),
            size=len(content),
        )

    def complete(self, path: Path, result: Result) -> None:
        if self.path(result.case_id, result.candidate_id, result.repeat, result.attempt) != path:
            raise ValueError("Result attempt identity drift")
        if result.manifest_hash != digest(self.manifest):
            raise ValueError("Result manifest drift")
        self.event(path, "completed", {"status": result.status})
        write_once(path / "result.json", canonical(result) + b"\n")
        files = sorted(p for p in path.iterdir() if p.is_file())
        receipt = {
            p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size": p.stat().st_size}
            for p in files
        }
        write_once(path / "receipt.json", canonical(receipt) + b"\n")

    def load(self) -> list[Result]:
        rows: list[Result] = []
        for path in sorted((self.root / "attempts").glob("*/*/*/*/result.json")):
            receipt_path = path.parent / "receipt.json"
            if not receipt_path.exists():
                raise ValueError("Incomplete archive receipt: preserve and recover this attempt")
            receipt = json.loads(receipt_path.read_bytes())
            actual_names = {p.name for p in path.parent.iterdir() if p.is_file()} - {"receipt.json"}
            if set(receipt) != actual_names:
                raise ValueError("Attempt file set changed")
            for name, expected in receipt.items():
                if not re.fullmatch(r"[a-zA-Z0-9._-]+", name):
                    raise ValueError("Unsafe receipt path")
                content = (path.parent / name).read_bytes()
                if (hashlib.sha256(content).hexdigest(), len(content)) != (
                    expected["sha256"],
                    expected["size"],
                ):
                    raise ValueError("Attempt artifact hash mismatch")
            row = Result.model_validate_json(path.read_bytes())
            if row.experiment_id != self.manifest.experiment_id or row.manifest_hash != digest(
                self.manifest
            ):
                raise ValueError("Result belongs to a different manifest")
            if row.cohort != self.manifest.environment.cohort:
                raise ValueError("Result cohort drift")
            if row.score.profile != self.manifest.score_profile:
                raise ValueError("Result scorer/profile drift")
            if self.path(row.case_id, row.candidate_id, row.repeat, row.attempt) != path.parent:
                raise ValueError("Result identity/path drift")
            for artifact in row.artifacts:
                target = self.root / artifact.path
                if target.parent != path.parent:
                    raise ValueError("Result artifact belongs to a different attempt")
                content = target.read_bytes()
                if (hashlib.sha256(content).hexdigest(), len(content)) != (
                    artifact.sha256,
                    artifact.size,
                ):
                    raise ValueError("Result artifact hash mismatch")
            rows.append(row)
        return rows

    def incomplete(self) -> list[Path]:
        return [
            p.parent
            for p in sorted((self.root / "attempts").glob("*/*/*/*/request.json"))
            if not (p.parent / "result.json").exists()
        ]
