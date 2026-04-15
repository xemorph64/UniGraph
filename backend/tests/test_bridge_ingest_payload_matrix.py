import math

from backend.app.contracts.transaction_ingest_contract import INGEST_CONTRACT_VERSION
from backend.app.contracts.transaction_ingest_payload import (
    normalize_bridge_ingest_payload,
)


def _base_bridge_payload() -> dict:
    return {
        "contract_version": INGEST_CONTRACT_VERSION,
        "txn_id": "TXN-ABC-001",
        "from_account": "ACC-1001",
        "to_account": "ACC-2002",
        "amount": 15000.0,
        "channel": "UPI",
        "device_account_count": 2,
        "velocity_1h": 3,
        "velocity_24h": 6,
    }


def test_bridge_payload_normalizes_accounts_and_channel():
    payload = _base_bridge_payload()
    payload["from_account"] = "  ACC-1001  "
    payload["to_account"] = "  ACC-2002  "
    payload["channel"] = " neft "

    normalized, error = normalize_bridge_ingest_payload(payload)

    assert error is None
    assert normalized is not None
    assert normalized["from_account"] == "ACC-1001"
    assert normalized["to_account"] == "ACC-2002"
    assert normalized["channel"] == "NEFT"


def test_bridge_payload_rejects_missing_required_field():
    payload = _base_bridge_payload()
    payload.pop("velocity_1h")

    normalized, error = normalize_bridge_ingest_payload(payload)

    assert normalized is None
    assert error == "missing field 'velocity_1h'"


def test_bridge_payload_rejects_wrong_contract_version():
    payload = _base_bridge_payload()
    payload["contract_version"] = "txn-ingest-v0"

    normalized, error = normalize_bridge_ingest_payload(payload)

    assert normalized is None
    assert error is not None
    assert "contract_version" in error


def test_bridge_payload_rejects_unsupported_channel():
    payload = _base_bridge_payload()
    payload["channel"] = "WIRE"

    normalized, error = normalize_bridge_ingest_payload(payload)

    assert normalized is None
    assert error is not None
    assert "channel" in error


def test_bridge_payload_rejects_non_finite_amount():
    payload = _base_bridge_payload()
    payload["amount"] = math.inf

    normalized, error = normalize_bridge_ingest_payload(payload)

    assert normalized is None
    assert error == "amount must be a finite number greater than zero"


def test_bridge_payload_rejects_empty_txn_id():
    payload = _base_bridge_payload()
    payload["txn_id"] = "   "

    normalized, error = normalize_bridge_ingest_payload(payload)

    assert normalized is None
    assert error is not None
    assert "txn_id" in error


def test_bridge_payload_rejects_invalid_device_account_count():
    payload = _base_bridge_payload()
    payload["device_account_count"] = 0

    normalized, error = normalize_bridge_ingest_payload(payload)

    assert normalized is None
    assert error is not None
    assert "device_account_count" in error
    assert ">=" in error or "greater than or equal to" in error


def test_bridge_payload_rejects_negative_velocity():
    payload = _base_bridge_payload()
    payload["velocity_24h"] = -2

    normalized, error = normalize_bridge_ingest_payload(payload)

    assert normalized is None
    assert error is not None
    assert "velocity_24h" in error
    assert ">=" in error or "greater than or equal to" in error
