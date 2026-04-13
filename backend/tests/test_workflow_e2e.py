import pytest
from fastapi.testclient import TestClient

from backend.app.auth.jwt_rbac import User, create_access_token
from backend.app.config import settings
from backend.app.main import app
from backend.app.routers import enforcement, reports


def _headers(user_id: str, role: str) -> dict:
    token = create_access_token(User(user_id=user_id, username=user_id, role=role))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _strict_non_demo_config(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "DEMO_SEED_ON_STARTUP", False)
    monkeypatch.setattr(settings, "FINACLE_API_URL", "https://finacle.test")
    monkeypatch.setattr(settings, "FINACLE_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "FINACLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "FIU_IND_API_URL", "https://fiu.test")
    monkeypatch.setattr(settings, "FIU_IND_MTLS_CERT_PATH", "cert.pem")
    monkeypatch.setattr(settings, "FIU_IND_MTLS_KEY_PATH", "key.pem")
    monkeypatch.setattr(settings, "NCRP_API_URL", "https://ncrp.test")
    monkeypatch.setattr(settings, "NCRP_API_KEY", "test-key")


def test_str_generate_approve_submit_workflow_with_persistence(monkeypatch):
    store = {}

    async def fake_get_alert_by_id(alert_id: str):
        return {
            "id": alert_id,
            "account_id": "ACC-E2E-1",
            "transaction_id": "TXN-E2E-1",
            "risk_score": 91.2,
            "risk_level": "CRITICAL",
            "rule_flags": ["STRUCTURING"],
            "shap_top3": ["velocity_1h", "amount", "device_account_count"],
        }

    async def fake_get_account_subgraph(account_id: str, hops: int = 2):
        return {"nodes": [{"id": account_id}], "edges": []}

    async def fake_get_transaction(txn_id: str):
        return {
            "txn_id": txn_id,
            "amount": 250000,
            "channel": "RTGS",
            "from_account": "ACC-E2E-1",
            "to_account": "ACC-E2E-2",
            "timestamp": "2026-03-09T16:56:00Z",
            "scoring_source": "ml_blended",
            "model_version": "e2e-model-v1",
        }

    async def fake_generate_str_narrative(case_data: dict):
        return f"Narrative for {case_data['account_id']}"

    async def fake_create_str_report(**kwargs):
        store[kwargs["str_id"]] = {
            "id": kwargs["str_id"],
            "status": "DRAFT",
            "account_id": kwargs["account_id"],
            "narrative": kwargs["narrative"],
        }
        return store[kwargs["str_id"]]

    async def fake_get_str_report(str_id: str):
        return store.get(str_id)

    async def fake_update_str_review(**kwargs):
        item = store[kwargs["str_id"]]
        item["status"] = kwargs["status"]
        item["reviewed_by"] = kwargs["reviewed_by"]
        item["review_notes"] = kwargs["review_notes"]
        return item

    async def fake_submit_str_report(**kwargs):
        item = store[kwargs["str_id"]]
        item["status"] = kwargs["status"]
        item["reference_id"] = kwargs["reference_id"]
        return item

    class FakeFIUIndService:
        def __init__(self, api_url: str, mtls_cert_path: str, mtls_key_path: str):
            self.api_url = api_url
            self.mtls_cert_path = mtls_cert_path
            self.mtls_key_path = mtls_key_path

        async def submit_str(self, str_xml: str, digital_signature: str):
            return {"reference_id": "FIU-E2E-1"}

    monkeypatch.setattr(reports.neo4j_service, "get_alert_by_id", fake_get_alert_by_id)
    monkeypatch.setattr(
        reports.neo4j_service, "get_account_subgraph", fake_get_account_subgraph
    )
    monkeypatch.setattr(reports.neo4j_service, "get_transaction", fake_get_transaction)
    monkeypatch.setattr(
        reports.llm_service, "generate_str_narrative", fake_generate_str_narrative
    )
    monkeypatch.setattr(reports.neo4j_service, "create_str_report", fake_create_str_report)
    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "update_str_review", fake_update_str_review)
    monkeypatch.setattr(reports.neo4j_service, "submit_str_report", fake_submit_str_report)
    monkeypatch.setattr(reports, "FIUIndService", FakeFIUIndService)
    monkeypatch.setattr(reports.settings, "DEMO_MODE", False)
    monkeypatch.setattr(reports.settings, "FIU_IND_API_URL", "https://fiu.example")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_CERT_PATH", "cert.pem")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_KEY_PATH", "key.pem")

    with TestClient(app) as client:
        generate_response = client.post(
            "/api/v1/reports/str/generate",
            json={"alert_id": "ALT-E2E-1", "case_notes": "workflow"},
        )
        assert generate_response.status_code == 200
        str_id = generate_response.json()["str_id"]

        approve_response = client.post(
            f"/api/v1/reports/str/{str_id}/approve",
            headers=_headers("checker-1", "SUPERVISOR"),
            json={"notes": "approved"},
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "APPROVED"

        submit_response = client.post(
            f"/api/v1/reports/str/{str_id}/submit",
            json={
                "str_id": str_id,
                "edited_narrative": "final narrative",
                "digital_signature": "sig-e2e",
            },
        )

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"
    assert store[str_id]["status"] == "SUBMITTED"
    assert store[str_id]["reference_id"] == "FIU-E2E-1"


def test_enforcement_create_approve_workflow_persists_accepted(monkeypatch):
    actions = {}

    async def fake_create_enforcement_action(**kwargs):
        actions[kwargs["action_id"]] = {
            "id": kwargs["action_id"],
            "status": kwargs["status"],
            "action_type": kwargs["action_type"],
            "account_id": kwargs.get("account_id", ""),
            "reason": kwargs.get("reason", ""),
            "metadata": kwargs.get("metadata", {}),
        }
        return actions[kwargs["action_id"]]

    async def fake_get_enforcement_action(action_id: str):
        return actions.get(action_id)

    async def fake_update_enforcement_action_status(**kwargs):
        item = actions[kwargs["action_id"]]
        item["status"] = kwargs["status"]
        item["reviewed_by"] = kwargs["reviewed_by"]
        item["review_notes"] = kwargs["review_notes"]
        item["metadata"] = kwargs.get("metadata", item.get("metadata", {}))
        return item

    class FakeFinacleService:
        def __init__(self, api_url: str, client_id: str, client_secret: str):
            self.api_url = api_url
            self.client_id = client_id
            self.client_secret = client_secret

        async def mark_lien(self, account_id: str, amount: float, reason: str):
            return {"ticket": "FIN-E2E-1"}

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "create_enforcement_action",
        fake_create_enforcement_action,
    )
    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )
    monkeypatch.setattr(
        enforcement.neo4j_service,
        "update_enforcement_action_status",
        fake_update_enforcement_action_status,
    )
    monkeypatch.setattr(enforcement, "FinacleService", FakeFinacleService)
    monkeypatch.setattr(enforcement.settings, "FINACLE_API_URL", "https://fin.example")
    monkeypatch.setattr(enforcement.settings, "FINACLE_CLIENT_ID", "cid")
    monkeypatch.setattr(enforcement.settings, "FINACLE_CLIENT_SECRET", "secret")

    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/enforcement/lien",
            headers=_headers("maker-1", "SUPERVISOR"),
            json={
                "accountId": "ACC-E2E-2",
                "reason": "workflow test",
                "alertId": "ALT-E2E-2",
                "amount": 10000,
                "initiatedBy": "maker-1",
                "requiresMakerChecker": True,
            },
        )
        assert create_response.status_code == 200
        action_id = create_response.json()["lienId"]

        approve_response = client.post(
            f"/api/v1/enforcement/actions/{action_id}/approve",
            headers=_headers("checker-2", "COMPLIANCE_OFFICER"),
            json={"notes": "approved"},
        )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "ACCEPTED"
    assert actions[action_id]["status"] == "ACCEPTED"
    assert actions[action_id]["reviewed_by"] == "checker-2"


def test_enforcement_create_reject_workflow_persists_rejected(monkeypatch):
    actions = {}

    async def fake_create_enforcement_action(**kwargs):
        actions[kwargs["action_id"]] = {
            "id": kwargs["action_id"],
            "status": kwargs["status"],
            "action_type": kwargs["action_type"],
            "account_id": kwargs.get("account_id", ""),
            "reason": kwargs.get("reason", ""),
            "metadata": kwargs.get("metadata", {}),
        }
        return actions[kwargs["action_id"]]

    async def fake_get_enforcement_action(action_id: str):
        return actions.get(action_id)

    async def fake_update_enforcement_action_status(**kwargs):
        item = actions[kwargs["action_id"]]
        item["status"] = kwargs["status"]
        item["reviewed_by"] = kwargs["reviewed_by"]
        item["review_notes"] = kwargs["review_notes"]
        item["metadata"] = kwargs.get("metadata", item.get("metadata", {}))
        return item

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "create_enforcement_action",
        fake_create_enforcement_action,
    )
    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )
    monkeypatch.setattr(
        enforcement.neo4j_service,
        "update_enforcement_action_status",
        fake_update_enforcement_action_status,
    )

    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/enforcement/freeze",
            headers=_headers("maker-2", "SUPERVISOR"),
            json={
                "accountId": "ACC-E2E-3",
                "reason": "workflow reject",
                "caseId": "CASE-E2E-1",
                "initiatedBy": "maker-2",
                "requiresMakerChecker": True,
            },
        )
        assert create_response.status_code == 200
        action_id = create_response.json()["freezeId"]

        reject_response = client.post(
            f"/api/v1/enforcement/actions/{action_id}/reject",
            headers=_headers("checker-3", "COMPLIANCE_OFFICER"),
            json={"notes": "rejected"},
        )

    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "REJECTED"
    assert actions[action_id]["status"] == "REJECTED"
    assert actions[action_id]["reviewed_by"] == "checker-3"
