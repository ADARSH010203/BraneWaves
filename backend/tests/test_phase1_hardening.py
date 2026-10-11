"""Regression tests for Phase 1 correctness and security hardening."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.deps import get_current_user
from app.security.jwt_handler import create_access_token
from app.services.auth_service import oauth_login_user
from app.services.budget_service import (
    BudgetReservationError,
    estimate_llm_reservation,
    reserve_task_budget,
)


class _FakeTasks:
    def __init__(self, modified_count: int = 1):
        self.modified_count = modified_count
        self.last_filter = None
        self.last_update = None

    async def update_one(self, query, update):
        self.last_filter = query
        self.last_update = update
        return SimpleNamespace(modified_count=self.modified_count)


class _BudgetDb:
    def __init__(self, modified_count: int = 1):
        self.tasks = _FakeTasks(modified_count)


@pytest.mark.asyncio
async def test_atomic_budget_reservation_rejects_when_capacity_is_unavailable():
    db = _BudgetDb(modified_count=0)
    with pytest.raises(BudgetReservationError):
        await reserve_task_budget(
            db, "task-1", "user-1", 0.05, enforce_account_quota=False
        )


@pytest.mark.asyncio
async def test_report_chat_can_reserve_completed_task_budget():
    db = _BudgetDb(modified_count=1)
    await reserve_task_budget(
        db,
        "task-1",
        "user-1",
        0.01,
        allow_completed=True,
        enforce_account_quota=False,
    )
    blocked = db.tasks.last_filter["status"]["$nin"]
    assert "completed" not in blocked
    assert "failed" in blocked
    assert "cancelled" in blocked




class _AggCursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, length=None):
        return self.rows


class _QuotaTasks(_FakeTasks):
    def __init__(self, spent: float, reserved: float):
        super().__init__(modified_count=1)
        self.spent = spent
        self.reserved = reserved

    def aggregate(self, _pipeline):
        return _AggCursor([{"spent": self.spent, "reserved": self.reserved}])


class _QuotaUsers:
    def __init__(self, quota: float):
        self.quota = quota

    async def find_one(self, *_args, **_kwargs):
        return {"_id": "user-1", "usage_quota_usd": self.quota}


class _QuotaDb:
    def __init__(self, quota: float, spent: float, reserved: float):
        self.users = _QuotaUsers(quota)
        self.tasks = _QuotaTasks(spent, reserved)


@pytest.mark.asyncio
async def test_account_quota_rejects_combined_task_commitment(monkeypatch):
    import app.database as database_module

    monkeypatch.setattr(database_module, "get_redis", lambda: None)
    db = _QuotaDb(quota=1.0, spent=0.75, reserved=0.20)

    with pytest.raises(BudgetReservationError, match="Account usage quota"):
        await reserve_task_budget(db, "task-1", "user-1", 0.10)


def test_llm_budget_reservation_is_positive_and_scales_with_output_limit():
    messages = [{"role": "user", "content": "research batteries"}]
    small = estimate_llm_reservation(messages, 256)
    large = estimate_llm_reservation(messages, 4096)
    assert small > 0
    assert large > small


class _Users:
    def __init__(self, user):
        self.user = user

    async def find_one(self, *_args, **_kwargs):
        return self.user


class _AuthDb:
    def __init__(self, user):
        self.users = _Users(user)


@pytest.mark.asyncio
async def test_authenticated_api_rejects_deactivated_user():
    token = create_access_token("user-1")
    db = _AuthDb({"_id": "user-1", "is_active": False})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(authorization=f"Bearer {token}", db=db)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_oauth_does_not_implicitly_link_different_provider():
    db = _AuthDb({
        "_id": "user-1",
        "email": "person@example.com",
        "name": "Person",
        "provider": "local",
        "is_active": True,
    })
    with pytest.raises(ValueError, match="already exists"):
        await oauth_login_user(db, "person@example.com", "Person", "google")
