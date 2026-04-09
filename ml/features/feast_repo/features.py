from datetime import timedelta
from feast import Entity, Feature, FeatureView, FileSource, ValueType, Duration


account = Entity(name="account_id", value_type=ValueType.STRING)
customer = Entity(name="customer_id", value_type=ValueType.STRING)


account_features = FeatureView(
    name="account_features",
    entities=["account_id"],
    ttl=Duration(days=1),
    features=[
        Feature(name="account_age_days", dtype=ValueType.INT32),
        Feature(name="kyc_tier", dtype=ValueType.INT32),
        Feature(name="is_dormant", dtype=ValueType.BOOL),
        Feature(name="avg_monthly_balance", dtype=ValueType.FLOAT),
        Feature(name="transaction_count_30d", dtype=ValueType.INT32),
        Feature(name="avg_txn_amount_30d", dtype=ValueType.FLOAT),
        Feature(name="std_txn_amount_30d", dtype=ValueType.FLOAT),
    ],
    online=True,
    batch_source=FileSource(
        path="data/account_features.parquet",
        timestamp_field="created_at",
        created_timestamp_column="created_at",
    ),
)


transaction_features = FeatureView(
    name="transaction_features",
    entities=["account_id"],
    ttl=Duration(hours=24),
    features=[
        Feature(name="velocity_1h", dtype=ValueType.INT32),
        Feature(name="velocity_24h", dtype=ValueType.INT32),
        Feature(name="amount_zscore", dtype=ValueType.FLOAT),
        Feature(name="channel_switch_count", dtype=ValueType.INT32),
    ],
    online=True,
    batch_source=FileSource(
        path="data/transaction_features.parquet",
        timestamp_field="txn_time",
        created_timestamp_column="txn_time",
    ),
)


graph_features = FeatureView(
    name="graph_features",
    entities=["account_id"],
    ttl=Duration(hours=6),
    features=[
        Feature(name="pagerank", dtype=ValueType.FLOAT),
        Feature(name="betweenness_centrality", dtype=ValueType.FLOAT),
        Feature(name="community_id", dtype=ValueType.INT32),
        Feature(name="clustering_coefficient", dtype=ValueType.FLOAT),
    ],
    online=True,
    batch_source=FileSource(
        path="data/graph_features.parquet",
        timestamp_field="computed_at",
        created_timestamp_column="computed_at",
    ),
)
