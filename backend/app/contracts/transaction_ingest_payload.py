from __future__ import annotations

import math
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .transaction_ingest_contract import (
    INGEST_CONTRACT_VERSION,
    SUPPORTED_INGEST_CHANNELS,
)


class TransactionIngestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = INGEST_CONTRACT_VERSION
    txn_id: Optional[str] = None
    from_account: str = Field(..., min_length=1)
    to_account: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    channel: str = "IMPS"
    customer_id: Optional[str] = None
    description: Optional[str] = "Transfer"
    device_id: Optional[str] = None
    is_dormant: bool = False
    device_account_count: int = Field(default=1, ge=1)
    velocity_1h: int = Field(default=0, ge=0)
    velocity_24h: int = Field(default=0, ge=0)
    account_age_days: Optional[int] = None
    kyc_tier: Optional[int] = None
    transaction_count_30d: Optional[int] = None
    avg_txn_amount_30d: Optional[float] = None
    device_count_30d: Optional[int] = None
    ip_count_30d: Optional[int] = None
    customer_age: Optional[float] = None
    avg_monthly_balance: Optional[float] = None
    avg_txn_amount: Optional[float] = None
    std_txn_amount: Optional[float] = None
    max_txn_amount: Optional[float] = None
    min_txn_amount: Optional[float] = None
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    is_weekend: Optional[bool] = None
    is_holiday: Optional[bool] = None
    geo_distance_from_home: Optional[float] = None
    device_risk_flag: Optional[bool] = None
    counterparty_risk_score: Optional[float] = None
    is_international: Optional[bool] = None
    channel_switch_count: Optional[int] = None
    amount_zscore: Optional[float] = None

    @field_validator("contract_version")
    @classmethod
    def validate_contract_version(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if normalized != INGEST_CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported contract_version '{normalized}'. Expected '{INGEST_CONTRACT_VERSION}'."
            )
        return normalized

    @field_validator("from_account", "to_account")
    @classmethod
    def validate_account_fields(cls, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Account id cannot be empty")
        return normalized

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if normalized not in SUPPORTED_INGEST_CHANNELS:
            raise ValueError(
                f"Unsupported channel '{normalized}'. Allowed channels: {sorted(SUPPORTED_INGEST_CHANNELS)}"
            )
        return normalized

    @field_validator("txn_id")
    @classmethod
    def normalize_txn_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("txn_id cannot be empty when provided")
        return normalized


def _coerce_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _first_validation_message(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return str(exc)

    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", []))
    message = str(first.get("msg") or "invalid payload")
    return f"{location}: {message}" if location else message


def normalize_ingest_payload(
    payload: dict[str, Any], *, require_txn_id: bool = False
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        model = TransactionIngestPayload.model_validate(payload)
    except ValidationError as exc:
        return None, _first_validation_message(exc)

    normalized = model.model_dump()

    if require_txn_id and not normalized.get("txn_id"):
        return None, "txn_id is required"

    amount = float(normalized.get("amount", 0.0) or 0.0)
    if not math.isfinite(amount) or amount <= 0.0:
        return None, "amount must be a finite number greater than zero"
    normalized["amount"] = amount

    return normalized, None


def normalize_bridge_ingest_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    required_fields = (
        "contract_version",
        "txn_id",
        "from_account",
        "to_account",
        "amount",
        "channel",
        "device_account_count",
        "velocity_1h",
        "velocity_24h",
    )
    for field in required_fields:
        if field not in payload:
            return None, f"missing field '{field}'"

    normalized, error = normalize_ingest_payload(payload, require_txn_id=True)
    if error:
        return None, error

    device_account_count = _coerce_int(payload.get("device_account_count"), 0)
    velocity_1h = _coerce_int(payload.get("velocity_1h"), -1)
    velocity_24h = _coerce_int(payload.get("velocity_24h"), -1)

    if device_account_count < 1:
        return None, "device_account_count must be >= 1"
    if velocity_1h < 0 or velocity_24h < 0:
        return None, "velocity_1h and velocity_24h must be >= 0"

    normalized["device_account_count"] = device_account_count
    normalized["velocity_1h"] = velocity_1h
    normalized["velocity_24h"] = velocity_24h
    return normalized, None
