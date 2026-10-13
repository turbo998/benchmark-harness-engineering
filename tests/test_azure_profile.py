import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from benchmark_harness.azure import (
    AzureGateError,
    azure_source_inventory,
    live_preflight,
    owned_resource_ids,
    request_owned_group_deletion,
    validate_profile,
    verify_complete_source_export,
    verify_export_receipt,
    write_export_receipt,
)
from benchmark_harness.broker import BrokerLedger, Settings
from benchmark_harness.budget import BudgetPolicy, PriceTable, new_ledger

MANIFEST_BYTES = json.dumps(
    {"experiment_id": "synthetic-experiment", "dataset_hash": "synthetic-dataset"}
).encode()


def profile() -> dict[str, object]:
    return {
        "schema_version": 1,
        "prefix": "bh",
        "subscription_id": "synthetic-subscription",
        "resource_group": "synthetic-rg",
        "location": "synthetic-region",
        "run_id": "synthetic-run",
        "lifecycle_owner": "synthetic-operator",
        "vm_size": "Standard_D4s_v5",
        "vm_image": {"publisher": "test", "offer": "test", "sku": "gen2", "version": "1.2.3"},
        "egress": {"mode": "existing", "approved": True, "subnet_id": "/synthetic/subnet"},
        "model": {
            "resource_group": "synthetic-model-rg",
            "account_name": "synthetic-model",
            "deployment": "synthetic-deployment",
            "name": "synthetic",
            "endpoint": "https://synthetic-model.openai.azure.com/",
            "version": "synthetic-v1",
            "api_version": "synthetic-api",
            "protocol": "azure_openai_chat",
            "input_token_limit": 1000,
            "context_bound_verified": True,
            "context_bound_source": "synthetic context-window fixture",
            "output_token_limit": 100,
            "output_limit_verified": True,
        },
        "prices": {
            "currency": "USD",
            "input_per_million": "2",
            "output_per_million": "4",
            "cache_read_per_million": "1",
            "effective_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "source": "synthetic fixture",
        },
        "limits": {
            "model_budget_usd": "1",
            "max_requests": 2,
            "max_concurrency": 1,
            "vm_lifetime_minutes": 30,
            "deadline_utc": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        },
        "approvals": {"data": "synthetic", "cloud_apply": False, "paid_inference": False},
        "operator": {"external_watchdog_verified": True},
        "storage": {
            "account": "synthetic",
            "artifacts_container": "artifacts",
            "ledger_container": "ledger",
        },
        "evidence": {
            "trusted_producers_quiesced": True,
            "frozen_manifest_sha256": hashlib.sha256(MANIFEST_BYTES).hexdigest(),
            "required_paths": [
                "ledger.json",
                "manifest.json",
                "settings.json",
                "attempt-1.json",
                "stdout.log",
                "stderr.log",
            ],
        },
    }


def test_offline_profile_does_not_run_azure() -> None:
    validate_profile(profile())


@pytest.mark.parametrize("field", ["subscription_id", "location", "lifecycle_owner"])
def test_missing_binding_is_blocked(field: str) -> None:
    data = profile()
    data[field] = ""
    with pytest.raises(AzureGateError, match="Missing"):
        validate_profile(data)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("egress", {"mode": "default", "approved": True}),
        ("operator", {"external_watchdog_verified": False}),
        ("approvals", {"data": "private"}),
        ("prices", {"currency": "USD", "input_per_million": "NaN"}),
        ("vm_image", {"publisher": "x", "offer": "x", "sku": "x", "version": "latest"}),
    ],
)
def test_safety_omissions_block_preflight(field: str, replacement: object) -> None:
    data = profile()
    data[field] = replacement
    with pytest.raises(AzureGateError):
        validate_profile(data)


def test_live_preflight_checks_both_quotas_without_writes() -> None:
    calls: list[list[str]] = []

    def fake(arguments: Sequence[str]) -> object:
        calls.append(list(arguments))
        if arguments[:2] == ["account", "show"]:
            return {"id": "synthetic-subscription"}
        if arguments[:2] == ["provider", "show"]:
            return {"registrationState": "Registered"}
        if arguments[:2] == ["vm", "list-skus"]:
            return [
                {
                    "name": "Standard_D4s_v5",
                    "family": "standardDSv5Family",
                    "restrictions": [],
                    "capabilities": [{"name": "vCPUs", "value": "4"}],
                }
            ]
        if arguments[:2] == ["vm", "list-usage"]:
            return [
                {"name": {"value": name}, "currentValue": 0, "limit": 4}
                for name in ("cores", "standardDSv5Family")
            ]
        if arguments[:3] == ["cognitiveservices", "account", "deployment"]:
            return {
                "properties": {
                    "model": {"name": "synthetic", "version": "synthetic-v1"},
                    "versionUpgradeOption": "NoAutoUpgrade",
                }
            }
        raise AssertionError(f"Unexpected command: {arguments}")

    result = live_preflight(profile(), fake)
    assert result["cloud_apply"] == "not_performed"
    assert result["data_plane_connectivity"] == "not_tested"
    assert not any(word in {"create", "register", "delete"} for call in calls for word in call)


def inventory(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "private-export"
    root.mkdir()
    settings = Settings(
        endpoint="https://synthetic.openai.azure.com",
        deployment="synthetic-deployment",
        model_name="synthetic",
        api_version="synthetic",
        input_limit=1000,
        output_limit=100,
        input_bound_verified=True,
        input_bound_source="synthetic context",
        ledger_url="https://synthetic.blob.core.windows.net",
        ledger_container="ledger",
        prices=PriceTable(
            effective_date=datetime.now(UTC).date(),
            source="synthetic",
            model_version="v1",
            per_million=dict.fromkeys(
                (
                    "input_tokens",
                    "cache_read_tokens",
                    "cache_write_tokens",
                    "output_tokens",
                    "reasoning_tokens",
                ),
                Decimal(1),
            ),
        ),
    )
    policy = BudgetPolicy(
        budget_usd=Decimal(1),
        max_calls=1,
        max_output_tokens=100,
        max_concurrency=1,
        approval_id="synthetic",
        price_table_hash=settings.prices.table_hash,
    )
    ledger = BrokerLedger(
        policy=policy,
        state=new_ledger(policy),
        target_hash=settings.target_hash,
        dispatch_closed=True,
        sealed=True,
    )
    content = {
        "ledger.json": (ledger.model_dump_json().encode(), "ledger"),
        "manifest.json": (MANIFEST_BYTES, "manifest"),
        "settings.json": (settings.model_dump_json().encode(), "accounting"),
        "attempt-1.json": (b'{"source":"synthetic"}', "artifact"),
        "stdout.log": (b"synthetic full stdout", "log"),
        "stderr.log": (b"synthetic full stderr", "log"),
    }
    rows = []
    for name, (payload, kind) in content.items():
        (root / name).write_bytes(payload)
        rows.append({"path": name, "kind": kind, "sha256": hashlib.sha256(payload).hexdigest()})
    path = tmp_path / "trusted-inventory.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "synthetic-run",
                "resource_group": "synthetic-rg",
                "dispatch_closed": True,
                "ledger_sealed": True,
                "in_flight": 0,
                "files": rows,
            }
        ),
        encoding="utf-8",
    )
    return path, root


def test_verified_export_is_stable_but_tampering_blocks_cleanup(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    receipt = tmp_path / "receipt.json"
    write_export_receipt(source, root, receipt)
    original = receipt.read_bytes()
    write_export_receipt(source, root, receipt)
    assert receipt.read_bytes() == original
    verify_export_receipt(receipt, "synthetic-run", "synthetic-rg")
    verify_export_receipt(receipt, "synthetic-run", "synthetic-rg")
    (root / "ledger.json").write_text("changed", encoding="utf-8")
    with pytest.raises(AzureGateError, match="hash mismatch"):
        verify_export_receipt(receipt, "synthetic-run", "synthetic-rg")


def test_receipt_refuses_an_unsealed_or_in_flight_export(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    data = json.loads(source.read_text(encoding="utf-8"))
    data["in_flight"] = 1
    source.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(AzureGateError, match="drained"):
        write_export_receipt(source, root, tmp_path / "receipt.json")


def test_existing_invalid_receipt_is_never_overwritten(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    receipt = tmp_path / "receipt.json"
    receipt.write_text('{"run_id":"different-run"}', encoding="utf-8")
    original = receipt.read_bytes()
    with pytest.raises(AzureGateError, match="does not match"):
        write_export_receipt(source, root, receipt)
    assert receipt.read_bytes() == original


def test_failed_receipt_flush_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchmark_harness import azure

    source, root = inventory(tmp_path)
    receipt = tmp_path / "receipt.json"

    def fail(_: int) -> None:
        raise OSError("synthetic flush interruption")

    monkeypatch.setattr(azure.os, "fsync", fail)
    with pytest.raises(AzureGateError, match="atomically"):
        write_export_receipt(source, root, receipt)
    assert not receipt.exists()
    assert not list(tmp_path.glob(".receipt.json.*.tmp"))


def test_interrupted_export_never_creates_receipt(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    (root / "ledger.json").unlink()
    receipt = tmp_path / "receipt.json"
    with pytest.raises(AzureGateError):
        write_export_receipt(source, root, receipt)
    assert not receipt.exists()


def test_wrong_scope_and_foreign_resources_block_cleanup(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    receipt = tmp_path / "receipt.json"
    write_export_receipt(source, root, receipt)
    with pytest.raises(AzureGateError, match="different run"):
        verify_export_receipt(receipt, "other-run", "synthetic-rg")
    resources = [
        {
            "id": "/subscriptions/s/resourceGroups/other/providers/Microsoft.Compute/virtualMachines/x",
            "tags": {"project": "benchmark-harness-engineering", "run_id": "synthetic-run"},
        }
    ]
    with pytest.raises(AzureGateError, match="unowned"):
        owned_resource_ids(resources, "s", "synthetic-rg", "synthetic-run")


def test_missing_ledger_and_path_escape_rejected(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    data = json.loads(source.read_text(encoding="utf-8"))
    data["files"][0]["kind"] = "artifact"
    source.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(AzureGateError, match="accounting"):
        write_export_receipt(source, root, tmp_path / "no-ledger.json")
    data["files"][0]["kind"] = "ledger"
    data["files"][0]["path"] = "../trusted-inventory.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(AzureGateError, match="escaping"):
        write_export_receipt(source, root, tmp_path / "escape.json")


def test_cleanup_requires_approval_before_any_cloud_call(tmp_path: Path) -> None:
    def forbidden(arguments: Sequence[str]) -> object:
        raise AssertionError("Unapproved cleanup called Azure")

    with pytest.raises(AzureGateError, match="confirmation"):
        request_owned_group_deletion(
            profile(), tmp_path / "absent.json", approved=False, invoke=forbidden
        )


def test_cleanup_rechecks_live_ownership_before_requesting_delete(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    receipt = tmp_path / "receipt.json"
    write_export_receipt(source, root, receipt)
    data = profile()
    data["approvals"] = {"destructive_cleanup": True}
    mutations: list[list[str]] = []
    tags = {"project": "benchmark-harness-engineering", "run_id": "synthetic-run"}

    def fake(arguments: Sequence[str]) -> object:
        if arguments[:2] == ["group", "show"]:
            return {"tags": tags}
        if arguments[:3] == ["containerapp", "revision", "list"]:
            return [{"properties": {"active": False}}]
        return [
            {
                "id": "/subscriptions/synthetic-subscription/resourceGroups/synthetic-rg/providers/Microsoft.App/containerApps/broker",
                "name": "broker",
                "type": "Microsoft.App/containerApps",
                "tags": tags,
            },
            {
                "id": "/subscriptions/synthetic-subscription/resourceGroups/synthetic-rg/providers/Microsoft.Storage/storageAccounts/synthetic",
                "name": "synthetic",
                "type": "Microsoft.Storage/storageAccounts",
                "tags": tags,
            },
        ]

    def mutation(arguments: Sequence[str]) -> None:
        mutations.append(list(arguments))

    result = request_owned_group_deletion(
        data,
        receipt,
        approved=True,
        invoke=fake,
        mutate=mutation,
        read_source=lambda _: json.loads(source.read_text())["files"],
    )
    assert result["completion_verified"] is False
    assert mutations[0][:2] == ["group", "delete"]
    assert "--no-wait" in mutations[0]


def test_missing_remote_artifact_prevents_actual_deletion(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    receipt = tmp_path / "receipt.json"
    write_export_receipt(source, root, receipt)
    data = profile()
    data["approvals"] = {"destructive_cleanup": True}
    tags = {"project": "benchmark-harness-engineering", "run_id": "synthetic-run"}
    called: list[str] = []

    def invoke(arguments: Sequence[str]) -> object:
        if arguments[:2] == ["group", "show"]:
            return {"tags": tags}
        return [
            {
                "id": "/subscriptions/synthetic-subscription/resourceGroups/synthetic-rg/providers/Microsoft.Storage/storageAccounts/synthetic",
                "name": "synthetic",
                "type": "Microsoft.Storage/storageAccounts",
                "tags": tags,
            }
        ]

    source_rows = json.loads(source.read_text())["files"]
    source_rows.append({"path": "unexported-attempt.json", "sha256": "0" * 64})
    with pytest.raises(AzureGateError, match="file sets"):
        request_owned_group_deletion(
            data,
            receipt,
            approved=True,
            invoke=invoke,
            mutate=lambda _: called.append("delete"),
            read_source=lambda _: source_rows,
        )
    assert not called


def test_partial_or_changed_source_never_authorizes_cleanup(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    receipt = tmp_path / "receipt.json"
    write_export_receipt(source, root, receipt)
    source_rows = json.loads(source.read_text())["files"]
    source_rows.append({"path": "missing-attempt.json", "sha256": "0" * 64})
    with pytest.raises(AzureGateError, match="file sets"):
        verify_complete_source_export(profile(), receipt, lambda _: source_rows)


def test_inventory_flags_cannot_replace_actual_ledger_seal(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    ledger_path = root / "ledger.json"
    ledger = json.loads(ledger_path.read_text())
    ledger["sealed"] = False
    ledger_path.write_text(json.dumps(ledger))
    data = json.loads(source.read_text())
    data["files"][0]["sha256"] = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    source.write_text(json.dumps(data))
    with pytest.raises(AzureGateError, match="Actual ledger"):
        write_export_receipt(source, root, tmp_path / "receipt.json")


@pytest.mark.parametrize(
    "drift",
    ["none", "extra-container", "extra-ledger", "other-run", "artifact-etag", "ledger-etag"],
)
def test_source_sdk_snapshot_is_complete_and_etag_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    sdk = pytest.importorskip("azure.storage.blob")
    from azure.core import MatchConditions

    source, root = inventory(tmp_path)
    rows = json.loads(source.read_text())["files"]
    payloads = {
        f"synthetic-run/{row['path']}": (root / row["path"]).read_bytes()
        for row in rows
        if row["kind"] != "ledger"
    }
    if drift == "other-run":
        payloads["another-run/attempt.json"] = b"foreign"
    downloads: list[str] = []
    closed: list[bool] = []

    class Blob:
        def __init__(self, name: str) -> None:
            self.name = name

        def get_blob_properties(self) -> SimpleNamespace:
            return SimpleNamespace(etag=None if drift == "ledger-etag" else "frozen")

        def download_blob(self, *, etag: str, match_condition: object) -> SimpleNamespace:
            assert etag == "frozen"
            assert match_condition == MatchConditions.IfNotModified
            downloads.append(self.name)
            content = (
                (root / "ledger.json").read_bytes()
                if self.name == "synthetic-run.json"
                else payloads[self.name]
            )
            return SimpleNamespace(readall=lambda: content)

    class Container:
        def __init__(self, name: str) -> None:
            self.name = name

        def list_blobs(self) -> list[SimpleNamespace]:
            names = (
                ["synthetic-run.json"] + (["other.json"] if drift == "extra-ledger" else [])
                if self.name == "ledger"
                else list(payloads)
            )
            return [
                SimpleNamespace(name=name, etag=None if drift == "artifact-etag" else "frozen")
                for name in names
            ]

        def get_blob_client(self, name: str) -> Blob:
            return Blob(name)

    class Client:
        def __init__(self, url: str, **kwargs: object) -> None:
            assert url == "https://synthetic.blob.core.windows.net"
            assert kwargs["retry_total"] == 0

        def list_containers(self) -> list[SimpleNamespace]:
            names = ["ledger", "artifacts"] + (["unknown"] if drift == "extra-container" else [])
            return [SimpleNamespace(name=name) for name in names]

        def get_container_client(self, name: str) -> Container:
            return Container(name)

        def get_blob_client(self, container: str, name: str) -> Blob:
            assert container == "ledger"
            return Blob(name)

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(sdk, "BlobServiceClient", Client)
    if drift == "none":
        actual = azure_source_inventory(profile())
        assert {row["path"]: row["sha256"] for row in actual} == {
            row["path"]: row["sha256"] for row in rows
        }
        assert len(downloads) == len(rows)
    else:
        with pytest.raises(AzureGateError):
            azure_source_inventory(profile())
    assert closed == [True]


def test_active_producers_block_source_read(tmp_path: Path) -> None:
    source, root = inventory(tmp_path)
    receipt = tmp_path / "receipt.json"
    write_export_receipt(source, root, receipt)
    data = profile()
    data["evidence"] = {"trusted_producers_quiesced": False}

    def forbidden(_: dict[str, object]) -> list[dict[str, object]]:
        raise AssertionError("Active producers must prevent source reads")

    with pytest.raises(AzureGateError, match="stop all"):
        verify_complete_source_export(data, receipt, forbidden)
