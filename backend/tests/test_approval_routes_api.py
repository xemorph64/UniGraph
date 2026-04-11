import pytest
from fastapi.testclient import TestClient

from backend.app.auth.jwt_rbac import User, create_access_token
from backend.app.config import settings
from backend.app.main import app
from backend.app.routers import enforcement, reports


def _auth_headers(user_id: str, role: str) -> dict:
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


def test_reports_approve_str_404_body(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return None

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/str/STR-404/approve",
            headers=_auth_headers("admin-1", "ADMIN"),
            json={"notes": "missing report"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "STR not found"}


def test_reports_approve_str_409_body(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "SUBMITTED"}

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/str/STR-1/approve",
            headers=_auth_headers("admin-1", "ADMIN"),
            json={"notes": "cannot approve now"},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Submitted STR cannot be re-approved"}


def test_reports_reject_str_404_body(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return None

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/str/STR-404/reject",
            headers=_auth_headers("admin-1", "ADMIN"),
            json={"notes": "missing report"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "STR not found"}


def test_reports_reject_str_409_body(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "SUBMITTED-DEMO"}

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/str/STR-2/reject",
            headers=_auth_headers("admin-1", "ADMIN"),
            json={"notes": "cannot reject now"},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Submitted STR cannot be rejected"}


def test_enforcement_approve_404_body(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return None

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/enforcement/actions/ACT-404/approve",
            headers=_auth_headers("admin-1", "ADMIN"),
            json={"notes": "missing action"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Enforcement action not found"}


def test_enforcement_approve_409_body(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "APPROVED_DEMO",
            "action_type": "LIEN",
            "metadata": {},
        }

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/enforcement/actions/ACT-1/approve",
            headers=_auth_headers("admin-1", "ADMIN"),
            json={"notes": "invalid state"},
        )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Action cannot be approved from status APPROVED_DEMO"
    )


def test_enforcement_reject_404_body(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return None

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/enforcement/actions/ACT-404/reject",
            headers=_auth_headers("admin-1", "ADMIN"),
            json={"notes": "missing action"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Enforcement action not found"}


def test_enforcement_reject_409_body(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "ACCEPTED",
            "action_type": "FREEZE",
            "metadata": {},
        }

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/enforcement/actions/ACT-2/reject",
            headers=_auth_headers("admin-1", "ADMIN"),
            json={"notes": "invalid state"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Action cannot be rejected from status ACCEPTED"


def test_demo_reset_endpoint_disabled_in_non_demo_mode():
    with TestClient(app) as client:
        response = client.get("/api/v1/demo/reset")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


def test_reports_approve_str_success_body(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "DRAFT"}

    async def fake_update_str_review(**kwargs):
        return {
            "id": kwargs["str_id"],
            "status": kwargs["status"],
            "reviewed_by": kwargs["reviewed_by"],
            "review_notes": kwargs["review_notes"],
        }

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "update_str_review", fake_update_str_review)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/str/STR-OK-1/approve",
            headers=_auth_headers("sup-1", "SUPERVISOR"),
            json={"notes": "looks valid"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["str_id"] == "STR-OK-1"
    assert body["status"] == "APPROVED"
    assert body["review"]["reviewed_by"] == "sup-1"


def test_reports_reject_str_success_body(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "DRAFT"}

    async def fake_update_str_review(**kwargs):
        return {
            "id": kwargs["str_id"],
            "status": kwargs["status"],
            "reviewed_by": kwargs["reviewed_by"],
            "review_notes": kwargs["review_notes"],
        }

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "update_str_review", fake_update_str_review)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/str/STR-OK-2/reject",
            headers=_auth_headers("co-1", "COMPLIANCE_OFFICER"),
            json={"notes": "missing evidence"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["str_id"] == "STR-OK-2"
    assert body["status"] == "REJECTED"
    assert body["review"]["reviewed_by"] == "co-1"


def test_enforcement_approve_success_body(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "LIEN",
            "account_id": "ACC-77",
            "reason": "risk threshold",
            "metadata": {"amount": 2000.0},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        return {
            "id": kwargs["action_id"],
            "status": kwargs["status"],
            "reviewed_by": kwargs["reviewed_by"],
            "metadata": kwargs.get("metadata", {}),
        }

    class FakeFinacleService:
        def __init__(self, api_url: str, client_id: str, client_secret: str):
            self.api_url = api_url
            self.client_id = client_id
            self.client_secret = client_secret

        async def mark_lien(self, account_id: str, amount: float, reason: str):
            return {"ticket": "FIN-ROUTE-1"}

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

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/enforcement/actions/EA-OK-1/approve",
            headers=_auth_headers("sup-2", "SUPERVISOR"),
            json={"notes": "approved"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["action_id"] == "EA-OK-1"
    assert body["status"] == "ACCEPTED"
    assert body["action"]["reviewed_by"] == "sup-2"


def test_enforcement_reject_success_body(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "FREEZE",
            "account_id": "ACC-88",
            "reason": "case-driven",
            "metadata": {},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        return {
            "id": kwargs["action_id"],
            "status": kwargs["status"],
            "reviewed_by": kwargs["reviewed_by"],
            "metadata": kwargs.get("metadata", {}),
        }

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
        response = client.post(
            "/api/v1/enforcement/actions/EA-OK-2/reject",
            headers=_auth_headers("co-2", "COMPLIANCE_OFFICER"),
            json={"notes": "rejecting"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["action_id"] == "EA-OK-2"
    assert body["status"] == "REJECTED"
    assert body["action"]["reviewed_by"] == "co-2"


@pytest.mark.parametrize(
    "role,expected_status",
    [
        ("SUPERVISOR", 200),
        ("COMPLIANCE_OFFICER", 200),
        ("INVESTIGATOR", 403),
    ],
)
def test_permission_matrix_approve_str(monkeypatch, role: str, expected_status: int):
    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "DRAFT"}

    async def fake_update_str_review(**kwargs):
        return kwargs

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "update_str_review", fake_update_str_review)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reports/str/STR-RBAC/approve",
            headers=_auth_headers(f"user-{role.lower()}", role),
            json={"notes": "rbac check"},
        )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "role,expected_status",
    [
        ("SUPERVISOR", 200),
        ("COMPLIANCE_OFFICER", 200),
        ("INVESTIGATOR", 403),
    ],
)
def test_permission_matrix_approve_enforcement(
    monkeypatch, role: str, expected_status: int
):
    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "LIEN",
            "account_id": "ACC-RBAC",
            "reason": "rbac",
            "metadata": {"amount": 1000.0},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        return kwargs

    class FakeFinacleService:
        def __init__(self, api_url: str, client_id: str, client_secret: str):
            self.api_url = api_url
            self.client_id = client_id
            self.client_secret = client_secret

        async def mark_lien(self, account_id: str, amount: float, reason: str):
            return {"ticket": "FIN-RBAC-1"}

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

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/enforcement/actions/EA-RBAC/approve",
            headers=_auth_headers(f"user-{role.lower()}", role),
            json={"notes": "rbac check"},
        )

    assert response.status_code == expected_status
