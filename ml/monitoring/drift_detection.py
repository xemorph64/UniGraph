import numpy as np
import pandas as pd
from typing import Optional


class DriftDetector:
    def __init__(self, reference_data: pd.DataFrame, psi_threshold: float = 0.2):
        self.reference = reference_data
        self.psi_threshold = psi_threshold
        self.reference_stats = self._compute_stats(reference_data)

    def _compute_stats(self, df: pd.DataFrame) -> dict:
        stats = {}
        for col in df.columns:
            if df[col].dtype in [np.float64, np.int64]:
                stats[col] = {
                    "mean": df[col].mean(),
                    "std": df[col].std(),
                    "min": df[col].min(),
                    "max": df[col].max(),
                    "bins": np.percentile(
                        df[col], [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
                    ),
                }
        return stats

    def compute_psi(self, current_data: pd.DataFrame, feature: str) -> float:
        if feature not in self.reference_stats:
            return 0.0

        ref_bins = self.reference_stats[feature]["bins"]
        ref_dist = np.diff(ref_bins) / len(ref_bins)

        curr_values = current_data[feature].values
        curr_hist, _ = np.histogram(curr_values, bins=ref_bins)
        curr_dist = curr_hist / curr_hist.sum() + 1e-10

        ref_dist = ref_dist + 1e-10
        psi = np.sum((curr_dist - ref_dist) * np.log(curr_dist / ref_dist))
        return abs(psi)

    def detect_drift(self, current_data: pd.DataFrame) -> dict:
        psi_scores = {}
        features_drifted = []

        for feature in self.reference_stats.keys():
            if feature in current_data.columns:
                psi = self.compute_psi(current_data, feature)
                psi_scores[feature] = round(psi, 4)
                if psi > self.psi_threshold:
                    features_drifted.append(feature)

        severity = "NONE"
        if len(features_drifted) >= 3:
            severity = "HIGH"
        elif len(features_drifted) >= 1:
            severity = "MEDIUM"

        drift_detected = len(features_drifted) > 0

        return {
            "drift_detected": drift_detected,
            "features_drifted": features_drifted,
            "psi_scores": psi_scores,
            "severity": severity,
        }

    def alert_if_drifted(self, results: dict):
        if results["drift_detected"]:
            print(f"[ALERT] Drift detected in features: {results['features_drifted']}")
            for feature, psi in results["psi_scores"].items():
                if psi > self.psi_threshold:
                    print(
                        f"  {feature}: PSI={psi:.4f} (threshold={self.psi_threshold})"
                    )
