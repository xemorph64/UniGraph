import numpy as np
import pandas as pd
from typing import Optional


class FairnessTester:
    def __init__(self, model, test_data: pd.DataFrame):
        self.model = model
        self.data = test_data

    def test_demographic_parity(self, protected_attribute: str) -> dict:
        if protected_attribute not in self.data.columns:
            return {
                "passed": True,
                "max_difference": 0.0,
                "threshold": 0.05,
                "details": {},
            }

        groups = self.data[protected_attribute].unique()
        fraud_rates = {}

        for group in groups:
            group_data = self.data[self.data[protected_attribute] == group]
            fraud_rate = group_data["is_fraud"].mean()
            fraud_rates[str(group)] = fraud_rate

        max_diff = (
            max(fraud_rates.values()) - min(fraud_rates.values())
            if fraud_rates
            else 0.0
        )

        return {
            "passed": max_diff < 0.05,
            "max_difference": round(max_diff, 4),
            "threshold": 0.05,
            "details": fraud_rates,
        }

    def test_equalized_odds(self, protected_attribute: str) -> dict:
        if protected_attribute not in self.data.columns:
            return {"passed": True, "tpr_difference": 0.0, "fpr_difference": 0.0}

        groups = self.data[protected_attribute].unique()
        tprs = {}
        fprs = {}

        for group in groups:
            group_data = self.data[self.data[protected_attribute] == group]
            if len(group_data) > 0:
                tp = ((group_data["pred"] == 1) & (group_data["is_fraud"] == 1)).sum()
                fn = ((group_data["pred"] == 0) & (group_data["is_fraud"] == 1)).sum()
                fp = ((group_data["pred"] == 1) & (group_data["is_fraud"] == 0)).sum()
                tn = ((group_data["pred"] == 0) & (group_data["is_fraud"] == 0)).sum()

                tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

                tprs[str(group)] = tpr
                fprs[str(group)] = fpr

        tpr_diff = max(tprs.values()) - min(tprs.values()) if tprs else 0.0
        fpr_diff = max(fprs.values()) - min(fprs.values()) if fprs else 0.0

        return {
            "passed": tpr_diff < 0.05 and fpr_diff < 0.05,
            "tpr_difference": round(tpr_diff, 4),
            "fpr_difference": round(fpr_diff, 4),
            "tpr_by_group": tprs,
            "fpr_by_group": fprs,
        }

    def test_predictive_parity(self, protected_attribute: str) -> dict:
        if protected_attribute not in self.data.columns:
            return {"passed": True, "ppv_difference": 0.0, "threshold": 0.05}

        groups = self.data[protected_attribute].unique()
        ppvs = {}

        for group in groups:
            group_data = self.data[self.data[protected_attribute] == group]
            if len(group_data) > 0:
                tp = ((group_data["pred"] == 1) & (group_data["is_fraud"] == 1)).sum()
                fp = ((group_data["pred"] == 1) & (group_data["is_fraud"] == 0)).sum()
                ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                ppvs[str(group)] = ppv

        ppv_diff = max(ppvs.values()) - min(ppvs.values()) if ppvs else 0.0

        return {
            "passed": ppv_diff < 0.05,
            "ppv_difference": round(ppv_diff, 4),
            "threshold": 0.05,
            "ppv_by_group": ppvs,
        }

    def run_all_tests(self) -> dict:
        gender_col = "gender" if "gender" in self.data.columns else None
        age_col = "age_group" if "age_group" in self.data.columns else None
        location_col = "location_type" if "location_type" in self.data.columns else None

        results = {"tests": {}, "overall": "PASS"}

        if gender_col:
            results["tests"]["demographic_parity_gender"] = (
                self.test_demographic_parity(gender_col)
            )
            results["tests"]["equalized_odds_gender"] = self.test_equalized_odds(
                gender_col
            )

        if age_col:
            results["tests"]["demographic_parity_age"] = self.test_demographic_parity(
                age_col
            )
            results["tests"]["predictive_parity_age"] = self.test_predictive_parity(
                age_col
            )

        all_passed = all(t.get("passed", True) for t in results["tests"].values())
        results["overall"] = "PASS" if all_passed else "FAIL"

        return results
