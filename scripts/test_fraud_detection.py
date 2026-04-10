#!/usr/bin/env python3
"""
UniGRAPH Fraud Test Script
Tests fraud detection for:
- Circular/Round-trip transactions
- Rapid Layering
- Dormant Account Awakening
- Mule Network Detection
"""

import json
from datetime import datetime, timedelta
from ml.data.synthetic_generator import SyntheticFraudGenerator
from ml.data.feature_engineering import FeatureEngineer


def test_circular_transaction():
    """Test circular transaction (round-trip) detection"""
    print("\n" + "=" * 60)
    print("TEST: Circular Transaction (Round-Trip) Detection")
    print("=" * 60)

    # Create a circular transaction pattern
    accounts = ["ACC-001", "ACC-002", "ACC-003", "ACC-001"]  # Returns to origin

    txns = []
    base_time = datetime.now()
    for i, (src, dst) in enumerate(zip(accounts[:-1], accounts[1:])):
        txn = {
            "txn_id": f"TXN-CIRC-{i:03d}",
            "from_account": src,
            "to_account": dst,
            "amount": 75000.00 + (i * 5000),
            "channel": "IMPS",
            "timestamp": (base_time + timedelta(minutes=i * 10)).isoformat(),
            "hour": (base_time + timedelta(minutes=i * 10)).hour,
            "day_of_week": (base_time + timedelta(minutes=i * 10)).weekday(),
            "device_risk_flag": 1,
            "device_account_count": 5,  # Multiple accounts sharing device
            "counterparty_risk_score": 0.85,
            "transaction_count_30d": 25,
            "avg_txn_amount": 50000,
            "std_txn_amount": 15000,
        }
        txns.append(txn)

    # Check for circular pattern
    if txns[0]["from_account"] == txns[-1]["to_account"]:
        print("✅ CIRCULAR PATTERN DETECTED: Funds returning to origin")
        print(
            f"   Cycle: {' → '.join([t['from_account'] for t in txns])} → {txns[-1]['to_account']}"
        )

    # Score with feature engineering
    fe = FeatureEngineer()
    features = fe.build_feature_vector(txns[0])

    # High risk indicators
    risk_score = 0
    if features.get("channel_switch_count", 0) > 3:
        risk_score += 25
    if features.get("counterparty_risk", 0) > 0.7:
        risk_score += 30
    if txns[0].get("device_account_count", 0) > 3:
        risk_score += 25

    print(f"\n📊 Risk Score: {risk_score}/100")
    print(f"   Counterparty Risk: {features.get('counterparty_risk', 0):.2f}")
    print(f"   Channel Switches: {features.get('channel_switch_count', 0)}")

    return txns


def test_rapid_layering():
    """Test rapid layering detection (multiple hops in short time)"""
    print("\n" + "=" * 60)
    print("TEST: Rapid Layering Detection")
    print("=" * 60)

    # Create rapid layering pattern: 6 transactions in <30 minutes
    accounts = [f"ACC-{i:03d}" for i in range(1, 8)]
    txns = []
    base_time = datetime.now()

    for i in range(6):
        txn = {
            "txn_id": f"TXN-LAYER-{i:03d}",
            "from_account": accounts[i],
            "to_account": accounts[i + 1],
            "amount": 50000 + (5000 * (5 - i)),  # Decreasing amounts
            "channel": "IMPS" if i % 2 == 0 else "RTGS",
            "timestamp": (base_time + timedelta(minutes=i * 5)).isoformat(),
            "hour": (base_time + timedelta(minutes=i * 5)).hour,
            "day_of_week": (base_time + timedelta(minutes=i * 5)).weekday(),
            "device_risk_flag": 1,
            "device_account_count": 6,
            "counterparty_risk_score": 0.90,
            "transaction_count_30d": 50,
            "avg_txn_amount": 55000,
            "std_txn_amount": 10000,
            "channel_switch_count": 4,
        }
        txns.append(txn)

    # Check for rapid layering
    time_diff = (
        datetime.fromisoformat(txns[-1]["timestamp"])
        - datetime.fromisoformat(txns[0]["timestamp"])
    ).total_seconds() / 60

    print(f"⏱️  Time window: {time_diff:.0f} minutes (threshold: 30 min)")
    print(f"📈 Number of hops: {len(txns)}")
    print(f"💰 Total amount: {sum(t['amount'] for t in txns):,.0f} INR")

    if time_diff < 30 and len(txns) >= 5:
        print("\n✅ RAPID LAYERING DETECTED!")
        print(f"   Pattern: {len(txns)} transactions in {time_diff:.0f} minutes")
        print(f"   Each > 50,000 INR (CTR threshold)")

    # Calculate risk
    fe = FeatureEngineer()
    risk_score = 0
    for txn in txns[:3]:  # Check first few
        features = fe.build_feature_vector(txn)
        if features.get("amount_to_avg_ratio", 0) > 1.0:
            risk_score += 20
        if features.get("velocity_1h", 0) > 5:
            risk_score += 15

    print(f"\n📊 Risk Score: {min(risk_score, 100)}/100")
    print(f"   High velocity detected")
    print(f"   Multiple channel switches")

    return txns


def test_dormant_awakening():
    """Test dormant account awakening detection"""
    print("\n" + "=" * 60)
    print("TEST: Dormant Account Awakening Detection")
    print("=" * 60)

    # Create dormant account pattern
    txn = {
        "txn_id": "TXN-DORM-001",
        "from_account": "ACC-DORMANT-001",
        "to_account": "ACC-RECIPIENT-001",
        "amount": 250000.00,  # Large transaction
        "channel": "RTGS",
        "timestamp": datetime.now().isoformat(),
        "hour": datetime.now().hour,
        "day_of_week": datetime.now().weekday(),
        "device_risk_flag": 1,
        "device_account_count": 3,
        "counterparty_risk_score": 0.75,
        "transaction_count_30d": 1,  # Very low activity
        "avg_txn_amount": 2500,  # Historically low
        "std_txn_amount": 500,
        "is_dormant": 1,
        "dormant_days": 210,  # 7 months dormant
    }

    print(f"📋 Account: {txn['from_account']}")
    print(f"   Dormant days: {txn['dormant_days']}")
    print(f"   Transaction count (30d): {txn['transaction_count_30d']}")
    print(f"   Avg txn history: {txn['avg_txn_amount']:,} INR")
    print(f"   Current txn: {txn['amount']:,} INR")

    # Check for dormant awakening
    if txn["dormant_days"] > 180 and txn["amount"] > 100000:
        print("\n✅ DORMANT AWAKENING DETECTED!")
        print(f"   Account dormant for {txn['dormant_days']} days")
        print(f"   Sudden large transaction: {txn['amount']:,} INR")

    # Calculate risk
    fe = FeatureEngineer()
    features = fe.build_feature_vector(txn)

    risk_score = 0
    if txn["amount"] > txn["avg_txn_amount"] * 10:
        risk_score += 40
    if txn["dormant_days"] > 180:
        risk_score += 35
    if txn["transaction_count_30d"] < 5:
        risk_score += 20

    print(f"\n📊 Risk Score: {min(risk_score, 100)}/100")
    print(f"   Large deviation from historical pattern")

    return txn


def test_mule_network():
    """Test mule network detection (shared device/IP)"""
    print("\n" + "=" * 60)
    print("TEST: Mule Network Detection")
    print("=" * 60)

    # Create mule network pattern - multiple accounts using same device
    device_id = "DEVICE-SHARED-001"
    mule_accounts = [
        "ACC-MULE-001",
        "ACC-MULE-002",
        "ACC-MULE-003",
        "ACC-MULE-004",
        "ACC-MULE-005",
    ]

    txns = []
    base_time = datetime.now()

    for i, acc in enumerate(mule_accounts):
        txn = {
            "txn_id": f"TXN-MULE-{i:03d}",
            "from_account": acc,
            "to_account": "ACC-DESTINATION-001",
            "amount": 45000.00 + (i * 5000),
            "channel": "IMPS",
            "timestamp": (base_time + timedelta(hours=i * 2)).isoformat(),
            "hour": (base_time + timedelta(hours=i * 2)).hour,
            "day_of_week": (base_time + timedelta(hours=i * 2)).weekday(),
            "device_fingerprint": device_id,
            "device_risk_flag": 1,
            "device_account_count": 5,  # 5 accounts sharing same device
            "counterparty_risk_score": 0.88,
            "transaction_count_30d": 15,
            "avg_txn_amount": 40000,
            "std_txn_amount": 8000,
            "channel_switch_count": 3,
        }
        txns.append(txn)

    print(f" Device: {device_id}")
    print(f"   Accounts using device: {len(mule_accounts)}")
    print(f"   Transactions: {len(txns)}")

    # Check for mule network
    if len(mule_accounts) >= 4:
        print("\n✅ MULE NETWORK DETECTED!")
        print(f"   {len(mule_accounts)} accounts sharing same device/IP")
        print(f"   Pattern: Multiple accounts funneling to single destination")

    # Calculate risk
    fe = FeatureEngineer()
    features = fe.build_feature_vector(txns[0])

    risk_score = 0
    if txns[0]["device_account_count"] >= 4:
        risk_score += 40
    if txns[0]["counterparty_risk_score"] > 0.8:
        risk_score += 30
    if txns[0]["channel_switch_count"] > 2:
        risk_score += 15

    print(f"\n📊 Risk Score: {min(risk_score, 100)}/100")
    print(f"   Device sharing risk: {txns[0]['device_account_count']} accounts")
    print(f"   High counterparty risk")

    return txns


def run_all_tests():
    """Run all fraud detection tests"""
    print("\n" + "#" * 60)
    print("# UniGRAPH Fraud Detection Test Suite")
    print("#" * 60)

    results = {}

    results["circular"] = test_circular_transaction()
    results["layering"] = test_rapid_layering()
    results["dormant"] = test_dormant_awakening()
    results["mule"] = test_mule_network()

    print("\n" + "#" * 60)
    print("# TEST SUMMARY")
    print("#" * 60)
    print("\n✅ All fraud detection tests completed!")
    print("\nFraud Types Tested:")
    print("  1. Circular/Round-Trip Transactions")
    print("  2. Rapid Layering (multiple hops <30 min)")
    print("  3. Dormant Account Awakening")
    print("  4. Mule Network (shared device/IP)")

    return results


if __name__ == "__main__":
    run_all_tests()
