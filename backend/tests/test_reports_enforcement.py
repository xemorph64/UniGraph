import asyncio

import pytest

from backend.app.auth.jwt_rbac import User
from backend.app.routers import enforcement, reports


def test_generate_str_creates_persisted_draft(monkeypatch):
    created_payload = {}
    captured_case_data = {}

    async def fake_get_alert_by_id(alert_id: str):
        return {
            "id": alert_id,
            "account_id": "ACC-1001",
            "transaction_id": "TXN-1001",
            "risk_score": 88.5,
            "risk_level": "HIGH",
            "rule_flags": ["STRUCTURING"],
            "shap_top3": ["velocity_1h", "device_account_count", "amount"],
        }

    async def fake_get_account_subgraph(account_id: str, hops: int = 2):
        return {"nodes": [{"id": account_id}], "edges": []}

    async def fake_generate_str_narrative(case_data: dict):
        captured_case_data.update(case_data)
        return f"Narrative for {case_data['account_id']}"

    async def fake_get_transaction(txn_id: str):
        return {
            "txn_id": txn_id,
            "amount": 49000,
            "channel": "UPI",
            "from_account": "ACC-1001",
            "to_account": "ACC-2002",
            "timestamp": "2026-03-06T10:23:00Z",
            "scoring_source": "ml_blended",
            "model_version": "test-model-v1",
        }

    async def fake_create_str_report(**kwargs):
        created_payload.update(kwargs)
        return kwargs

    monkeypatch.setattr(reports.neo4j_service, "get_alert_by_id", fake_get_alert_by_id)
    monkeypatch.setattr(
        reports.neo4j_service, "get_account_subgraph", fake_get_account_subgraph
    )
    monkeypatch.setattr(reports.neo4j_service, "get_transaction", fake_get_transaction)
    monkeypatch.setattr(
        reports.llm_service, "generate_str_narrative", fake_generate_str_narrative
    )
    monkeypatch.setattr(reports.neo4j_service, "create_str_report", fake_create_str_report)

    response = asyncio.run(
        reports.generate_str(
            reports.STRGenerateRequest(alert_id="ALT-100", case_notes="reviewed")
        )
    )

    assert response.str_id == "STR-ALT-100"
    assert response.account_id == "ACC-1001"
    assert "Narrative for ACC-1001" in response.narrative
    assert created_payload["str_id"] == "STR-ALT-100"
    assert created_payload["alert_id"] == "ALT-100"
    assert captured_case_data["case_notes"] == "reviewed"
    assert "txn_id=TXN-1001" in captured_case_data["transaction_snapshot"]


def test_submit_str_falls_back_to_demo_without_fiu_config(monkeypatch):
    persisted = {}

    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "DRAFT"}

    async def fake_submit_str_report(**kwargs):
        persisted.update(kwargs)
        return kwargs

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "submit_str_report", fake_submit_str_report)
    monkeypatch.setattr(reports.settings, "DEMO_MODE", True)
    monkeypatch.setattr(reports.settings, "FIU_IND_API_URL", "")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_CERT_PATH", "")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_KEY_PATH", "")

    response = asyncio.run(
        reports.submit_str(
            "STR-ALT-100",
            reports.STRSubmitRequest(
                str_id="STR-ALT-100",
                edited_narrative="edited narrative",
                digital_signature="digital-signature",
            ),
        )
    )

    assert response["status"] == "submitted-demo"
    assert response["reference_id"].startswith("DEMO-")
    assert persisted["status"] == "SUBMITTED-DEMO"


def test_mark_lien_pending_approval_persists_action(monkeypatch):
    persisted = {}

    async def fake_create_enforcement_action(**kwargs):
        persisted.update(kwargs)
        return kwargs

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "create_enforcement_action",
        fake_create_enforcement_action,
    )

    response = asyncio.run(
        enforcement.mark_lien(
            enforcement.LienRequest(
                accountId="ACC-200",
                reason="Fraud ring linkage",
                alertId="ALT-200",
                amount=50000,
                initiatedBy="investigator-1",
                requiresMakerChecker=True,
            ),
            user=User(user_id="investigator-1", username="inv1", role="ADMIN"),
        )
    )

    assert response["status"] == "PENDING_APPROVAL"
    assert response["lienId"].startswith("LIEN-")
    assert persisted["action_type"] == "LIEN"
    assert persisted["account_id"] == "ACC-200"


def test_submit_ncrp_demo_without_provider_config(monkeypatch):
    persisted = {}

    async def fake_create_enforcement_action(**kwargs):
        persisted.update(kwargs)
        return kwargs

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "create_enforcement_action",
        fake_create_enforcement_action,
    )
    monkeypatch.setattr(enforcement.settings, "NCRP_API_URL", "")
    monkeypatch.setattr(enforcement.settings, "NCRP_API_KEY", "")

    response = asyncio.run(
        enforcement.submit_ncrp_report(
            enforcement.NCRPReportRequest(
                complaintId="NCRP-100",
                accountId="ACC-300",
                action="AUTO_LIEN",
                evidence={"txn_ids": ["TXN-1"]},
            ),
            user=User(user_id="compliance-1", username="co1", role="ADMIN"),
        )
    )

    assert response["status"] == "submitted-demo"
    assert persisted["action_type"] == "NCRP_REPORT"
    assert persisted["reference_id"] == "NCRP-100"


def test_approve_str_updates_review_status(monkeypatch):
    captured = {}

    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "DRAFT"}

    async def fake_update_str_review(**kwargs):
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "update_str_review", fake_update_str_review)

    response = asyncio.run(
        reports.approve_str(
            "STR-ALT-77",
            reports.STRReviewRequest(notes="checker ok"),
            user=User(user_id="sup-22", username="sup", role="ADMIN"),
        )
    )

    assert response["status"] == "APPROVED"
    assert captured["status"] == "APPROVED"
    assert captured["reviewed_by"] == "sup-22"


def test_approve_enforcement_action_demo_transition(monkeypatch):
    captured = {}

    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "LIEN",
            "account_id": "ACC-400",
            "reason": "rule hit",
            "metadata": {"amount": 7500.0},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        captured.update(kwargs)
        return kwargs

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
    monkeypatch.setattr(enforcement.settings, "FINACLE_API_URL", "")
    monkeypatch.setattr(enforcement.settings, "FINACLE_CLIENT_ID", "")
    monkeypatch.setattr(enforcement.settings, "FINACLE_CLIENT_SECRET", "")

    response = asyncio.run(
        enforcement.approve_enforcement_action(
            "LIEN-100",
            enforcement.EnforcementReviewRequest(notes="approved by checker"),
            user=User(user_id="checker-1", username="checker", role="ADMIN"),
        )
    )

    assert response["status"] == "APPROVED_DEMO"
    assert captured["status"] == "APPROVED_DEMO"
    assert captured["reviewed_by"] == "checker-1"


def test_reject_enforcement_action_sets_rejected(monkeypatch):
    captured = {}

    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "FREEZE",
            "metadata": {},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        captured.update(kwargs)
        return kwargs

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

    response = asyncio.run(
        enforcement.reject_enforcement_action(
            "FRZ-44",
            enforcement.EnforcementReviewRequest(notes="insufficient evidence"),
            user=User(user_id="checker-2", username="checker2", role="ADMIN"),
        )
    )

    assert response["status"] == "REJECTED"
    assert captured["status"] == "REJECTED"
    assert captured["reviewed_by"] == "checker-2"


def test_approve_str_returns_404_when_missing(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return None

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)

    with pytest.raises(reports.HTTPException) as exc:
        asyncio.run(
            reports.approve_str(
                "STR-MISSING",
                reports.STRReviewRequest(notes="irrelevant"),
                user=User(user_id="checker-404", username="checker", role="ADMIN"),
            )
        )

    assert exc.value.status_code == 404


def test_reject_str_returns_409_for_submitted_status(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "SUBMITTED"}

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)

    with pytest.raises(reports.HTTPException) as exc:
        asyncio.run(
            reports.reject_str(
                "STR-SUB-1",
                reports.STRReviewRequest(notes="late rejection"),
                user=User(user_id="checker-409", username="checker", role="ADMIN"),
            )
        )

    assert exc.value.status_code == 409


def test_approve_enforcement_action_returns_404_when_missing(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return None

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    with pytest.raises(enforcement.HTTPException) as exc:
        asyncio.run(
            enforcement.approve_enforcement_action(
                "ACT-MISSING",
                enforcement.EnforcementReviewRequest(notes="irrelevant"),
                user=User(user_id="checker-404", username="checker", role="ADMIN"),
            )
        )

    assert exc.value.status_code == 404


def test_reject_enforcement_action_returns_409_for_invalid_state(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "ACCEPTED",
            "action_type": "LIEN",
            "metadata": {},
        }

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    with pytest.raises(enforcement.HTTPException) as exc:
        asyncio.run(
            enforcement.reject_enforcement_action(
                "ACT-DONE",
                enforcement.EnforcementReviewRequest(notes="cannot reject now"),
                user=User(user_id="checker-409", username="checker", role="ADMIN"),
            )
        )

    assert exc.value.status_code == 409


def test_approve_str_returns_409_for_submitted_status(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "SUBMITTED-DEMO"}

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)

    with pytest.raises(reports.HTTPException) as exc:
        asyncio.run(
            reports.approve_str(
                "STR-SUB-2",
                reports.STRReviewRequest(notes="late approval"),
                user=User(user_id="checker-410", username="checker", role="ADMIN"),
            )
        )

    assert exc.value.status_code == 409


def test_reject_str_returns_404_when_missing(monkeypatch):
    async def fake_get_str_report(str_id: str):
        return None

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)

    with pytest.raises(reports.HTTPException) as exc:
        asyncio.run(
            reports.reject_str(
                "STR-404-2",
                reports.STRReviewRequest(notes="missing str"),
                user=User(user_id="checker-411", username="checker", role="ADMIN"),
            )
        )

    assert exc.value.status_code == 404


def test_approve_enforcement_action_returns_409_for_invalid_state(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "REJECTED",
            "action_type": "FREEZE",
            "metadata": {},
        }

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    with pytest.raises(enforcement.HTTPException) as exc:
        asyncio.run(
            enforcement.approve_enforcement_action(
                "ACT-STATE",
                enforcement.EnforcementReviewRequest(notes="cannot approve now"),
                user=User(user_id="checker-412", username="checker", role="ADMIN"),
            )
        )

    assert exc.value.status_code == 409


def test_reject_enforcement_action_returns_404_when_missing(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return None

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    with pytest.raises(enforcement.HTTPException) as exc:
        asyncio.run(
            enforcement.reject_enforcement_action(
                "ACT-404-2",
                enforcement.EnforcementReviewRequest(notes="missing action"),
                user=User(user_id="checker-413", username="checker", role="ADMIN"),
            )
        )

    assert exc.value.status_code == 404


def test_submit_str_provider_configured_returns_submitted(monkeypatch):
    persisted = {}

    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "APPROVED"}

    async def fake_submit_str_report(**kwargs):
        persisted.update(kwargs)
        return kwargs

    class FakeFIUIndService:
        def __init__(self, api_url: str, mtls_cert_path: str, mtls_key_path: str):
            self.api_url = api_url
            self.mtls_cert_path = mtls_cert_path
            self.mtls_key_path = mtls_key_path

        async def submit_str(self, str_xml: str, digital_signature: str):
            return {"reference_id": "FIU-REF-001"}

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "submit_str_report", fake_submit_str_report)
    monkeypatch.setattr(reports, "FIUIndService", FakeFIUIndService)
    monkeypatch.setattr(reports.settings, "FIU_IND_API_URL", "https://fiu.example")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_CERT_PATH", "cert.pem")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_KEY_PATH", "key.pem")

    response = asyncio.run(
        reports.submit_str(
            "STR-FIU-1",
            reports.STRSubmitRequest(
                str_id="STR-FIU-1",
                edited_narrative="signed payload",
                digital_signature="sig-1",
            ),
        )
    )

    assert response["status"] == "submitted"
    assert response["reference_id"] == "FIU-REF-001"
    assert persisted["status"] == "SUBMITTED"


def test_submit_str_provider_configured_returns_queued_on_empty_response(monkeypatch):
    persisted = {}

    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "APPROVED"}

    async def fake_submit_str_report(**kwargs):
        persisted.update(kwargs)
        return kwargs

    class FakeFIUIndService:
        def __init__(self, api_url: str, mtls_cert_path: str, mtls_key_path: str):
            self.api_url = api_url
            self.mtls_cert_path = mtls_cert_path
            self.mtls_key_path = mtls_key_path

        async def submit_str(self, str_xml: str, digital_signature: str):
            return {}

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "submit_str_report", fake_submit_str_report)
    monkeypatch.setattr(reports, "FIUIndService", FakeFIUIndService)
    monkeypatch.setattr(reports.settings, "FIU_IND_API_URL", "https://fiu.example")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_CERT_PATH", "cert.pem")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_KEY_PATH", "key.pem")

    response = asyncio.run(
        reports.submit_str(
            "STR-FIU-2",
            reports.STRSubmitRequest(
                str_id="STR-FIU-2",
                edited_narrative="signed payload",
                digital_signature="sig-2",
            ),
        )
    )

    assert response["status"] == "queued"
    assert persisted["status"] == "QUEUED"


def test_approve_enforcement_action_finacle_lien_returns_accepted(monkeypatch):
    captured = {}

    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "LIEN",
            "account_id": "ACC-501",
            "reason": "manual escalation",
            "metadata": {"amount": 4500.0},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        captured.update(kwargs)
        return kwargs

    class FakeFinacleService:
        def __init__(self, api_url: str, client_id: str, client_secret: str):
            self.api_url = api_url
            self.client_id = client_id
            self.client_secret = client_secret

        async def mark_lien(self, account_id: str, amount: float, reason: str):
            return {"ticket": "FIN-OK-1"}

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

    response = asyncio.run(
        enforcement.approve_enforcement_action(
            "EA-FIN-1",
            enforcement.EnforcementReviewRequest(notes="ok"),
            user=User(user_id="checker-fin", username="checker", role="ADMIN"),
        )
    )

    assert response["status"] == "ACCEPTED"
    assert captured["status"] == "ACCEPTED"


def test_approve_enforcement_action_ncrp_returns_submitted(monkeypatch):
    captured = {}

    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "NCRP_REPORT",
            "account_id": "ACC-601",
            "reference_id": "NCRP-C-900",
            "reason": "AUTO_FREEZE",
            "metadata": {"evidence": {"txn_ids": ["TXN-9"]}},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        captured.update(kwargs)
        return kwargs

    class FakeNCRPService:
        def __init__(self, api_url: str, api_key: str):
            self.api_url = api_url
            self.api_key = api_key

        async def submit_complaint(self, payload: dict):
            return {"receipt": "NCRP-ACK-1"}

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
    monkeypatch.setattr(enforcement, "NCRPService", FakeNCRPService)
    monkeypatch.setattr(enforcement.settings, "NCRP_API_URL", "https://ncrp.example")
    monkeypatch.setattr(enforcement.settings, "NCRP_API_KEY", "k")

    response = asyncio.run(
        enforcement.approve_enforcement_action(
            "EA-NCRP-1",
            enforcement.EnforcementReviewRequest(notes="ok"),
            user=User(user_id="checker-ncrp", username="checker", role="ADMIN"),
        )
    )

    assert response["status"] == "SUBMITTED"
    assert captured["status"] == "SUBMITTED"


def test_approve_enforcement_action_ncrp_returns_queued_on_empty_response(monkeypatch):
    captured = {}

    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "NCRP_REPORT",
            "account_id": "ACC-602",
            "reference_id": "NCRP-C-901",
            "reason": "AUTO_LIEN",
            "metadata": {"evidence": {"txn_ids": ["TXN-10"]}},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        captured.update(kwargs)
        return kwargs

    class FakeNCRPService:
        def __init__(self, api_url: str, api_key: str):
            self.api_url = api_url
            self.api_key = api_key

        async def submit_complaint(self, payload: dict):
            return {}

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
    monkeypatch.setattr(enforcement, "NCRPService", FakeNCRPService)
    monkeypatch.setattr(enforcement.settings, "NCRP_API_URL", "https://ncrp.example")
    monkeypatch.setattr(enforcement.settings, "NCRP_API_KEY", "k")

    response = asyncio.run(
        enforcement.approve_enforcement_action(
            "EA-NCRP-2",
            enforcement.EnforcementReviewRequest(notes="ok"),
            user=User(user_id="checker-ncrp", username="checker", role="ADMIN"),
        )
    )

    assert response["status"] == "QUEUED"
    assert captured["status"] == "QUEUED"


def test_submit_str_provider_exception_returns_queued(monkeypatch):
    persisted = {}

    async def fake_get_str_report(str_id: str):
        return {"id": str_id, "status": "APPROVED"}

    async def fake_submit_str_report(**kwargs):
        persisted.update(kwargs)
        return kwargs

    class FakeFIUIndService:
        def __init__(self, api_url: str, mtls_cert_path: str, mtls_key_path: str):
            self.api_url = api_url
            self.mtls_cert_path = mtls_cert_path
            self.mtls_key_path = mtls_key_path

        async def submit_str(self, str_xml: str, digital_signature: str):
            raise RuntimeError("fiu unavailable")

    monkeypatch.setattr(reports.neo4j_service, "get_str_report", fake_get_str_report)
    monkeypatch.setattr(reports.neo4j_service, "submit_str_report", fake_submit_str_report)
    monkeypatch.setattr(reports, "FIUIndService", FakeFIUIndService)
    monkeypatch.setattr(reports.settings, "FIU_IND_API_URL", "https://fiu.example")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_CERT_PATH", "cert.pem")
    monkeypatch.setattr(reports.settings, "FIU_IND_MTLS_KEY_PATH", "key.pem")

    response = asyncio.run(
        reports.submit_str(
            "STR-FIU-3",
            reports.STRSubmitRequest(
                str_id="STR-FIU-3",
                edited_narrative="signed payload",
                digital_signature="sig-3",
            ),
        )
    )

    assert response["status"] == "queued"
    assert persisted["status"] == "QUEUED"


def test_approve_enforcement_action_finacle_exception_returns_rejected(monkeypatch):
    captured = {}

    async def fake_get_enforcement_action(action_id: str):
        return {
            "id": action_id,
            "status": "PENDING_APPROVAL",
            "action_type": "LIEN",
            "account_id": "ACC-701",
            "reason": "manual escalation",
            "metadata": {"amount": 5500.0},
        }

    async def fake_update_enforcement_action_status(**kwargs):
        captured.update(kwargs)
        return kwargs

    class FakeFinacleService:
        def __init__(self, api_url: str, client_id: str, client_secret: str):
            self.api_url = api_url
            self.client_id = client_id
            self.client_secret = client_secret

        async def mark_lien(self, account_id: str, amount: float, reason: str):
            raise RuntimeError("finacle unavailable")

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

    response = asyncio.run(
        enforcement.approve_enforcement_action(
            "EA-FIN-2",
            enforcement.EnforcementReviewRequest(notes="ok"),
            user=User(user_id="checker-fin", username="checker", role="ADMIN"),
        )
    )

    assert response["status"] == "REJECTED"
    assert captured["status"] == "REJECTED"


def test_submit_ncrp_provider_exception_returns_queued(monkeypatch):
    persisted = {}

    async def fake_create_enforcement_action(**kwargs):
        persisted.update(kwargs)
        return kwargs

    class FakeNCRPService:
        def __init__(self, api_url: str, api_key: str):
            self.api_url = api_url
            self.api_key = api_key

        async def submit_complaint(self, payload: dict):
            raise RuntimeError("ncrp unavailable")

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "create_enforcement_action",
        fake_create_enforcement_action,
    )
    monkeypatch.setattr(enforcement, "NCRPService", FakeNCRPService)
    monkeypatch.setattr(enforcement.settings, "NCRP_API_URL", "https://ncrp.example")
    monkeypatch.setattr(enforcement.settings, "NCRP_API_KEY", "k")

    response = asyncio.run(
        enforcement.submit_ncrp_report(
            enforcement.NCRPReportRequest(
                complaintId="NCRP-ERR-1",
                accountId="ACC-801",
                action="AUTO_FREEZE",
                evidence={"txn_ids": ["TXN-11"]},
            ),
            user=User(user_id="compliance-1", username="co1", role="ADMIN"),
        )
    )

    assert response["status"] == "queued"
    assert persisted["status"] == "QUEUED"
