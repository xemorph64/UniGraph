#!/usr/bin/env python3
"""Validate trained model artifacts against UniGraph ML service contracts.

This script checks file presence, object interfaces, and performs a direct
in-process scoring probe through ml.serving.ml_service.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from ml.serving import ml_service  # noqa: E402


def _check_exists(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def _load_pickle(path: Path) -> Any:
    with path.open("rb") as fp:
        return pickle.load(fp)


def _required_interface(obj: Any, attrs: list[str]) -> list[str]:
    missing = []
    for attr in attrs:
        if not hasattr(obj, attr):
            missing.append(attr)
    return missing


def _validate_xgboost(path: Path) -> dict[str, Any]:
    info = _check_exists(path)
    if not info["exists"]:
        info.update({"ok": False, "error": "missing_file"})
        return info

    try:
        obj = _load_pickle(path)
        wrapped = isinstance(obj, dict)
        target = obj.get("model") if wrapped else obj
        required = ["prepare_features", "predict_proba", "predict_risk_score", "model"]
        missing = _required_interface(target, required) if target is not None else required
        loader_wrappable = bool(target is not None and hasattr(target, "predict_proba"))
        ok = len(missing) == 0 or loader_wrappable
        info.update(
            {
                "ok": ok,
                "type": type(obj).__name__,
                "wrapped": wrapped,
                "inner_type": type(target).__name__ if target is not None else None,
                "missing_interface": missing,
                "loader_wrappable": loader_wrappable,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive path
        info.update({"ok": False, "error": str(exc)})

    return info


def _validate_iforest(path: Path) -> dict[str, Any]:
    info = _check_exists(path)
    if not info["exists"]:
        info.update({"ok": False, "error": "missing_file"})
        return info

    try:
        obj = _load_pickle(path)
        wrapped = isinstance(obj, dict)
        target = obj.get("model") if wrapped else obj
        required = ["score_samples", "score_to_0_100"]
        missing = _required_interface(target, required) if target is not None else required
        loader_wrappable = bool(target is not None and hasattr(target, "score_samples"))
        ok = len(missing) == 0 or loader_wrappable
        info.update(
            {
                "ok": ok,
                "type": type(obj).__name__,
                "wrapped": wrapped,
                "inner_type": type(target).__name__ if target is not None else None,
                "missing_interface": missing,
                "loader_wrappable": loader_wrappable,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive path
        info.update({"ok": False, "error": str(exc)})

    return info


def _validate_graphsage(path: Path) -> dict[str, Any]:
    chosen_path = path
    if not chosen_path.exists():
        alt_path = path.with_name("graphsage.pt")
        if alt_path.exists():
            chosen_path = alt_path

    info = _check_exists(chosen_path)
    if not info["exists"]:
        # Optional for runtime; fallback remains valid if absent.
        info.update({"ok": True, "warning": "graphsage_model_missing_optional"})
        return info

    try:
        import torch

        checkpoint = torch.load(chosen_path, map_location="cpu")
        has_state = isinstance(checkpoint, dict) and "model_state_dict" in checkpoint
        info.update(
            {
                "ok": bool(has_state),
                "checkpoint_keys": list(checkpoint.keys()) if isinstance(checkpoint, dict) else [],
            }
        )
        if not has_state:
            info["error"] = "missing_model_state_dict"
    except Exception as exc:  # pragma: no cover - defensive path
        info.update({"ok": False, "error": str(exc)})

    return info


async def _run_scoring_probe(model_dir: Path) -> dict[str, Any]:
    await ml_service.load_models(str(model_dir))

    sample_txn = {
        "txn_id": "PROBE-TXN-001",
        "amount": 49000.0,
        "channel": "UPI",
        "velocity_1h": 4,
        "velocity_24h": 7,
        "device_account_count": 3,
        "is_dormant": False,
        "amount_zscore": 2.1,
        "channel_switch_count": 3,
        "account_age_days": 220,
        "kyc_tier": 2,
        "transaction_count_30d": 46,
        "avg_txn_amount_30d": 35000.0,
        "device_count_30d": 2,
        "ip_count_30d": 2,
        "rule_violations": ["STRUCTURING"],
    }

    sample_graph = {
        "pagerank": 0.07,
        "betweenness_centrality": 0.03,
        "community_id": 17,
        "in_degree_24h": 8,
        "out_degree_24h": 6,
        "shortest_path_to_fraud": 2,
        "community_risk_score": 0.41,
        "neighbor_fraud_ratio": 0.22,
    }

    score = await ml_service.score_transaction(sample_txn, sample_graph)
    return {
        "ml_health_flags": {
            "gnn_loaded": ml_service.gnn_model is not None,
            "if_loaded": ml_service.if_model is not None,
            "xgb_loaded": ml_service.xgb_model is not None,
            "fallback_ready": bool(ml_service.fallback_ready),
            "model_version": ml_service.model_version,
        },
        "sample_score": score,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate model artifact compatibility")
    parser.add_argument(
        "--artifact-dir",
        required=True,
        help="Directory containing xgboost_model.pkl, isolation_forest_model.pkl, and optional graphsage_model.pt",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON only",
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir).expanduser().resolve()
    xgb_path = artifact_dir / "xgboost_model.pkl"
    if_path = artifact_dir / "isolation_forest_model.pkl"
    gnn_path = artifact_dir / "graphsage_model.pt"

    report: dict[str, Any] = {
        "artifact_dir": str(artifact_dir),
        "xgboost": _validate_xgboost(xgb_path),
        "isolation_forest": _validate_iforest(if_path),
        "graphsage": _validate_graphsage(gnn_path),
    }

    hard_fail = (not report["xgboost"].get("ok", False)) or (not report["isolation_forest"].get("ok", False))

    probe_error = None
    probe_result = None
    try:
        probe_result = asyncio.run(_run_scoring_probe(artifact_dir))
    except Exception as exc:
        probe_error = str(exc)

    report["probe_ok"] = probe_error is None
    report["probe_error"] = probe_error
    report["probe_result"] = probe_result

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("Artifact directory:", report["artifact_dir"])
        print("XGBoost:", json.dumps(report["xgboost"], indent=2, default=str))
        print("Isolation Forest:", json.dumps(report["isolation_forest"], indent=2, default=str))
        print("GraphSAGE:", json.dumps(report["graphsage"], indent=2, default=str))
        print("Probe OK:", report["probe_ok"])
        if report["probe_error"]:
            print("Probe error:", report["probe_error"])
        elif report["probe_result"]:
            print("Probe result:", json.dumps(report["probe_result"], indent=2, default=str))

    if hard_fail:
        return 2
    if probe_error is not None:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
