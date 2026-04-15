#!/usr/bin/env python3
"""Verify transaction ingest contract integrity and anti-drift invariants.

Checks:
1) Contract schema has required structure and strictness fields.
2) Shared loader constants match schema values.
3) Backend router and ingestion bridge import shared contract constants.
4) Backend router and ingestion bridge do not hardcode contract constants.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "transaction-ingest-contract.json"
BACKEND_ROUTER_PATH = ROOT / "backend" / "app" / "routers" / "transactions.py"
BRIDGE_PATH = ROOT / "ingestion" / "neo4j_writer.py"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.contracts.transaction_ingest_contract import (  # noqa: E402
    INGEST_CONTRACT_VERSION,
    SUPPORTED_INGEST_CHANNELS,
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _ok(message: str) -> None:
    print(f"OK: {message}")


def _fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def _validate_schema() -> tuple[int, str, set[str]]:
    status = 0

    if not SCHEMA_PATH.exists():
        return _fail(f"schema file missing: {SCHEMA_PATH}"), "", set()

    try:
        schema = json.loads(_read(SCHEMA_PATH))
    except Exception as exc:
        return _fail(f"schema JSON parse failed: {exc}"), "", set()

    if schema.get("type") != "object":
        status |= _fail("schema.type must be 'object'")
    else:
        _ok("schema type is object")

    if schema.get("additionalProperties") is not False:
        status |= _fail("schema.additionalProperties must be false")
    else:
        _ok("schema additionalProperties is false")

    required = set(schema.get("required") or [])
    required_minimum = {
        "contract_version",
        "from_account",
        "to_account",
        "amount",
        "channel",
    }
    if not required_minimum.issubset(required):
        status |= _fail("schema required fields missing one or more core keys")
    else:
        _ok("schema required fields include core ingest keys")

    properties = schema.get("properties") or {}
    version = str((properties.get("contract_version") or {}).get("const") or "").strip()
    if not version:
        status |= _fail("schema properties.contract_version.const missing")
    else:
        _ok(f"schema version constant present: {version}")

    channels = {
        str(channel).strip().upper()
        for channel in (properties.get("channel") or {}).get("enum") or []
        if str(channel).strip()
    }
    if not channels:
        status |= _fail("schema properties.channel.enum must not be empty")
    else:
        _ok(f"schema channels enum present with {len(channels)} values")

    return status, version, channels


def _validate_loader_matches_schema(version: str, channels: set[str]) -> int:
    status = 0

    if INGEST_CONTRACT_VERSION != version:
        status |= _fail(
            "shared loader contract_version mismatch with schema "
            f"(loader={INGEST_CONTRACT_VERSION}, schema={version})"
        )
    else:
        _ok("shared loader contract_version matches schema")

    if SUPPORTED_INGEST_CHANNELS != channels:
        status |= _fail("shared loader channel enum mismatch with schema")
    else:
        _ok("shared loader channels match schema")

    return status


def _validate_no_local_hardcoded_constants(path: Path) -> int:
    status = 0
    content = _read(path)

    hardcoded_version = re.search(r"^\s*INGEST_CONTRACT_VERSION\s*=", content, flags=re.MULTILINE)
    hardcoded_channels = re.search(r"^\s*SUPPORTED_INGEST_CHANNELS\s*=", content, flags=re.MULTILINE)

    if hardcoded_version:
        status |= _fail(f"hardcoded INGEST_CONTRACT_VERSION found in {path}")
    else:
        _ok(f"no hardcoded INGEST_CONTRACT_VERSION in {path}")

    if hardcoded_channels:
        status |= _fail(f"hardcoded SUPPORTED_INGEST_CHANNELS found in {path}")
    else:
        _ok(f"no hardcoded SUPPORTED_INGEST_CHANNELS in {path}")

    return status


def _validate_imports() -> int:
    status = 0

    backend_content = _read(BACKEND_ROUTER_PATH)
    bridge_content = _read(BRIDGE_PATH)

    if "from ..contracts.transaction_ingest_contract import" not in backend_content:
        status |= _fail("backend transactions router is not importing shared contract module")
    else:
        _ok("backend transactions router imports shared contract module")

    if "from backend.app.contracts.transaction_ingest_contract import" not in bridge_content:
        status |= _fail("ingestion bridge is not importing shared contract module")
    else:
        _ok("ingestion bridge imports shared contract module")

    if "normalize_bridge_ingest_payload" not in bridge_content:
        status |= _fail("ingestion bridge is not using shared bridge payload normalization")
    else:
        _ok("ingestion bridge uses shared bridge payload normalization")

    return status


def main() -> int:
    status, version, channels = _validate_schema()
    if status != 0:
        return status

    status |= _validate_loader_matches_schema(version, channels)
    status |= _validate_imports()
    status |= _validate_no_local_hardcoded_constants(BACKEND_ROUTER_PATH)
    status |= _validate_no_local_hardcoded_constants(BRIDGE_PATH)

    if status == 0:
        print("PASS: Ingest contract integrity checks completed")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
