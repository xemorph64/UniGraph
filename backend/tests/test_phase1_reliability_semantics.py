import asyncio

import pytest
from fastapi import HTTPException, Response

from backend.app.config import settings
from backend.app.main import health
from backend.app.routers import accounts, alerts, reports, transactions


def test_transactions_get_transaction_raises_404(monkeypatch):
    async def fake_get_transaction(txn_id: str):
        return None

    monkeypatch.setattr(transactions.neo4j_service, "get_transaction", fake_get_transaction)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(transactions.get_transaction("TXN-404"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Transaction not found"


def test_alerts_get_alert_raises_404(monkeypatch):
    async def fake_get_alert_by_id(alert_id: str):
        return None

    monkeypatch.setattr(alerts.neo4j_service, "get_alert_by_id", fake_get_alert_by_id)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(alerts.get_alert("ALT-404"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Alert not found"


def test_alerts_investigate_raises_404(monkeypatch):
    async def fake_get_alert_by_id(alert_id: str):
        return None

    monkeypatch.setattr(alerts.neo4j_service, "get_alert_by_id", fake_get_alert_by_id)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(alerts.investigate_alert("ALT-404", 2))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Alert not found"


def test_accounts_profile_raises_404(monkeypatch):
    class FakeResult:
        async def single(self):
            return None

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def run(self, *_args, **_kwargs):
            return FakeResult()

    class FakeDriver:
        def session(self):
            return FakeSession()

    monkeypatch.setattr(accounts.neo4j_service, "driver", FakeDriver())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(accounts.get_account_profile("ACC-404"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Account not found"


def test_generate_str_raises_500_on_persistence_failure(monkeypatch):
    async def fake_get_alert_by_id(alert_id: str):
        return {
            "id": alert_id,
            "account_id": "ACC-TEST-1",
            "risk_score": 89.0,
            "risk_level": "HIGH",
            "rule_flags": ["STRUCTURING"],
            "shap_top3": ["amount", "velocity_1h", "device_account_count"],
        }

    async def fake_get_account_subgraph(account_id: str, hops: int = 2):
        return {"nodes": [{"id": account_id}], "edges": []}

    async def fake_generate_str_narrative(case_data: dict):
        return f"Narrative for {case_data['account_id']}"

    async def fake_create_str_report(**_kwargs):
        raise RuntimeError("neo4j write failed")

    monkeypatch.setattr(reports.neo4j_service, "get_alert_by_id", fake_get_alert_by_id)
    monkeypatch.setattr(
        reports.neo4j_service,
        "get_account_subgraph",
        fake_get_account_subgraph,
    )
    monkeypatch.setattr(
        reports.llm_service,
        "generate_str_narrative",
        fake_generate_str_narrative,
    )
    monkeypatch.setattr(reports.neo4j_service, "create_str_report", fake_create_str_report)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            reports.generate_str(
                reports.STRGenerateRequest(alert_id="ALT-TEST-1", case_notes="case notes")
            )
        )

    assert exc.value.status_code == 500
    assert "Failed to persist STR draft" in exc.value.detail


def test_submit_str_raises_500_on_persistence_failure(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "DRAFT"}

    async def fake_submit_str_report(**_kwargs):
        raise RuntimeError("neo4j submit write failed")

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "submit_str_report", fake_submit_str_report)
    monkeypatch.setattr(reports.settings, "DEMO_MODE", True)
    monkeypatch.setattr(reports.settings, "FIU_IND_API_URL", "")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_CERT_PATH", "")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_KEY_PATH", "")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            reports.submit_str(
                "STR-TEST-1",
                reports.STRSubmitRequest(
                    str_id="STR-TEST-1",
                    edited_narrative="final narrative",
                    digital_signature="sig",
                ),
            )
        )

    assert exc.value.status_code == 500
    assert "Failed to persist STR submission" in exc.value.detail


def test_health_is_degraded_when_ml_unreachable(monkeypatch):
    async def fake_graph_stats():
        return {"total_accounts": 10}

    async def fake_ml_readiness():
        return {
            "ml_service_reachable": False,
            "ml_service_url": "http://localhost:8002",
            "fallback_mode_available": True,
        }

    monkeypatch.setattr("backend.app.main.neo4j_service.get_graph_stats", fake_graph_stats)
    monkeypatch.setattr("backend.app.main.fraud_scorer.get_ml_readiness", fake_ml_readiness)

    response = Response()
    payload = asyncio.run(health(response))

    assert response.status_code == 200
    assert payload["status"] == "degraded"
    assert payload["neo4j"] == "connected"


def test_health_is_unhealthy_when_neo4j_unreachable(monkeypatch):
    async def fake_graph_stats():
        raise RuntimeError("neo4j down")

    async def fake_ml_readiness():
        return {
            "ml_service_reachable": True,
            "ml_service_url": "http://localhost:8002",
            "fallback_mode_available": True,
        }

    monkeypatch.setattr("backend.app.main.neo4j_service.get_graph_stats", fake_graph_stats)
    monkeypatch.setattr("backend.app.main.fraud_scorer.get_ml_readiness", fake_ml_readiness)

    response = Response()
    payload = asyncio.run(health(response))

    assert response.status_code == 503
    assert payload["status"] == "unhealthy"
    assert payload["neo4j"] == "disconnected"


def test_health_is_healthy_when_neo4j_and_ml_ok(monkeypatch):
    async def fake_graph_stats():
        return {"total_accounts": 10}

    async def fake_ml_readiness():
        return {
            "ml_service_reachable": True,
            "ml_service_url": "http://localhost:8002",
            "fallback_mode_available": True,
            "ml_model_version": "v1",
        }

    monkeypatch.setattr("backend.app.main.neo4j_service.get_graph_stats", fake_graph_stats)
    monkeypatch.setattr("backend.app.main.fraud_scorer.get_ml_readiness", fake_ml_readiness)

    response = Response()
    payload = asyncio.run(health(response))

    assert response.status_code == 200
    assert payload["status"] == "healthy"
    assert payload["neo4j"] == "connected"


def test_health_is_unhealthy_when_ml_unreachable_in_strict_mode(monkeypatch):
    async def fake_graph_stats():
        return {"total_accounts": 10}

    async def fake_ml_readiness():
        return {
            "ml_service_reachable": False,
            "ml_service_url": "http://localhost:8002",
            "fallback_mode_available": True,
        }

    monkeypatch.setattr("backend.app.main.neo4j_service.get_graph_stats", fake_graph_stats)
    monkeypatch.setattr("backend.app.main.fraud_scorer.get_ml_readiness", fake_ml_readiness)
    monkeypatch.setattr(settings, "SCORER_REQUIRE_ML", True)

    response = Response()
    payload = asyncio.run(health(response))

    assert response.status_code == 503
    assert payload["status"] == "unhealthy"
    assert payload["neo4j"] == "connected"
