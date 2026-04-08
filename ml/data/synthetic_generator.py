import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from imblearn.over_sampling import SMOTE
import json
import os


class SyntheticFraudGenerator:
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def generate_dataset(
        self,
        num_normal: int = 50000,
        num_fraud: int = 250,
        num_accounts: int = 5000,
        date_range_days: int = 90,
    ) -> pd.DataFrame:
        accounts = [f"ACC-{i:05d}" for i in range(1, num_accounts + 1)]
        normal_df = self._generate_normal_transactions(
            num_normal, accounts, date_range_days
        )
        fraud_dfs = []
        num_per_type = num_fraud // 5
        remainder = num_fraud - (num_per_type * 5)
        fraud_dfs.append(
            self._generate_fraud_layering(num_per_type, accounts, date_range_days)
        )
        fraud_dfs.append(
            self._generate_fraud_structuring(num_per_type, accounts, date_range_days)
        )
        fraud_dfs.append(
            self._generate_fraud_round_trip(num_per_type, accounts, date_range_days)
        )
        fraud_dfs.append(
            self._generate_fraud_dormant(num_per_type, accounts, date_range_days)
        )
        fraud_dfs.append(
            self._generate_fraud_mule(
                num_per_type + remainder, accounts, date_range_days
            )
        )
        fraud_df = pd.concat(fraud_dfs, ignore_index=True)
        df = pd.concat([normal_df, fraud_df], ignore_index=True)
        df = df.sample(frac=1, random_state=self.rng).reset_index(drop=True)
        return df

    def _generate_normal_transactions(
        self, num: int, accounts: list, date_range_days: int
    ) -> pd.DataFrame:
        records = []
        base_date = datetime(2026, 1, 1)
        for i in range(num):
            txn_id = f"TXN-N-{i:06d}"
            from_acc = self.rng.choice(accounts)
            to_acc = self.rng.choice([a for a in accounts if a != from_acc])
            txn_type = self.rng.choice(
                ["salary", "bill", "peer", "merchant", "atm"],
                p=[0.15, 0.25, 0.30, 0.20, 0.10],
            )
            if txn_type == "salary":
                amount = self.rng.normal(55000, 15000)
                channel = "NEFT"
            elif txn_type == "bill":
                amount = self.rng.lognormal(7, 0.8)
                channel = self.rng.choice(["UPI", "IMPS"])
            elif txn_type == "peer":
                amount = self.rng.lognormal(6, 1.2)
                channel = self.rng.choice(["UPI", "IMPS", "NEFT"])
            elif txn_type == "merchant":
                amount = self.rng.lognormal(6, 1.5)
                channel = self.rng.choice(["UPI", "POS"])
            else:
                amount = self.rng.lognormal(7, 0.6)
                channel = "ATM"
            amount = max(10.0, round(amount, 2))
            day_offset = self.rng.randint(0, date_range_days)
            hour = self.rng.choice(range(24), p=self._business_hour_probs())
            minute = self.rng.randint(0, 60)
            second = self.rng.randint(0, 60)
            timestamp = base_date + timedelta(
                days=int(day_offset),
                hours=int(hour),
                minutes=int(minute),
                seconds=int(second),
            )
            customer_age = self.rng.randint(18, 70)
            account_age_days = self.rng.randint(30, 3650)
            kyc_tier = int(self.rng.choice([1, 2, 3], p=[0.15, 0.55, 0.30]))
            avg_monthly_balance = self.rng.lognormal(10, 1.0)
            txn_count_30d = self.rng.poisson(15)
            avg_txn_amount = self.rng.lognormal(7, 0.5)
            std_txn_amount = self.rng.uniform(500, 15000)
            max_txn_amount = avg_txn_amount + std_txn_amount * self.rng.uniform(1, 3)
            min_txn_amount = max(
                10, avg_txn_amount - std_txn_amount * self.rng.uniform(0.5, 2)
            )
            hour_of_day = timestamp.hour
            day_of_week = timestamp.weekday()
            is_weekend = int(day_of_week >= 5)
            is_holiday = int(self.rng.random() < 0.05)
            geo_distance = self.rng.exponential(5)
            device_risk_flag = int(self.rng.random() < 0.02)
            device_account_count = int(self.rng.poisson(1.2) + 1)
            counterparty_risk = self.rng.uniform(0.0, 0.3)
            is_international = int(self.rng.random() < 0.03)
            channel_switch_count = int(self.rng.poisson(1))
            records.append(
                {
                    "txn_id": txn_id,
                    "from_account": from_acc,
                    "to_account": to_acc,
                    "amount": amount,
                    "channel": channel,
                    "timestamp": timestamp.isoformat(),
                    "is_fraud": 0,
                    "fraud_type": "none",
                    "customer_age": customer_age,
                    "account_age_days": account_age_days,
                    "kyc_tier": kyc_tier,
                    "avg_monthly_balance": round(avg_monthly_balance, 2),
                    "transaction_count_30d": txn_count_30d,
                    "avg_txn_amount": round(avg_txn_amount, 2),
                    "std_txn_amount": round(std_txn_amount, 2),
                    "max_txn_amount": round(max_txn_amount, 2),
                    "min_txn_amount": round(min_txn_amount, 2),
                    "hour_of_day": hour_of_day,
                    "day_of_week": day_of_week,
                    "is_weekend": is_weekend,
                    "is_holiday": is_holiday,
                    "geo_distance_from_home": round(geo_distance, 2),
                    "device_risk_flag": device_risk_flag,
                    "device_account_count": device_account_count,
                    "counterparty_risk_score": round(counterparty_risk, 4),
                    "is_international": is_international,
                    "channel_switch_count": channel_switch_count,
                    "currency": "INR",
                    "ip_address": f"sha256:{self.rng.bytes(8).hex()}",
                    "device_fingerprint": f"dev_fp_{self.rng.bytes(4).hex()}",
                }
            )
        return pd.DataFrame(records)

    def _generate_fraud_layering(
        self, num: int, accounts: list, date_range_days: int
    ) -> pd.DataFrame:
        records = []
        base_date = datetime(2026, 1, 1)
        num_chains = max(1, num // 6)
        for chain_idx in range(num_chains):
            chain_length = min(6, num - len(records))
            if chain_length < 1:
                break
            chain_accounts = list(
                self.rng.choice(
                    accounts, size=min(chain_length + 1, len(accounts)), replace=False
                )
            )
            day_offset = self.rng.randint(0, date_range_days)
            start_time = base_date + timedelta(
                days=int(day_offset), hours=self.rng.randint(9, 18)
            )
            for hop in range(chain_length):
                txn_id = f"TXN-F-LAYER-{len(records):06d}"
                from_acc = chain_accounts[hop]
                to_acc = chain_accounts[(hop + 1) % len(chain_accounts)]
                amount = round(self.rng.uniform(50000, 500000), 2)
                timestamp = start_time + timedelta(minutes=hop * self.rng.randint(2, 5))
                records.append(
                    self._make_fraud_record(
                        txn_id, from_acc, to_acc, amount, timestamp, "layering"
                    )
                )
        while len(records) < num:
            idx = len(records)
            txn_id = f"TXN-F-LAYER-{idx:06d}"
            from_acc = self.rng.choice(accounts)
            to_acc = self.rng.choice([a for a in accounts if a != from_acc])
            day_offset = self.rng.randint(0, date_range_days)
            timestamp = base_date + timedelta(
                days=int(day_offset),
                hours=self.rng.randint(0, 23),
                minutes=self.rng.randint(0, 59),
            )
            amount = round(self.rng.uniform(50000, 500000), 2)
            records.append(
                self._make_fraud_record(
                    txn_id, from_acc, to_acc, amount, timestamp, "layering"
                )
            )
        return pd.DataFrame(records[:num])

    def _generate_fraud_structuring(
        self, num: int, accounts: list, date_range_days: int
    ) -> pd.DataFrame:
        records = []
        base_date = datetime(2026, 1, 1)
        for i in range(num):
            txn_id = f"TXN-F-STRUCT-{i:06d}"
            from_acc = self.rng.choice(accounts)
            to_acc = self.rng.choice([a for a in accounts if a != from_acc])
            amount = round(self.rng.uniform(500000, 999999), 2)
            day_offset = self.rng.randint(0, date_range_days)
            timestamp = base_date + timedelta(
                days=int(day_offset),
                hours=self.rng.randint(8, 20),
                minutes=self.rng.randint(0, 59),
            )
            records.append(
                self._make_fraud_record(
                    txn_id, from_acc, to_acc, amount, timestamp, "structuring"
                )
            )
        return pd.DataFrame(records)

    def _generate_fraud_round_trip(
        self, num: int, accounts: list, date_range_days: int
    ) -> pd.DataFrame:
        records = []
        base_date = datetime(2026, 1, 1)
        num_cycles = max(1, num // 4)
        for cycle_idx in range(num_cycles):
            cycle_length = min(4, num - len(records))
            if cycle_length < 2:
                break
            cycle_accounts = list(
                self.rng.choice(
                    accounts, size=min(cycle_length + 1, len(accounts)), replace=False
                )
            )
            day_offset = self.rng.randint(0, date_range_days)
            start_time = base_date + timedelta(
                days=int(day_offset), hours=self.rng.randint(9, 17)
            )
            for hop in range(cycle_length):
                txn_id = f"TXN-F-ROUND-{len(records):06d}"
                from_acc = cycle_accounts[hop]
                to_acc = cycle_accounts[(hop + 1) % len(cycle_accounts)]
                amount = round(self.rng.uniform(100000, 1000000) * (1 - hop * 0.02), 2)
                timestamp = start_time + timedelta(hours=hop * self.rng.randint(1, 6))
                records.append(
                    self._make_fraud_record(
                        txn_id, from_acc, to_acc, amount, timestamp, "round_trip"
                    )
                )
        while len(records) < num:
            idx = len(records)
            txn_id = f"TXN-F-ROUND-{idx:06d}"
            from_acc = self.rng.choice(accounts)
            to_acc = self.rng.choice([a for a in accounts if a != from_acc])
            day_offset = self.rng.randint(0, date_range_days)
            timestamp = base_date + timedelta(
                days=int(day_offset),
                hours=self.rng.randint(0, 23),
                minutes=self.rng.randint(0, 59),
            )
            amount = round(self.rng.uniform(100000, 1000000), 2)
            records.append(
                self._make_fraud_record(
                    txn_id, from_acc, to_acc, amount, timestamp, "round_trip"
                )
            )
        return pd.DataFrame(records[:num])

    def _generate_fraud_dormant(
        self, num: int, accounts: list, date_range_days: int
    ) -> pd.DataFrame:
        records = []
        base_date = datetime(2026, 1, 1)
        for i in range(num):
            txn_id = f"TXN-F-DORM-{i:06d}"
            from_acc = self.rng.choice(accounts)
            to_acc = self.rng.choice([a for a in accounts if a != from_acc])
            amount = round(self.rng.uniform(100000, 2000000), 2)
            day_offset = self.rng.randint(0, date_range_days)
            timestamp = base_date + timedelta(
                days=int(day_offset),
                hours=self.rng.randint(0, 23),
                minutes=self.rng.randint(0, 59),
            )
            records.append(
                self._make_fraud_record(
                    txn_id, from_acc, to_acc, amount, timestamp, "dormant"
                )
            )
        return pd.DataFrame(records)

    def _generate_fraud_mule(
        self, num: int, accounts: list, date_range_days: int
    ) -> pd.DataFrame:
        records = []
        base_date = datetime(2026, 1, 1)
        num_clusters = max(1, num // 5)
        for cluster_idx in range(num_clusters):
            cluster_size = min(5, num - len(records))
            if cluster_size < 1:
                break
            cluster_accounts = list(
                self.rng.choice(
                    accounts, size=min(cluster_size + 2, len(accounts)), replace=False
                )
            )
            shared_device_count = self.rng.randint(4, 10)
            day_offset = self.rng.randint(0, date_range_days)
            for j in range(cluster_size):
                txn_id = f"TXN-F-MULE-{len(records):06d}"
                from_acc = cluster_accounts[j]
                to_acc = self.rng.choice([a for a in cluster_accounts if a != from_acc])
                amount = round(self.rng.uniform(20000, 500000), 2)
                timestamp = base_date + timedelta(
                    days=int(day_offset),
                    hours=self.rng.randint(0, 23),
                    minutes=self.rng.randint(0, 59),
                )
                records.append(
                    self._make_fraud_record(
                        txn_id,
                        from_acc,
                        to_acc,
                        amount,
                        timestamp,
                        "mule",
                        device_account_count=shared_device_count,
                    )
                )
        while len(records) < num:
            idx = len(records)
            txn_id = f"TXN-F-MULE-{idx:06d}"
            from_acc = self.rng.choice(accounts)
            to_acc = self.rng.choice([a for a in accounts if a != from_acc])
            day_offset = self.rng.randint(0, date_range_days)
            timestamp = base_date + timedelta(
                days=int(day_offset),
                hours=self.rng.randint(0, 23),
                minutes=self.rng.randint(0, 59),
            )
            amount = round(self.rng.uniform(20000, 500000), 2)
            records.append(
                self._make_fraud_record(
                    txn_id, from_acc, to_acc, amount, timestamp, "mule"
                )
            )
        return pd.DataFrame(records[:num])

    def _make_fraud_record(
        self,
        txn_id,
        from_acc,
        to_acc,
        amount,
        timestamp,
        fraud_type,
        device_account_count=None,
    ):
        if fraud_type == "layering":
            return {
                "txn_id": txn_id,
                "from_account": from_acc,
                "to_account": to_acc,
                "amount": amount,
                "channel": self.rng.choice(["IMPS", "NEFT", "RTGS"]),
                "timestamp": timestamp.isoformat(),
                "is_fraud": 1,
                "fraud_type": fraud_type,
                "customer_age": self.rng.randint(18, 50),
                "account_age_days": self.rng.randint(10, 365),
                "kyc_tier": int(self.rng.choice([1, 2], p=[0.6, 0.4])),
                "avg_monthly_balance": round(self.rng.lognormal(9, 0.5), 2),
                "transaction_count_30d": self.rng.poisson(30),
                "avg_txn_amount": round(self.rng.lognormal(10, 0.5), 2),
                "std_txn_amount": round(self.rng.uniform(10000, 50000), 2),
                "max_txn_amount": round(self.rng.uniform(200000, 800000), 2),
                "min_txn_amount": round(self.rng.uniform(5000, 50000), 2),
                "hour_of_day": timestamp.hour,
                "day_of_week": timestamp.weekday(),
                "is_weekend": int(timestamp.weekday() >= 5),
                "is_holiday": 0,
                "geo_distance_from_home": round(self.rng.exponential(50), 2),
                "device_risk_flag": int(self.rng.random() < 0.3),
                "device_account_count": device_account_count
                if device_account_count
                else int(self.rng.poisson(3) + 1),
                "counterparty_risk_score": round(self.rng.uniform(0.5, 0.95), 4),
                "is_international": int(self.rng.random() < 0.1),
                "channel_switch_count": int(self.rng.poisson(3)),
                "currency": "INR",
                "ip_address": f"sha256:{self.rng.bytes(8).hex()}",
                "device_fingerprint": f"dev_fp_{self.rng.bytes(4).hex()}",
            }
        elif fraud_type == "structuring":
            return {
                "txn_id": txn_id,
                "from_account": from_acc,
                "to_account": to_acc,
                "amount": amount,
                "channel": self.rng.choice(["IMPS", "NEFT", "RTGS"]),
                "timestamp": timestamp.isoformat(),
                "is_fraud": 1,
                "fraud_type": fraud_type,
                "customer_age": self.rng.randint(22, 60),
                "account_age_days": self.rng.randint(60, 730),
                "kyc_tier": int(self.rng.choice([1, 2, 3], p=[0.3, 0.5, 0.2])),
                "avg_monthly_balance": round(self.rng.lognormal(10, 0.8), 2),
                "transaction_count_30d": self.rng.poisson(20),
                "avg_txn_amount": round(self.rng.lognormal(10, 0.3), 2),
                "std_txn_amount": round(self.rng.uniform(50000, 200000), 2),
                "max_txn_amount": round(self.rng.uniform(500000, 1500000), 2),
                "min_txn_amount": round(self.rng.uniform(100000, 500000), 2),
                "hour_of_day": timestamp.hour,
                "day_of_week": timestamp.weekday(),
                "is_weekend": int(timestamp.weekday() >= 5),
                "is_holiday": 0,
                "geo_distance_from_home": round(self.rng.exponential(20), 2),
                "device_risk_flag": int(self.rng.random() < 0.15),
                "device_account_count": device_account_count
                if device_account_count
                else int(self.rng.poisson(2) + 1),
                "counterparty_risk_score": round(self.rng.uniform(0.3, 0.8), 4),
                "is_international": int(self.rng.random() < 0.05),
                "channel_switch_count": int(self.rng.poisson(2)),
                "currency": "INR",
                "ip_address": f"sha256:{self.rng.bytes(8).hex()}",
                "device_fingerprint": f"dev_fp_{self.rng.bytes(4).hex()}",
            }
        elif fraud_type == "round_trip":
            return {
                "txn_id": txn_id,
                "from_account": from_acc,
                "to_account": to_acc,
                "amount": amount,
                "channel": self.rng.choice(["IMPS", "NEFT", "RTGS"]),
                "timestamp": timestamp.isoformat(),
                "is_fraud": 1,
                "fraud_type": fraud_type,
                "customer_age": self.rng.randint(20, 55),
                "account_age_days": self.rng.randint(30, 500),
                "kyc_tier": int(self.rng.choice([1, 2], p=[0.5, 0.5])),
                "avg_monthly_balance": round(self.rng.lognormal(10, 0.6), 2),
                "transaction_count_30d": self.rng.poisson(25),
                "avg_txn_amount": round(self.rng.lognormal(10, 0.4), 2),
                "std_txn_amount": round(self.rng.uniform(20000, 80000), 2),
                "max_txn_amount": round(self.rng.uniform(300000, 1200000), 2),
                "min_txn_amount": round(self.rng.uniform(20000, 100000), 2),
                "hour_of_day": timestamp.hour,
                "day_of_week": timestamp.weekday(),
                "is_weekend": int(timestamp.weekday() >= 5),
                "is_holiday": 0,
                "geo_distance_from_home": round(self.rng.exponential(30), 2),
                "device_risk_flag": int(self.rng.random() < 0.2),
                "device_account_count": device_account_count
                if device_account_count
                else int(self.rng.poisson(2) + 1),
                "counterparty_risk_score": round(self.rng.uniform(0.4, 0.85), 4),
                "is_international": int(self.rng.random() < 0.08),
                "channel_switch_count": int(self.rng.poisson(2)),
                "currency": "INR",
                "ip_address": f"sha256:{self.rng.bytes(8).hex()}",
                "device_fingerprint": f"dev_fp_{self.rng.bytes(4).hex()}",
            }
        elif fraud_type == "dormant":
            return {
                "txn_id": txn_id,
                "from_account": from_acc,
                "to_account": to_acc,
                "amount": amount,
                "channel": self.rng.choice(["IMPS", "NEFT", "RTGS"]),
                "timestamp": timestamp.isoformat(),
                "is_fraud": 1,
                "fraud_type": fraud_type,
                "customer_age": self.rng.randint(25, 65),
                "account_age_days": self.rng.randint(365, 1825),
                "kyc_tier": int(self.rng.choice([1, 2, 3], p=[0.2, 0.5, 0.3])),
                "avg_monthly_balance": round(self.rng.lognormal(9, 0.5), 2),
                "transaction_count_30d": self.rng.poisson(1),
                "avg_txn_amount": round(self.rng.lognormal(7, 0.3), 2),
                "std_txn_amount": round(self.rng.uniform(1000, 5000), 2),
                "max_txn_amount": round(self.rng.uniform(10000, 50000), 2),
                "min_txn_amount": round(self.rng.uniform(1000, 10000), 2),
                "hour_of_day": timestamp.hour,
                "day_of_week": timestamp.weekday(),
                "is_weekend": int(timestamp.weekday() >= 5),
                "is_holiday": 0,
                "geo_distance_from_home": round(self.rng.exponential(100), 2),
                "device_risk_flag": int(self.rng.random() < 0.4),
                "device_account_count": device_account_count
                if device_account_count
                else int(self.rng.poisson(1) + 1),
                "counterparty_risk_score": round(self.rng.uniform(0.5, 0.95), 4),
                "is_international": int(self.rng.random() < 0.15),
                "channel_switch_count": int(self.rng.poisson(4)),
                "currency": "INR",
                "ip_address": f"sha256:{self.rng.bytes(8).hex()}",
                "device_fingerprint": f"dev_fp_{self.rng.bytes(4).hex()}",
            }
        elif fraud_type == "mule":
            return {
                "txn_id": txn_id,
                "from_account": from_acc,
                "to_account": to_acc,
                "amount": amount,
                "channel": self.rng.choice(["IMPS", "UPI", "NEFT"]),
                "timestamp": timestamp.isoformat(),
                "is_fraud": 1,
                "fraud_type": fraud_type,
                "customer_age": self.rng.randint(18, 35),
                "account_age_days": self.rng.randint(5, 180),
                "kyc_tier": int(self.rng.choice([1, 2], p=[0.7, 0.3])),
                "avg_monthly_balance": round(self.rng.lognormal(8, 0.5), 2),
                "transaction_count_30d": self.rng.poisson(40),
                "avg_txn_amount": round(self.rng.lognormal(9, 0.5), 2),
                "std_txn_amount": round(self.rng.uniform(30000, 100000), 2),
                "max_txn_amount": round(self.rng.uniform(100000, 600000), 2),
                "min_txn_amount": round(self.rng.uniform(5000, 30000), 2),
                "hour_of_day": timestamp.hour,
                "day_of_week": timestamp.weekday(),
                "is_weekend": int(timestamp.weekday() >= 5),
                "is_holiday": 0,
                "geo_distance_from_home": round(self.rng.exponential(80), 2),
                "device_risk_flag": 1,
                "device_account_count": device_account_count
                if device_account_count
                else int(self.rng.randint(4, 10)),
                "counterparty_risk_score": round(self.rng.uniform(0.6, 0.98), 4),
                "is_international": int(self.rng.random() < 0.12),
                "channel_switch_count": int(self.rng.poisson(3)),
                "currency": "INR",
                "ip_address": f"sha256:{self.rng.bytes(8).hex()}",
                "device_fingerprint": f"dev_fp_{self.rng.bytes(4).hex()}",
            }

    def apply_smote(
        self, df: pd.DataFrame, target_col: str = "is_fraud"
    ) -> pd.DataFrame:
        feature_cols = [
            "amount",
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
        available_cols = [c for c in feature_cols if c in df.columns]
        X = df[available_cols].values
        y = df[target_col].values
        smote = SMOTE(random_state=42)
        X_res, y_res = smote.fit_resample(X, y)
        df_res = pd.DataFrame(X_res, columns=available_cols)
        df_res[target_col] = y_res
        for col in df.columns:
            if col not in df_res.columns:
                df_res[col] = df[col].iloc[0] if len(df) > 0 else None
        return df_res

    def save_dataset(self, df: pd.DataFrame, path: str):
        os.makedirs(path, exist_ok=True)
        csv_path = os.path.join(path, "synthetic_dataset.csv")
        df.to_csv(csv_path, index=False)
        metadata = {
            "num_records": len(df),
            "num_fraud": int(df["is_fraud"].sum()),
            "num_normal": int((df["is_fraud"] == 0).sum()),
            "fraud_ratio": round(float(df["is_fraud"].mean()), 4),
            "columns": list(df.columns),
            "generated_at": datetime.now().isoformat(),
            "fraud_type_distribution": df["fraud_type"].value_counts().to_dict(),
        }
        meta_path = os.path.join(path, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _business_hour_probs(self):
        probs = np.array(
            [
                0.01,
                0.005,
                0.005,
                0.005,
                0.005,
                0.01,
                0.02,
                0.04,
                0.07,
                0.09,
                0.10,
                0.10,
                0.08,
                0.07,
                0.08,
                0.09,
                0.08,
                0.06,
                0.04,
                0.03,
                0.02,
                0.02,
                0.015,
                0.01,
            ]
        )
        return probs / probs.sum()
