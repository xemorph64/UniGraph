import numpy as np
from datetime import datetime
from typing import Optional


class FeatureEngineer:
    def __init__(self, neo4j_driver=None, redis_client=None):
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self._account_history = {}

    def extract_transaction_features(self, txn: dict) -> dict:
        """Extract per-transaction features."""
        return {
            "amount_zscore": self._amount_zscore(txn),
            "velocity_1h": self._velocity(txn, window_hours=1),
            "velocity_6h": self._velocity(txn, window_hours=6),
            "velocity_24h": self._velocity(txn, window_hours=24),
            "hour_sin": np.sin(2 * np.pi * txn.get("hour", 0) / 24),
            "hour_cos": np.cos(2 * np.pi * txn.get("hour", 0) / 24),
            "day_sin": np.sin(2 * np.pi * txn.get("day_of_week", 0) / 7),
            "day_cos": np.cos(2 * np.pi * txn.get("day_of_week", 0) / 7),
            "geo_distance": self._geo_distance(txn),
            "channel_switch_count": self._channel_switches(txn),
            "counterparty_risk": self._counterparty_risk(txn),
            "amount_to_avg_ratio": txn["amount"] / max(self._avg_amount(txn), 1.0),
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
            "min_txn_amount_30d": self._min_txn_amount(account_id),
            "median_txn_amount_30d": self._median_txn_amount(account_id),
        }

    def build_feature_vector(self, txn: dict) -> dict:
        """Combine all feature types into single vector for ML."""
        account_id = txn["from_account"]
        features = {}
        features.update(self.extract_transaction_features(txn))
        if self.neo4j is not None:
            features.update(self.extract_graph_features(account_id))
        features.update(self.extract_account_features(account_id))
        return features

    def _amount_zscore(self, txn: dict) -> float:
        account_id = txn.get("from_account", "")
        history = self._account_history.get(account_id, {})
        mean = history.get("mean_amount", 50000.0)
        std = history.get("std_amount", 25000.0)
        if std == 0:
            return 0.0
        return (txn["amount"] - mean) / std

    def _velocity(self, txn: dict, window_hours: int = 1) -> int:
        account_id = txn.get("from_account", "")
        history = self._account_history.get(account_id, {})
        return history.get(f"velocity_{window_hours}h", 0)

    def _geo_distance(self, txn: dict) -> float:
        return txn.get("geo_distance_from_home", 0.0)

    def _channel_switches(self, txn: dict) -> int:
        account_id = txn.get("from_account", "")
        history = self._account_history.get(account_id, {})
        return history.get("channel_switch_count", 0)

    def _counterparty_risk(self, txn: dict) -> float:
        return txn.get("counterparty_risk_score", 0.0)

    def _avg_amount(self, txn: dict) -> float:
        account_id = txn.get("from_account", "")
        history = self._account_history.get(account_id, {})
        return history.get("mean_amount", 50000.0)

    def _is_round_amount(self, amount: float) -> int:
        return int(amount % 1000 == 0)

    def _time_since_last(self, txn: dict) -> float:
        account_id = txn.get("from_account", "")
        history = self._account_history.get(account_id, {})
        return history.get("time_since_last_txn_minutes", 1440.0)

    def _get_pagerank(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _get_betweenness(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _get_community(self, account_id: str) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _get_clustering(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _in_degree(self, account_id: str, hours: int = 24) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _out_degree(self, account_id: str, hours: int = 24) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _shortest_path_to_known_fraud(self, account_id: str) -> int:
        if self.neo4j is None:
            return -1
        return -1

    def _community_risk(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _neighbor_fraud_ratio(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _account_age(self, account_id: str) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _kyc_tier(self, account_id: str) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _is_dormant(self, account_id: str) -> bool:
        if self.neo4j is None:
            return False
        return False

    def _dormant_days(self, account_id: str) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _avg_balance(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _txn_count_30d(self, account_id: str) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _unique_counterparties(self, account_id: str) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _avg_txn_amount(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _std_txn_amount(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _max_txn_amount(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _device_count(self, account_id: str) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _ip_count(self, account_id: str) -> int:
        if self.neo4j is None:
            return 0
        return 0

    def _min_txn_amount(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0

    def _median_txn_amount(self, account_id: str) -> float:
        if self.neo4j is None:
            return 0.0
        return 0.0
