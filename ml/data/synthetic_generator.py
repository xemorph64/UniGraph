import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class SyntheticFraudGenerator:
    OUTPUT_COLUMNS = [
        "txn_id",
        "from_account",
        "to_account",
        "amount",
        "channel",
        "timestamp",
        "currency",
        "geo_lat",
        "geo_lon",
        "is_fraud",
        "fraud_type",
        "customer_age",
        "account_age_days",
        "kyc_tier",
        "avg_monthly_balance",
        "transaction_count_30d",
        "avg_txn_amount",
        "std_txn_amount",
        "max_txn_amount",
        "min_txn_amount",
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "is_holiday",
        "geo_distance_from_home",
        "device_risk_flag",
        "device_account_count",
        "counterparty_risk_score",
        "is_international",
        "channel_switch_count",
    ]

    CHANNELS = ["UPI", "IMPS", "NEFT", "RTGS", "CASH", "SWIFT"]

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self._start_ts: pd.Timestamp | None = None
        self._date_range_days = 90

    def generate_dataset(
        self,
        num_normal: int = 50000,
        num_fraud: int = 250,
        num_accounts: int = 5000,
        date_range_days: int = 90,
    ) -> pd.DataFrame:
        """
        Generate synthetic transaction dataset with:
        - num_normal normal transactions
        - num_fraud fraud transactions (0.5% ratio)
        - Realistic account behaviors
        - Temporal patterns (business hours, weekends)
        Returns DataFrame with columns matching feature engineering spec.
        """
        self._date_range_days = date_range_days
        self._start_ts = pd.Timestamp.utcnow().floor("min") - pd.Timedelta(days=date_range_days)

        accounts = [f"ACC-{i:06d}" for i in range(1, num_accounts + 1)]

        normal_df = self._generate_normal_transactions(num_normal, accounts)

        split = np.full(5, num_fraud // 5, dtype=int)
        split[: num_fraud % 5] += 1

        fraud_parts = [
            self._generate_fraud_layering(int(split[0]), accounts),
            self._generate_fraud_structuring(int(split[1]), accounts),
            self._generate_fraud_round_trip(int(split[2]), accounts),
            self._generate_fraud_dormant(int(split[3]), accounts),
            self._generate_fraud_mule(int(split[4]), accounts),
        ]

        df = pd.concat([normal_df] + fraud_parts, ignore_index=True)
        df = df.sample(frac=1.0, random_state=self.rng).reset_index(drop=True)
        return df[self.OUTPUT_COLUMNS]

    def _generate_normal_transactions(self, num: int, accounts: list) -> pd.DataFrame:
        """Normal transactions: salary credits, bill payments, peer transfers."""
        rows: list[dict[str, Any]] = []
        for _ in range(num):
            src = self.rng.choice(accounts)
            dst = self.rng.choice(accounts)
            while dst == src:
                dst = self.rng.choice(accounts)

            behavior = self.rng.choice(["salary", "bill", "peer"], p=[0.15, 0.35, 0.50])
            if behavior == "salary":
                amount = float(np.clip(self.rng.normal(65000, 15000), 12000, 300000))
                channel = "NEFT"
            elif behavior == "bill":
                amount = float(np.clip(self.rng.normal(4500, 2500), 100, 50000))
                channel = self.rng.choice(["UPI", "IMPS", "CASH"], p=[0.7, 0.2, 0.1])
            else:
                amount = float(np.clip(self.rng.lognormal(mean=8.1, sigma=0.8), 100, 200000))
                channel = self.rng.choice(["UPI", "IMPS", "NEFT"], p=[0.6, 0.3, 0.1])

            ts = self._random_timestamp(business_hour_bias=True)
            rows.append(
                self._build_row(
                    txn_id=self._txn_id(),
                    from_account=src,
                    to_account=dst,
                    amount=amount,
                    channel=channel,
                    timestamp=ts,
                    is_fraud=0,
                    fraud_type="normal",
                    device_risk_flag=0,
                    device_account_count=int(self.rng.randint(1, 3)),
                    counterparty_risk_score=float(self.rng.uniform(0.0, 0.2)),
                    is_international=0,
                    channel_switch_count=int(self.rng.randint(0, 3)),
                )
            )
        return pd.DataFrame(rows, columns=self.OUTPUT_COLUMNS)

    def _generate_fraud_layering(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: rapid layering — multiple hops in short time."""
        rows: list[dict[str, Any]] = []
        for _ in range(num):
            base_idx = self.rng.randint(0, max(1, len(accounts) - 7))
            chain = accounts[base_idx : base_idx + 7]
            if len(chain) < 7:
                chain = list(self.rng.choice(accounts, size=7, replace=False))

            hop = int(self.rng.randint(0, 6))
            ts0 = self._random_timestamp(business_hour_bias=False)
            ts = ts0 + pd.Timedelta(minutes=hop * 5)
            src, dst = chain[hop], chain[hop + 1]
            amount = float(self.rng.uniform(50000, 90000) - hop * self.rng.uniform(500, 2000))

            rows.append(
                self._build_row(
                    txn_id=self._txn_id(),
                    from_account=src,
                    to_account=dst,
                    amount=max(amount, 50000.0),
                    channel=self.rng.choice(["IMPS", "RTGS", "NEFT"], p=[0.45, 0.35, 0.20]),
                    timestamp=ts,
                    is_fraud=1,
                    fraud_type="rapid_layering",
                    device_risk_flag=1,
                    device_account_count=int(self.rng.randint(3, 7)),
                    counterparty_risk_score=float(self.rng.uniform(0.7, 0.95)),
                    is_international=0,
                    channel_switch_count=int(self.rng.randint(2, 7)),
                    account_age_days=int(self.rng.randint(20, 400)),
                )
            )
        return pd.DataFrame(rows, columns=self.OUTPUT_COLUMNS)

    def _generate_fraud_structuring(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: structuring — amounts just below CTR threshold."""
        rows: list[dict[str, Any]] = []
        for _ in range(num):
            src = self.rng.choice(accounts)
            dst = self.rng.choice(accounts)
            while dst == src:
                dst = self.rng.choice(accounts)

            ts = self._random_timestamp(business_hour_bias=False)
            amount = float(self.rng.uniform(900000, 999500))
            rows.append(
                self._build_row(
                    txn_id=self._txn_id(),
                    from_account=src,
                    to_account=dst,
                    amount=amount,
                    channel=self.rng.choice(["NEFT", "RTGS", "IMPS"], p=[0.45, 0.45, 0.10]),
                    timestamp=ts,
                    is_fraud=1,
                    fraud_type="structuring",
                    device_risk_flag=1,
                    device_account_count=int(self.rng.randint(2, 5)),
                    counterparty_risk_score=float(self.rng.uniform(0.6, 0.9)),
                    is_international=0,
                    channel_switch_count=int(self.rng.randint(2, 6)),
                )
            )
        return pd.DataFrame(rows, columns=self.OUTPUT_COLUMNS)

    def _generate_fraud_round_trip(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: round-tripping — funds return to origin."""
        rows: list[dict[str, Any]] = []
        for _ in range(num):
            ring = list(self.rng.choice(accounts, size=3, replace=False))
            leg = int(self.rng.randint(0, 3))
            src = ring[leg]
            dst = ring[(leg + 1) % 3]
            ts = self._random_timestamp(business_hour_bias=False) + pd.Timedelta(minutes=leg * 20)
            amount = float(self.rng.uniform(60000, 250000))

            rows.append(
                self._build_row(
                    txn_id=self._txn_id(),
                    from_account=src,
                    to_account=dst,
                    amount=amount,
                    channel=self.rng.choice(["IMPS", "NEFT", "RTGS"], p=[0.5, 0.3, 0.2]),
                    timestamp=ts,
                    is_fraud=1,
                    fraud_type="round_tripping",
                    device_risk_flag=1,
                    device_account_count=int(self.rng.randint(2, 6)),
                    counterparty_risk_score=float(self.rng.uniform(0.65, 0.95)),
                    is_international=int(self.rng.choice([0, 1], p=[0.85, 0.15])),
                    channel_switch_count=int(self.rng.randint(2, 8)),
                )
            )
        return pd.DataFrame(rows, columns=self.OUTPUT_COLUMNS)

    def _generate_fraud_dormant(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: dormant account awakening."""
        rows: list[dict[str, Any]] = []
        for _ in range(num):
            src = self.rng.choice(accounts)
            dst = self.rng.choice(accounts)
            while dst == src:
                dst = self.rng.choice(accounts)

            ts = self._random_timestamp(business_hour_bias=False)
            rows.append(
                self._build_row(
                    txn_id=self._txn_id(),
                    from_account=src,
                    to_account=dst,
                    amount=float(self.rng.uniform(120000, 950000)),
                    channel=self.rng.choice(["IMPS", "RTGS", "SWIFT"], p=[0.4, 0.4, 0.2]),
                    timestamp=ts,
                    is_fraud=1,
                    fraud_type="dormant_awakening",
                    account_age_days=int(self.rng.randint(365, 3000)),
                    transaction_count_30d=int(self.rng.randint(0, 2)),
                    avg_txn_amount=float(self.rng.uniform(500, 5000)),
                    std_txn_amount=float(self.rng.uniform(100, 1000)),
                    max_txn_amount=float(self.rng.uniform(2000, 10000)),
                    min_txn_amount=float(self.rng.uniform(100, 500)),
                    device_risk_flag=1,
                    device_account_count=int(self.rng.randint(2, 5)),
                    counterparty_risk_score=float(self.rng.uniform(0.6, 0.95)),
                    is_international=int(self.rng.choice([0, 1], p=[0.7, 0.3])),
                    channel_switch_count=int(self.rng.randint(1, 5)),
                )
            )
        return pd.DataFrame(rows, columns=self.OUTPUT_COLUMNS)

    def _generate_fraud_mule(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: mule network — shared device/IP."""
        rows: list[dict[str, Any]] = []
        mule_accounts = list(self.rng.choice(accounts, size=min(5, len(accounts)), replace=False))
        for _ in range(num):
            src = self.rng.choice(mule_accounts)
            dst = self.rng.choice(accounts)
            while dst == src:
                dst = self.rng.choice(accounts)

            ts = self._random_timestamp(business_hour_bias=False)
            rows.append(
                self._build_row(
                    txn_id=self._txn_id(),
                    from_account=src,
                    to_account=dst,
                    amount=float(self.rng.uniform(20000, 450000)),
                    channel=self.rng.choice(["UPI", "IMPS", "NEFT"], p=[0.25, 0.55, 0.20]),
                    timestamp=ts,
                    is_fraud=1,
                    fraud_type="mule_network",
                    device_risk_flag=1,
                    device_account_count=int(self.rng.randint(4, 10)),
                    counterparty_risk_score=float(self.rng.uniform(0.7, 0.98)),
                    is_international=int(self.rng.choice([0, 1], p=[0.8, 0.2])),
                    channel_switch_count=int(self.rng.randint(3, 9)),
                )
            )
        return pd.DataFrame(rows, columns=self.OUTPUT_COLUMNS)

    def apply_smote(self, df: pd.DataFrame, target_col: str = "is_fraud") -> pd.DataFrame:
        """Apply SMOTE to balance classes for tabular features."""
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found in DataFrame")

        from imblearn.over_sampling import SMOTE

        y = df[target_col]
        X = pd.get_dummies(df.drop(columns=[target_col]), drop_first=False)
        smote = SMOTE(random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X, y)

        resampled_df = pd.DataFrame(X_resampled, columns=X.columns)
        resampled_df[target_col] = y_resampled
        return resampled_df

    def save_dataset(self, df: pd.DataFrame, path: str):
        """Save to CSV + metadata JSON."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

        metadata = {
            "rows": int(df.shape[0]),
            "columns": list(df.columns),
            "class_distribution": df["is_fraud"].value_counts().to_dict() if "is_fraud" in df.columns else {},
            "fraud_type_distribution": df["fraud_type"].value_counts().to_dict() if "fraud_type" in df.columns else {},
        }

        metadata_path = output_path.with_suffix(".metadata.json")
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def _build_row(
        self,
        txn_id: str,
        from_account: str,
        to_account: str,
        amount: float,
        channel: str,
        timestamp: pd.Timestamp,
        is_fraud: int,
        fraud_type: str,
        device_risk_flag: int,
        device_account_count: int,
        counterparty_risk_score: float,
        is_international: int,
        channel_switch_count: int,
        account_age_days: int | None = None,
        transaction_count_30d: int | None = None,
        avg_txn_amount: float | None = None,
        std_txn_amount: float | None = None,
        max_txn_amount: float | None = None,
        min_txn_amount: float | None = None,
    ) -> dict[str, Any]:
        customer_age = int(self.rng.randint(21, 75))
        acct_age = int(account_age_days if account_age_days is not None else self.rng.randint(30, 3650))
        avg_balance = float(self.rng.uniform(10000, 1500000))
        txn_count_30d = int(transaction_count_30d if transaction_count_30d is not None else self.rng.randint(2, 90))

        avg_amount = float(avg_txn_amount if avg_txn_amount is not None else max(200.0, amount * self.rng.uniform(0.2, 0.8)))
        std_amount = float(std_txn_amount if std_txn_amount is not None else max(50.0, avg_amount * self.rng.uniform(0.1, 0.9)))
        max_amount = float(max_txn_amount if max_txn_amount is not None else max(amount, avg_amount + 3 * std_amount))
        min_amount = float(min_txn_amount if min_txn_amount is not None else max(10.0, avg_amount - 2 * std_amount))

        holiday_chance = 0.03
        dow = int(timestamp.dayofweek)
        is_weekend = int(dow >= 5)

        return {
            "txn_id": txn_id,
            "from_account": from_account,
            "to_account": to_account,
            "amount": round(float(amount), 2),
            "channel": channel,
            "timestamp": timestamp.isoformat(),
            "currency": "INR",
            "geo_lat": round(float(self.rng.uniform(8.0, 37.0)), 6),
            "geo_lon": round(float(self.rng.uniform(68.0, 97.0)), 6),
            "is_fraud": int(is_fraud),
            "fraud_type": fraud_type,
            "customer_age": customer_age,
            "account_age_days": acct_age,
            "kyc_tier": int(self.rng.choice([1, 2, 3], p=[0.7, 0.25, 0.05])),
            "avg_monthly_balance": round(avg_balance, 2),
            "transaction_count_30d": txn_count_30d,
            "avg_txn_amount": round(avg_amount, 2),
            "std_txn_amount": round(std_amount, 2),
            "max_txn_amount": round(max_amount, 2),
            "min_txn_amount": round(min_amount, 2),
            "hour_of_day": int(timestamp.hour),
            "day_of_week": dow,
            "is_weekend": is_weekend,
            "is_holiday": int(self.rng.rand() < holiday_chance),
            "geo_distance_from_home": round(float(np.clip(self.rng.exponential(scale=12.0), 0.1, 3000.0)), 3),
            "device_risk_flag": int(device_risk_flag),
            "device_account_count": int(device_account_count),
            "counterparty_risk_score": round(float(counterparty_risk_score), 4),
            "is_international": int(is_international),
            "channel_switch_count": int(channel_switch_count),
        }

    def _random_timestamp(self, business_hour_bias: bool) -> pd.Timestamp:
        if self._start_ts is None:
            self._start_ts = pd.Timestamp.utcnow().floor("min") - pd.Timedelta(days=self._date_range_days)

        day_offset = int(self.rng.randint(0, self._date_range_days))
        base_day = self._start_ts + pd.Timedelta(days=day_offset)

        if business_hour_bias:
            hour = int(self.rng.choice(np.arange(24), p=self._hour_distribution_business()))
        else:
            hour = int(self.rng.randint(0, 24))

        minute = int(self.rng.randint(0, 60))
        second = int(self.rng.randint(0, 60))
        return base_day + pd.Timedelta(hours=hour, minutes=minute, seconds=second)

    def _hour_distribution_business(self) -> np.ndarray:
        weights = np.array([
            0.01,
            0.005,
            0.005,
            0.005,
            0.005,
            0.01,
            0.015,
            0.03,
            0.06,
            0.08,
            0.09,
            0.09,
            0.09,
            0.08,
            0.08,
            0.07,
            0.06,
            0.05,
            0.04,
            0.03,
            0.02,
            0.015,
            0.01,
            0.01,
        ])
        return weights / weights.sum()

    def _txn_id(self) -> str:
        return f"TXN-{self.rng.randint(2026000000, 2026999999)}"
