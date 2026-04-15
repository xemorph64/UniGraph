from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


TRANSACTION_INGEST_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "transaction-ingest-contract.json"
)


def _contract_error(message: str) -> RuntimeError:
    return RuntimeError(
        f"Invalid transaction ingest contract at {TRANSACTION_INGEST_CONTRACT_PATH}: {message}"
    )


@lru_cache(maxsize=1)
def _load_contract_constraints() -> tuple[str, frozenset[str]]:
    try:
        raw = TRANSACTION_INGEST_CONTRACT_PATH.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except Exception as exc:
        raise _contract_error(f"unable to load contract schema ({exc})") from exc

    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise _contract_error("missing object 'properties'")

    contract_version = str(
        (properties.get("contract_version") or {}).get("const") or ""
    ).strip()
    if not contract_version:
        raise _contract_error("missing properties.contract_version.const")

    channels = (properties.get("channel") or {}).get("enum") or []
    normalized_channels = {
        str(value).strip().upper()
        for value in channels
        if str(value).strip()
    }
    if not normalized_channels:
        raise _contract_error("missing properties.channel.enum entries")

    return contract_version, frozenset(normalized_channels)


INGEST_CONTRACT_VERSION, SUPPORTED_INGEST_CHANNELS = _load_contract_constraints()
