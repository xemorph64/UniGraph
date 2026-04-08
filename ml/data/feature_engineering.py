from datetime import datetime, timezone
from typing import Any

import numpy as np


class FeatureEngineer:
    def __init__(self, neo4j_driver, redis_client):
        self.neo4j = neo4j_driver
        self.redis = redis_client

    def extract_transaction_features(self, txn: dict) -> dict:
        """Extract per-transaction features."""
        return {
            "amount_zscore": self._amount_zscore(txn),
            "velocity_1h": self._velocity(txn, window_hours=1),
            "velocity_6h": self._velocity(txn, window_hours=6),
            "velocity_24h": self._velocity(txn, window_hours=24),
            "hour_sin": np.sin(2 * np.pi * txn["hour"] / 24),
            "hour_cos": np.cos(2 * np.pi * txn["hour"] / 24),
            "day_sin": np.sin(2 * np.pi * txn["day_of_week"] / 7),
            "day_cos": np.cos(2 * np.pi * txn["day_of_week"] / 7),
            "geo_distance": self._geo_distance(txn),
            "channel_switch_count": self._channel_switches(txn),
            "counterparty_risk": self._counterparty_risk(txn),
            "amount_to_avg_ratio": txn["amount"] / self._avg_amount(txn),
            "is_round_amount": self._is_round_amount(txn["amount"]),
            "time_since_last_txn": self._time_since_last(txn),
        }

    def extract_graph_features(self, account_id: str) -> dict:
        """Extract graph-based features from Neo4j GDS."""
        return {
            "pagerank": self._get_pagerank(account_id),
            "betweenness_centrality": self._get_betweenness(account_id),
            "community_id": self._get_community(account_id),
            "clustering_coefficient": self._get_clustering(account_id),
            "in_degree_24h": self._in_degree(account_id, hours=24),
            "out_degree_24h": self._out_degree(account_id, hours=24),
            "shortest_path_to_fraud": self._shortest_path_to_known_fraud(account_id),
            "community_risk_score": self._community_risk(account_id),
            "neighbor_fraud_ratio": self._neighbor_fraud_ratio(account_id),
        }

    def extract_account_features(self, account_id: str) -> dict:
        """Extract account-level features."""
        return {
            "account_age_days": self._account_age(account_id),
            "kyc_tier": self._kyc_tier(account_id),
            "is_dormant": self._is_dormant(account_id),
            "dormant_days": self._dormant_days(account_id),
            "avg_monthly_balance": self._avg_balance(account_id),
            "transaction_count_30d": self._txn_count_30d(account_id),
            "unique_counterparties_30d": self._unique_counterparties(account_id),
            "avg_txn_amount_30d": self._avg_txn_amount(account_id),
            "std_txn_amount_30d": self._std_txn_amount(account_id),
            "max_txn_amount_30d": self._max_txn_amount(account_id),
            "device_count_30d": self._device_count(account_id),
            "ip_count_30d": self._ip_count(account_id),
        }

    def build_feature_vector(self, txn: dict) -> dict:
        """Combine all feature types into single vector for ML."""
        account_id = txn["from_account"]
        features = {}
        features.update(self.extract_transaction_features(txn))
        features.update(self.extract_graph_features(account_id))
        account_features = self.extract_account_features(account_id)
        for key in (
            "account_age_days",
            "kyc_tier",
            "is_dormant",
            "dormant_days",
            "avg_monthly_balance",
        ):
            features[key] = account_features[key]
        return features

    def _amount_zscore(self, txn: dict) -> float:
        avg = float(txn.get("avg_txn_amount", txn.get("amount", 0.0)))
        std = float(txn.get("std_txn_amount", max(avg * 0.25, 1.0)))
        return float((float(txn["amount"]) - avg) / max(std, 1e-6))

    def _velocity(self, txn: dict, window_hours: int) -> int:
        key = f"velocity:{txn['from_account']}:{window_hours}h"
        if self.redis is not None:
            value = self.redis.get(key)
            if value is not None:
                return int(value)

        base_velocity = float(txn.get("transaction_count_30d", 0)) / 30.0
        estimated = max(0, int(round(base_velocity * window_hours)))
        return estimated

    def _geo_distance(self, txn: dict) -> float:
        if "geo_distance_from_home" in txn:
            return float(txn["geo_distance_from_home"])

        lat = float(txn.get("geo_lat", 0.0))
        lon = float(txn.get("geo_lon", 0.0))
        home_lat = float(txn.get("home_lat", lat))
        home_lon = float(txn.get("home_lon", lon))

        lat1, lon1, lat2, lon2 = map(np.radians, [lat, lon, home_lat, home_lon])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))
        return float(6371.0 * c)

    def _channel_switches(self, txn: dict) -> int:
        if "channel_switch_count" in txn:
            return int(txn["channel_switch_count"])

        key = f"channel_switches:{txn['from_account']}"
        if self.redis is not None:
            value = self.redis.get(key)
            if value is not None:
                return int(value)
        return 0

    def _counterparty_risk(self, txn: dict) -> float:
        return float(txn.get("counterparty_risk_score", 0.0))

    def _avg_amount(self, txn: dict) -> float:
        return max(float(txn.get("avg_txn_amount", txn["amount"])), 1.0)

    def _is_round_amount(self, amount: float) -> int:
        return int(float(amount) % 1000 == 0 or float(amount) % 500 == 0)

    def _time_since_last(self, txn: dict) -> float:
        ts = self._parse_ts(txn.get("timestamp"))
        last_ts = self._parse_ts(txn.get("last_txn_timestamp"))
        return float((ts - last_ts).total_seconds())

    def _get_pagerank(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "pagerank", 0.0)

    def _get_betweenness(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "betweenness_centrality", 0.0)

    def _get_community(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "community_id", 0))

    def _get_clustering(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "clustering_coefficient", 0.0)

    def _in_degree(self, account_id: str, hours: int = 24) -> int:
        return int(self._neo4j_numeric(account_id, f"in_degree_{hours}h", 0))

    def _out_degree(self, account_id: str, hours: int = 24) -> int:
        return int(self._neo4j_numeric(account_id, f"out_degree_{hours}h", 0))

    def _shortest_path_to_known_fraud(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "shortest_path_to_fraud", 99))

    def _community_risk(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "community_risk_score", 0.0)

    def _neighbor_fraud_ratio(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "neighbor_fraud_ratio", 0.0)

    def _account_age(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "account_age_days", 0))

    def _kyc_tier(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "kyc_tier", 1))

    def _is_dormant(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "is_dormant", 0))

    def _dormant_days(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "dormant_days", 0))

    def _avg_balance(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "avg_monthly_balance", 0.0)

    def _txn_count_30d(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "transaction_count_30d", 0))

    def _unique_counterparties(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "unique_counterparties_30d", 0))

    def _avg_txn_amount(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "avg_txn_amount_30d", 0.0)

    def _std_txn_amount(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "std_txn_amount_30d", 0.0)

    def _max_txn_amount(self, account_id: str) -> float:
        return self._neo4j_numeric(account_id, "max_txn_amount_30d", 0.0)

    def _device_count(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "device_count_30d", 0))

    def _ip_count(self, account_id: str) -> int:
        return int(self._neo4j_numeric(account_id, "ip_count_30d", 0))

    def _neo4j_numeric(self, account_id: str, key: str, default: float) -> float:
        if self.neo4j is None:
            return float(default)

        getter = getattr(self.neo4j, "get_account_features", None)
        if callable(getter):
            try:
                data = getter(account_id)
                if isinstance(data, dict) and key in data:
                    return float(data[key])
            except Exception:
                return float(default)

        if isinstance(self.neo4j, dict):
            account_data = self.neo4j.get(account_id, {})
            if isinstance(account_data, dict) and key in account_data:
                return float(account_data[key])

        return float(default)

    def _parse_ts(self, value: Any) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value

        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return datetime.now(timezone.utc)
