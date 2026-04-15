import json

import pytest
from pydantic import ValidationError

from backend.app.contracts.transaction_ingest_contract import (
    TRANSACTION_INGEST_CONTRACT_PATH,
)
from backend.app.routers.transactions import (
    INGEST_CONTRACT_VERSION,
    SUPPORTED_INGEST_CHANNELS,
    TransactionIngest,
)


def _base_payload() -> dict:
    return {
        "from_account": "ACC-1001",
        "to_account": "ACC-2002",
        "amount": 25000.0,
        "channel": "UPI",
    }


def test_ingest_contract_accepts_default_contract_version():
    txn = TransactionIngest(**_base_payload())
    assert txn.contract_version == INGEST_CONTRACT_VERSION


def test_ingest_contract_normalizes_channel_case():
    payload = _base_payload()
    payload["channel"] = "neft"
    txn = TransactionIngest(**payload)
    assert txn.channel == "NEFT"


def test_ingest_contract_rejects_unsupported_channel():
    payload = _base_payload()
    payload["channel"] = "WIRE"

    with pytest.raises(ValidationError):
        TransactionIngest(**payload)


def test_ingest_contract_rejects_non_positive_amount():
    payload = _base_payload()
    payload["amount"] = 0

    with pytest.raises(ValidationError):
        TransactionIngest(**payload)


def test_ingest_contract_rejects_wrong_contract_version():
    payload = _base_payload()
    payload["contract_version"] = "txn-ingest-v0"

    with pytest.raises(ValidationError):
        TransactionIngest(**payload)


def test_ingest_contract_rejects_unknown_fields():
    payload = _base_payload()
    payload["unexpected_field"] = "not-allowed"

    with pytest.raises(ValidationError):
        TransactionIngest(**payload)


def test_ingest_contract_schema_artifact_is_source_of_truth():
    schema = json.loads(TRANSACTION_INGEST_CONTRACT_PATH.read_text(encoding="utf-8"))

    schema_version = schema["properties"]["contract_version"]["const"]
    schema_channels = {
        str(channel).strip().upper()
        for channel in schema["properties"]["channel"]["enum"]
    }

    assert INGEST_CONTRACT_VERSION == schema_version
    assert SUPPORTED_INGEST_CHANNELS == schema_channels
