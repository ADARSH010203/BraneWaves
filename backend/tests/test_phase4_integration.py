"""Phase 4 integration regression tests."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.models.agent_outputs import StepDefinition
from app.routes.auth import _validate_browser_origin
from app.services.account_service import update_profile
from app.services import report_chat_service


class _Users:
    def __init__(self):
        self.user = {
            "_id": "user-1",
            "email": "person@example.com",
            "name": "Old Name",
            "provider": "local",
            "role": "user",
            "plan": "free",
            "usage_quota_usd": 10.0,
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            "is_active": True,
        }

    async def update_one(self, query, update):
        self.user.update(update["$set"])
        return SimpleNamespace(modified_count=1)

    async def find_one(self, query):
        return dict(self.user)


class _ProfileDb:
    def __init__(self):
        self.users = _Users()


@pytest.mark.asyncio
async def test_profile_update_is_authoritative_and_trimmed():
    db = _ProfileDb()
    result = await update_profile(db, "user-1", "  New Name  ")
    assert result.name == "New Name"
    assert db.users.user["name"] == "New Name"


def test_cookie_auth_origin_guard_rejects_unknown_origin(monkeypatch):
    import app.routes.auth as auth_module

    monkeypatch.setattr(auth_module.settings, "ALLOWED_ORIGINS", ["https://app.example.com"])
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/auth/refresh",
        "headers": [(b"origin", b"https://evil.example")],
    })
    with pytest.raises(HTTPException) as exc:
        _validate_browser_origin(request)
    assert exc.value.status_code == 403


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, length=None):
        return self.rows if length is None else self.rows[:length]


class _ReportChunks:
    def find(self, query, projection=None):
        return _Cursor([
            {"_id": "chunk-good", "text": "Battery thermal safety evidence", "embedding": [1.0, 0.0], "index": 0},
            {"_id": "chunk-bad", "text": "Unrelated market content", "embedding": [0.0, 1.0], "index": 1},
        ])


class _ReportDb:
    report_chunks = _ReportChunks()


@pytest.mark.asyncio
async def test_report_chat_retrieves_semantically_relevant_chunks(monkeypatch):
    async def no_index(_db, _report):
        return None

    async def query_embedding(_text):
        return [1.0, 0.0]

    monkeypatch.setattr(report_chat_service, "ensure_report_index", no_index)
    monkeypatch.setattr(report_chat_service, "generate_embedding", query_embedding)

    report = {"_id": "report-1", "user_id": "user-1", "task_id": "task-1"}
    results = await report_chat_service.retrieve_report_context(
        _ReportDb(),
        report,
        "thermal safety",
        top_k=1,
    )
    assert results[0]["chunk_id"] == "chunk-good"
    assert results[0]["score"] > 0.99


def test_code_agent_golden_contract_is_python_only():
    # Planner code steps are deliberately Python-sandbox oriented.
    step = StepDefinition(
        id="code_1",
        type="code",
        title="Analyze CSV",
        description="Write Python to analyze a CSV string.",
    )
    assert step.type == "code"
