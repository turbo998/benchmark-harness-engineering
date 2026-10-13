"""Opt-in Azure preflight and evidence-preserving lifecycle controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from benchmark_harness.broker import BrokerLedger, Settings
from benchmark_harness.budget import BudgetError, PriceTable, new_ledger

PROJECT = "benchmark-harness-engineering"


class AzureGateError(ValueError):
    pass


def _object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise AzureGateError(f"{name} must be an object with string keys")
    return {str(k): v for k, v in value.items()}


def _text(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AzureGateError(f"Missing non-empty {key}")
    return value


def _integer(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AzureGateError(f"{key} must be a positive integer")
    return value


def _money(data: dict[str, object], key: str, *, zero_allowed: bool = False) -> Decimal:
    value = data.get(key)
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise AzureGateError(f"Missing price/budget: {key}")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise AzureGateError(f"Invalid decimal: {key}") from error
    if not amount.is_finite() or amount < 0 or (not zero_allowed and amount == 0):
        raise AzureGateError(f"Invalid positive price/budget: {key}")
    return amount


def read_object(path: Path) -> dict[str, object]:
    try:
        return _object(json.loads(path.read_text(encoding="utf-8")), str(path))
    except (OSError, json.JSONDecodeError) as error:
        raise AzureGateError(f"Cannot read JSON {path}: {error}") from error


def validate_profile(data: dict[str, object]) -> None:
    if data.get("schema_version") != 1:
        raise AzureGateError("Unsupported Azure profile schema_version")
    for key in ("subscription_id", "resource_group", "location", "run_id", "lifecycle_owner"):
        _text(data, key)
    if not re.fullmatch(r"[a-z][a-z0-9]{1,7}", _text(data, "prefix")):
        raise AzureGateError("prefix must be 2-8 lowercase alphanumeric characters")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", _text(data, "run_id")):
        raise AzureGateError("Unsafe run_id")
    _text(data, "vm_size")
    image = _object(data.get("vm_image"), "vm_image")
    for key in ("publisher", "offer", "sku", "version"):
        _text(image, key)
    if image["version"] == "latest":
        raise AzureGateError("A frozen VM image version is required")
    egress = _object(data.get("egress"), "egress")
    if egress.get("approved") is not True:
        raise AzureGateError(
            "Explicit egress approval is required; default outbound is not assumed"
        )
    if egress.get("mode") == "existing":
        _text(egress, "subnet_id")
    elif egress.get("mode") != "outbound_ip":
        raise AzureGateError("egress.mode must be existing or explicitly approved outbound_ip")
    model = _object(data.get("model"), "model")
    for key in ("resource_group", "account_name", "deployment", "name", "version", "api_version"):
        _text(model, key)
    endpoint = urlparse(_text(model, "endpoint"))
    try:
        port = endpoint.port
    except ValueError as error:
        raise AzureGateError("Invalid model endpoint port") from error
    if (
        endpoint.scheme != "https"
        or not endpoint.hostname
        or not endpoint.hostname.endswith(".openai.azure.com")
        or endpoint.username
        or endpoint.password
        or port not in (None, 443)
        or endpoint.path not in ("", "/")
        or endpoint.query
        or endpoint.fragment
    ):
        raise AzureGateError(
            "First profile requires an approved public-Azure OpenAI resource endpoint"
        )
    if model.get("protocol") != "azure_openai_chat":
        raise AzureGateError("Only probed azure_openai_chat protocol is supported by this broker")
    _integer(model, "input_token_limit")
    _integer(model, "output_token_limit")
    if model.get("context_bound_verified") is not True:
        raise AzureGateError("Input reservation must cover the verified deployment context window")
    _text(model, "context_bound_source")
    if model.get("output_limit_verified") is not True:
        raise AzureGateError(
            "Hard completion limit capability must be verified before live inference"
        )
    prices = _object(data.get("prices"), "prices")
    if prices.get("currency") != "USD":
        raise AzureGateError("Price currency must be explicit USD")
    input_price = _money(prices, "input_per_million")
    output_price = _money(prices, "output_per_million")
    cached_price = _money(prices, "cache_read_per_million", zero_allowed=True)
    if cached_price > input_price:
        raise AzureGateError("Cache-read price cannot exceed the reserved input upper-bound price")
    try:
        effective_date = datetime.strptime(_text(prices, "effective_date"), "%Y-%m-%d").date()
    except ValueError as error:
        raise AzureGateError("Price effective_date must be YYYY-MM-DD") from error
    _text(prices, "source")
    table = PriceTable(
        effective_date=effective_date,
        source=_text(prices, "source"),
        model_version=_text(model, "version"),
        per_million={
            "input_tokens": input_price,
            "cache_read_tokens": cached_price,
            "cache_write_tokens": input_price,
            "output_tokens": output_price,
            "reasoning_tokens": output_price,
        },
    )
    try:
        table.estimate(dict.fromkeys(table.per_million, 0), today=datetime.now(UTC).date())
    except BudgetError as error:
        raise AzureGateError(str(error)) from error
    limits = _object(data.get("limits"), "limits")
    _money(limits, "model_budget_usd")
    for key in ("max_requests", "max_concurrency", "vm_lifetime_minutes"):
        _integer(limits, key)
    try:
        deadline = datetime.fromisoformat(_text(limits, "deadline_utc").replace("Z", "+00:00"))
    except ValueError as error:
        raise AzureGateError("Invalid deadline_utc") from error
    if deadline.tzinfo is None or deadline <= datetime.now(UTC):
        raise AzureGateError("Run deadline must be timezone-aware and in the future")
    approvals = _object(data.get("approvals"), "approvals")
    if approvals.get("data") != "synthetic":
        raise AzureGateError(
            "Customer/private datasets require a separate private-connectivity profile"
        )
    operator = _object(data.get("operator"), "operator")
    if operator.get("external_watchdog_verified") is not True:
        raise AzureGateError(
            "An independent compute-lifecycle watchdog is required; a TTL tag is not one"
        )
    storage = _object(data.get("storage"), "storage")
    for key in ("account", "artifacts_container", "ledger_container"):
        _text(storage, key)


def az_json(arguments: Sequence[str]) -> object:
    try:
        result = subprocess.run(
            ["az", *arguments, "--output", "json", "--only-show-errors"],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
            shell=False,
        )
        return json.loads(result.stdout)
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
        json.JSONDecodeError,
    ) as error:
        detail = (
            error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        )
        raise AzureGateError(f"Azure CLI check failed: {detail}") from error


def _rows(value: object, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise AzureGateError(f"{label} must be a list")
    return [_object(row, label) for row in value]


def live_preflight(
    data: dict[str, object],
    invoke: Callable[[Sequence[str]], object] = az_json,
) -> dict[str, object]:
    validate_profile(data)
    subscription = _text(data, "subscription_id")
    location = _text(data, "location")
    global_args = ["--subscription", subscription]
    account = _object(invoke(["account", "show", *global_args]), "account")
    if account.get("id") != subscription:
        raise AzureGateError("Azure account does not match the approved subscription")
    for namespace in (
        "Microsoft.Compute",
        "Microsoft.Network",
        "Microsoft.Storage",
        "Microsoft.App",
        "Microsoft.ManagedIdentity",
    ):
        provider = _object(
            invoke(["provider", "show", "--namespace", namespace, *global_args]), namespace
        )
        if provider.get("registrationState") != "Registered":
            raise AzureGateError(
                f"Provider is not Registered: {namespace}; no registration was attempted"
            )
    skus = _rows(
        invoke(
            [
                "vm",
                "list-skus",
                "--location",
                location,
                "--size",
                _text(data, "vm_size"),
                "--all",
                *global_args,
            ]
        ),
        "SKU",
    )
    selected = [sku for sku in skus if sku.get("name") == data["vm_size"]]
    if len(selected) != 1 or selected[0].get("restrictions"):
        raise AzureGateError(
            "VM SKU is absent, ambiguous or restricted for this location/subscription"
        )
    sku = selected[0]
    capabilities = {
        _text(row, "name"): _text(row, "value")
        for row in _rows(sku.get("capabilities"), "capability")
    }
    try:
        vcpus = int(capabilities["vCPUs"])
    except (KeyError, ValueError) as error:
        raise AzureGateError("VM vCPU requirement was not available") from error
    quotas = _rows(invoke(["vm", "list-usage", "--location", location, *global_args]), "quota")
    for name in ("cores", _text(sku, "family")):
        rows = [
            row for row in quotas if _object(row.get("name"), "quota.name").get("value") == name
        ]
        if len(rows) != 1:
            raise AzureGateError(f"Quota was unavailable: {name}")
        row = rows[0]
        used, limit = row.get("currentValue"), row.get("limit")
        if not isinstance(used, int) or not isinstance(limit, int) or limit - used < vcpus:
            raise AzureGateError(f"Insufficient or unknown remaining quota: {name}")
    model = _object(data["model"], "model")
    deployment = _object(
        invoke(
            [
                "cognitiveservices",
                "account",
                "deployment",
                "show",
                "--resource-group",
                _text(model, "resource_group"),
                "--name",
                _text(model, "account_name"),
                "--deployment-name",
                _text(model, "deployment"),
                *global_args,
            ]
        ),
        "deployment",
    )
    properties = _object(deployment.get("properties"), "deployment.properties")
    served = _object(properties.get("model"), "deployment.model")
    if served.get("version") != model["version"] or served.get("name") != model["name"]:
        raise AzureGateError("Served model version differs from the frozen profile")
    if properties.get("versionUpgradeOption") != "NoAutoUpgrade":
        raise AzureGateError(
            "Automatic model upgrades must be disabled for a frozen price/context bound"
        )
    return {
        "status": "selected_control_plane_checks_passed",
        "capacity": "not_guaranteed_by_quota",
        "data_plane_connectivity": "not_tested",
        "effective_inference_rbac": "not_tested",
        "what_if": "not_run",
        "cloud_apply": "not_performed",
        "paid_inference": "not_performed",
    }


def _export_files(inventory: dict[str, object], root: Path) -> list[dict[str, object]]:
    if inventory.get("dispatch_closed") is not True:
        raise AzureGateError("Trusted inventory must confirm future run dispatch is closed")
    if (
        inventory.get("ledger_sealed") is not True
        or type(inventory.get("in_flight")) is not int
        or inventory.get("in_flight") != 0
    ):
        raise AzureGateError("A sealed, drained ledger is required before evidence export")
    rows = _rows(inventory.get("files"), "inventory.files")
    required = {"ledger", "manifest", "accounting", "artifact", "log"}
    if not required.issubset({_text(row, "kind") for row in rows}):
        raise AzureGateError(
            "Export requires ledger, frozen manifest, accounting, artifacts and full logs"
        )
    base = root.resolve(strict=True)
    seen: set[str] = set()
    for row in rows:
        relative = _text(row, "path")
        path = base / relative
        if relative in seen or Path(relative).is_absolute() or path.is_symlink():
            raise AzureGateError("Duplicate, absolute or symlink export path")
        seen.add(relative)
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(base)
        except (OSError, ValueError) as error:
            raise AzureGateError("Missing or escaping export file") from error
        if not resolved.is_file():
            raise AzureGateError("Export entries must be files")
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if digest != _text(row, "sha256"):
            raise AzureGateError(f"Export hash mismatch: {relative}")
    ledgers = [row for row in rows if row.get("kind") == "ledger"]
    settings = [row for row in rows if row.get("kind") == "accounting"]
    manifests = [row for row in rows if row.get("kind") == "manifest"]
    if len(ledgers) != 1 or len(settings) != 1 or len(manifests) != 1:
        raise AzureGateError(
            "Exactly one ledger, frozen manifest and accounting settings are required"
        )
    try:
        ledger = BrokerLedger.model_validate_json((base / _text(ledgers[0], "path")).read_bytes())
        metadata = Settings.model_validate_json((base / _text(settings[0], "path")).read_bytes())
    except ValidationError as error:
        raise AzureGateError(
            "Exported ledger/accounting metadata is not a valid trusted contract"
        ) from error
    if (
        not ledger.dispatch_closed
        or not ledger.sealed
        or any(item.state in ("reserved", "dispatched") for item in ledger.state.reservations)
        or ledger.target_hash != metadata.target_hash
        or ledger.policy.price_table_hash != metadata.prices.table_hash
        or ledger.state.policy_hash != new_ledger(ledger.policy).policy_hash
    ):
        raise AzureGateError("Actual ledger is not drained/sealed or accounting identity differs")
    manifest = read_object(base / _text(manifests[0], "path"))
    if not manifest.get("experiment_id") or not manifest.get("dataset_hash"):
        raise AzureGateError("Frozen experiment manifest is missing its identity")
    return rows


def azure_source_inventory(data: dict[str, object]) -> list[dict[str, object]]:
    """Read every scoped persisted object; callers must have stopped all producers."""
    from azure.core import MatchConditions
    from azure.core.exceptions import AzureError
    from azure.identity import AzureCliCredential
    from azure.storage.blob import BlobServiceClient

    storage = _object(data.get("storage"), "storage")
    run_id = _text(data, "run_id")
    account = _text(storage, "account")
    if not re.fullmatch(r"[a-z0-9]{3,24}", account):
        raise AzureGateError("Invalid source storage account")
    client = BlobServiceClient(
        f"https://{account}.blob.core.windows.net",
        credential=AzureCliCredential(),
        retry_total=0,
        connection_timeout=5,
        read_timeout=15,
    )
    rows: list[dict[str, object]] = []
    try:
        containers = {item.name for item in client.list_containers()}
        expected_containers = {
            _text(storage, "artifacts_container"),
            _text(storage, "ledger_container"),
        }
        if len(expected_containers) != 2 or containers != expected_containers:
            raise AzureGateError(
                "Source account contains missing or unexpected evidence containers"
            )
        ledger_container = client.get_container_client(_text(storage, "ledger_container"))
        if [item.name for item in ledger_container.list_blobs()] != [f"{run_id}.json"]:
            raise AzureGateError("Ledger container is not exclusively owned by this run")
        container = client.get_container_client(_text(storage, "artifacts_container"))
        prefix = f"{run_id}/"
        for item in container.list_blobs():
            if not isinstance(item.name, str) or not item.name.startswith(prefix):
                raise AzureGateError("Source object listing escaped run scope")
            relative = item.name[len(prefix) :]
            if not relative or any(
                not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or part in (".", "..")
                for part in relative.split("/")
            ):
                raise AzureGateError("Unsafe source artifact path")
            blob = container.get_blob_client(item.name)
            if not isinstance(item.etag, str) or not item.etag:
                raise AzureGateError("Source artifact has no immutable ETag")
            content = blob.download_blob(
                etag=item.etag,
                match_condition=MatchConditions.IfNotModified,
            ).readall()
            rows.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest()})
        ledger = client.get_blob_client(_text(storage, "ledger_container"), f"{run_id}.json")
        properties = ledger.get_blob_properties()
        if not isinstance(properties.etag, str) or not properties.etag:
            raise AzureGateError("Source ledger has no immutable ETag")
        content = ledger.download_blob(
            etag=properties.etag,
            match_condition=MatchConditions.IfNotModified,
        ).readall()
        rows.append({"path": "ledger.json", "sha256": hashlib.sha256(content).hexdigest()})
    except AzureError as error:
        raise AzureGateError(
            "Complete source snapshot failed or changed; no deletion allowed"
        ) from error
    finally:
        client.close()
    return rows


def verify_complete_source_export(
    data: dict[str, object],
    receipt_path: Path,
    read_source: Callable[[dict[str, object]], list[dict[str, object]]] = azure_source_inventory,
) -> None:
    evidence = _object(data.get("evidence"), "evidence")
    if evidence.get("trusted_producers_quiesced") is not True:
        raise AzureGateError(
            "Trusted controller must stop all artifact/log producers before cleanup"
        )
    expected = evidence.get("required_paths")
    if (
        not isinstance(expected, list)
        or not expected
        or not all(isinstance(p, str) for p in expected)
    ):
        raise AzureGateError("Controller-approved complete evidence paths are required")
    receipt = read_object(receipt_path)
    inventory = read_object(Path(_text(receipt, "inventory_path")))
    rows = _export_files(inventory, Path(_text(receipt, "export_root")))
    accounting = next(row for row in rows if row["kind"] == "accounting")
    metadata = Settings.model_validate_json(
        (Path(_text(receipt, "export_root")) / _text(accounting, "path")).read_bytes()
    )
    storage = _object(data.get("storage"), "storage")
    if (
        metadata.ledger_url.rstrip("/")
        != f"https://{_text(storage, 'account')}.blob.core.windows.net"
        or metadata.ledger_container != _text(storage, "ledger_container")
    ):
        raise AzureGateError("Accounting namespace differs from the approved source storage")
    exported = {_text(row, "path"): _text(row, "sha256") for row in rows}
    if len(exported) != len(rows) or not set(expected).issubset(exported):
        raise AzureGateError("Export misses controller-approved required evidence")
    manifest = next(row for row in rows if row["kind"] == "manifest")
    if manifest["sha256"] != _text(evidence, "frozen_manifest_sha256").lower():
        raise AzureGateError("Exported manifest differs from the approved frozen experiment")
    source_rows = read_source(data)
    source = {_text(row, "path"): _text(row, "sha256") for row in source_rows}
    if len(source) != len(source_rows) or source != exported:
        raise AzureGateError(
            "Source/export file sets or hashes differ; incomplete or changed export"
        )


def write_export_receipt(inventory_path: Path, root: Path, destination: Path) -> None:
    inventory = read_object(inventory_path)
    _text(inventory, "run_id")
    _text(inventory, "resource_group")
    _export_files(inventory, root)
    receipt = {
        "schema_version": 1,
        "run_id": inventory["run_id"],
        "resource_group": inventory["resource_group"],
        "export_root": str(root.resolve()),
        "inventory_path": str(inventory_path.resolve()),
        "inventory_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        "verified_utc": datetime.now(UTC).isoformat(),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        existing = read_object(destination)
        for key in (
            "schema_version",
            "run_id",
            "resource_group",
            "export_root",
            "inventory_path",
            "inventory_sha256",
        ):
            if existing.get(key) != receipt[key]:
                raise AzureGateError("Existing receipt does not match this verified export")
        verify_export_receipt(
            destination, _text(inventory, "run_id"), _text(inventory, "resource_group")
        )
        return
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(receipt, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    except OSError as error:
        raise AzureGateError(
            "Receipt could not be atomically published; rerun export proof"
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verify_export_receipt(path: Path, run_id: str, resource_group: str) -> None:
    receipt = read_object(path)
    if (
        receipt.get("schema_version") != 1
        or receipt.get("run_id") != run_id
        or receipt.get("resource_group") != resource_group
    ):
        raise AzureGateError("Export receipt belongs to a different run/resource group")
    inventory_path = Path(_text(receipt, "inventory_path"))
    if hashlib.sha256(inventory_path.read_bytes()).hexdigest() != _text(
        receipt, "inventory_sha256"
    ):
        raise AzureGateError("Export inventory changed after verification")
    inventory = read_object(inventory_path)
    if inventory.get("run_id") != run_id or inventory.get("resource_group") != resource_group:
        raise AzureGateError("Export inventory scope does not match receipt")
    _export_files(inventory, Path(_text(receipt, "export_root")))


def owned_resource_ids(
    resources: object, subscription: str, resource_group: str, run_id: str
) -> list[str]:
    scope = f"/subscriptions/{subscription}/resourceGroups/{resource_group}/".lower()
    identifiers: list[str] = []
    for resource in _rows(resources, "resources"):
        identifier = _text(resource, "id")
        tags = _object(resource.get("tags"), "resource.tags")
        if (
            not identifier.lower().startswith(scope)
            or tags.get("project") != PROJECT
            or tags.get("run_id") != run_id
        ):
            raise AzureGateError(
                "Cleanup scope contains unowned or foreign resources; no deletion permitted"
            )
        identifiers.append(identifier)
    if not identifiers:
        raise AzureGateError("No owned resources found; do not issue a broad delete")
    return identifiers


def az_mutation(arguments: Sequence[str]) -> None:
    try:
        subprocess.run(
            ["az", *arguments, "--only-show-errors"],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
            shell=False,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
        detail = (
            error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        )
        raise AzureGateError(
            f"Azure mutation failed or its completion is unknown: {detail}"
        ) from error


def request_owned_group_deletion(
    data: dict[str, object],
    receipt: Path,
    *,
    approved: bool,
    invoke: Callable[[Sequence[str]], object] = az_json,
    mutate: Callable[[Sequence[str]], None] = az_mutation,
    read_source: Callable[[dict[str, object]], list[dict[str, object]]] = azure_source_inventory,
) -> dict[str, object]:
    approvals = _object(data.get("approvals"), "approvals")
    if not approved or approvals.get("destructive_cleanup") is not True:
        raise AzureGateError(
            "Both explicit deletion confirmation and profile cleanup approval are required"
        )
    subscription = _text(data, "subscription_id")
    group = _text(data, "resource_group")
    run_id = _text(data, "run_id")
    verify_export_receipt(receipt, run_id, group)
    try:
        group_info = _object(
            invoke(["group", "show", "--name", group, "--subscription", subscription]), "group"
        )
    except AzureGateError as error:
        cause = error.__cause__
        if (
            isinstance(cause, subprocess.CalledProcessError)
            and "ResourceGroupNotFound" in cause.stderr
        ):
            return {
                "status": "owned_group_absent",
                "completion_verified": True,
                "deletion_performed": False,
            }
        raise
    tags = _object(group_info.get("tags"), "group.tags")
    if tags.get("project") != PROJECT or tags.get("run_id") != run_id:
        raise AzureGateError("Resource group is not exclusively owned by this experiment")
    properties = _object(group_info.get("properties", {}), "group.properties")
    if properties.get("provisioningState") == "Deleting":
        return {"status": "owned_group_deletion_in_progress", "completion_verified": False}
    fresh = invoke(["resource", "list", "--resource-group", group, "--subscription", subscription])
    ids = owned_resource_ids(fresh, subscription, group, run_id)
    storage = _object(data.get("storage"), "storage")
    source_storage_id = (
        f"/subscriptions/{subscription}/resourceGroups/{group}/providers/"
        f"Microsoft.Storage/storageAccounts/{_text(storage, 'account')}"
    ).lower()
    if source_storage_id not in {identifier.lower() for identifier in ids}:
        raise AzureGateError(
            "Source evidence storage is not an owned resource in the deletion scope"
        )
    for resource in _rows(fresh, "resources"):
        if resource.get("type") == "Microsoft.Compute/virtualMachines":
            view = _object(
                invoke(
                    [
                        "vm",
                        "get-instance-view",
                        "--name",
                        _text(resource, "name"),
                        "--resource-group",
                        group,
                        "--subscription",
                        subscription,
                    ]
                ),
                "vm view",
            )
            statuses = _rows(
                _object(view.get("instanceView"), "instanceView").get("statuses"), "statuses"
            )
            if not any(row.get("code") == "PowerState/deallocated" for row in statuses):
                raise AzureGateError(
                    "Deallocate owned workers before an immutable evidence snapshot"
                )
        if resource.get("type") == "Microsoft.App/containerApps":
            revisions = _rows(
                invoke(
                    [
                        "containerapp",
                        "revision",
                        "list",
                        "--name",
                        _text(resource, "name"),
                        "--resource-group",
                        group,
                        "--subscription",
                        subscription,
                    ]
                ),
                "revisions",
            )
            if not revisions or any(
                _object(row.get("properties"), "revision.properties").get("active") is not False
                for row in revisions
            ):
                raise AzureGateError(
                    "Deactivate broker revisions before source verification/deletion"
                )
    verify_complete_source_export(data, receipt, read_source)
    mutate(
        ["group", "delete", "--name", group, "--subscription", subscription, "--yes", "--no-wait"]
    )
    return {
        "status": "owned_group_deletion_requested",
        "resource_count": len(ids),
        "completion_verified": False,
        "external_inference_roles": "not_deleted; review separately if previously created",
        "export_receipt": str(receipt),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    preflight = subcommands.add_parser("preflight")
    preflight.add_argument("--profile", type=Path, required=True)
    preflight.add_argument("--live-checks", action="store_true")
    export = subcommands.add_parser("export-proof")
    export.add_argument("--inventory", type=Path, required=True)
    export.add_argument("--export-root", type=Path, required=True)
    export.add_argument("--receipt", type=Path, required=True)
    cleanup = subcommands.add_parser("cleanup-plan")
    cleanup.add_argument("--profile", type=Path, required=True)
    cleanup.add_argument("--resources", type=Path, required=True)
    cleanup.add_argument("--receipt", type=Path, required=True)
    delete = subcommands.add_parser("cleanup")
    delete.add_argument("--profile", type=Path, required=True)
    delete.add_argument("--receipt", type=Path, required=True)
    delete.add_argument("--approved-delete", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "export-proof":
            write_export_receipt(args.inventory, args.export_root, args.receipt)
            output: dict[str, object] = {
                "status": "local_export_hashes_verified; live source completeness is a deletion gate",
                "receipt": str(args.receipt),
            }
        elif args.command == "cleanup":
            data = read_object(args.profile)
            output = request_owned_group_deletion(data, args.receipt, approved=args.approved_delete)
        else:
            data = read_object(args.profile)
            if args.command == "preflight":
                validate_profile(data)
                output = (
                    live_preflight(data)
                    if args.live_checks
                    else {
                        "status": "offline_profile_valid",
                        "live_checks": "not_run",
                        "cloud_apply": "not_performed",
                        "paid_inference": "not_performed",
                    }
                )
            else:
                run_id = _text(data, "run_id")
                resource_group = _text(data, "resource_group")
                verify_export_receipt(args.receipt, run_id, resource_group)
                resources = json.loads(args.resources.read_text(encoding="utf-8"))
                ids = owned_resource_ids(
                    resources, _text(data, "subscription_id"), resource_group, run_id
                )
                output = {
                    "status": "cleanup_preview_only",
                    "resource_ids": ids,
                    "deletion_performed": False,
                }
    except (AzureGateError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
