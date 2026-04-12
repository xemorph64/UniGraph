import asyncio

from fastapi import HTTPException

from backend.app.auth.jwt_rbac import User
from backend.app.routers import accounts, enforcement, reports


def test_accounts_timeline_uses_service(monkeypatch):
    async def fake_get_account_timeline(account_id: str, days: int):
        return {
            "account_id": account_id,
            "days": days,
            "source": "neo4j_fallback",
            "timeline": [{"day": "2026-04-10", "risk_score": 72.4}],
        }

    monkeypatch.setattr(
        accounts.timeline_service,
        "get_account_timeline",
        fake_get_account_timeline,
    )

    response = asyncio.run(accounts.get_account_timeline("ACC-900", 30))

    assert response["account_id"] == "ACC-900"
    assert response["source"] == "neo4j_fallback"
    assert response["timeline"][0]["risk_score"] == 72.4


def test_list_str_reports_route(monkeypatch):
    captured = {}

    async def fake_list_str_reports(**kwargs):
        captured.update(kwargs)
        return {
            "items": [{"id": "STR-1", "status": "DRAFT", "account_id": "ACC-1"}],
            "total": 1,
        }

    monkeypatch.setattr(reports.neo4j_service, "list_str_reports", fake_list_str_reports)

    response = asyncio.run(
        reports.list_str_reports(page=1, page_size=25, status="draft", account_id="ACC-1")
    )

    assert response["total"] == 1
    assert response["items"][0]["id"] == "STR-1"
    assert captured["status"] == "DRAFT"
    assert captured["account_id"] == "ACC-1"


def test_get_enforcement_action_not_found(monkeypatch):
    async def fake_get_enforcement_action(action_id: str):
        return None

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "get_enforcement_action",
        fake_get_enforcement_action,
    )

    try:
        asyncio.run(
            enforcement.get_enforcement_action(
                "EA-404",
                user=User(user_id="u1", username="u1", role="ADMIN"),
            )
        )
    except HTTPException as ex:
        assert ex.status_code == 404
        assert ex.detail == "Enforcement action not found"
    else:
        assert False, "Expected HTTPException"


def test_list_enforcement_actions_route(monkeypatch):
    captured = {}

    async def fake_list_enforcement_actions(**kwargs):
        captured.update(kwargs)
        return {
            "items": [{"id": "LIEN-1", "action_type": "LIEN", "status": "PENDING_APPROVAL"}],
            "total": 1,
        }

    monkeypatch.setattr(
        enforcement.neo4j_service,
        "list_enforcement_actions",
        fake_list_enforcement_actions,
    )

    response = asyncio.run(
        enforcement.list_enforcement_actions(
            page=1,
            page_size=20,
            action_type="lien",
            status="pending_approval",
            account_id="ACC-11",
            user=User(user_id="sup-1", username="sup1", role="ADMIN"),
        )
    )

    assert response["total"] == 1
    assert response["items"][0]["action_type"] == "LIEN"
    assert captured["action_type"] == "LIEN"
    assert captured["status"] == "PENDING_APPROVAL"
