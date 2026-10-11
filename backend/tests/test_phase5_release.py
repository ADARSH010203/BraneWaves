"""Phase 5 release-gate integration tests using real CI MongoDB + Redis."""
from __future__ import annotations

import json
import uuid

import httpx
import pytest

from app.database import (
    connect_db,
    connect_redis,
    disconnect_db,
    disconnect_redis,
    get_db,
    get_redis,
)
from app.main import app
from app.routes.auth import _oauth_exchange_key


async def _ensure_connections():
    # pytest-asyncio uses a fresh loop per test. Module-level Motor/Redis clients
    # created by an earlier test must not leak into the next event loop.
    await disconnect_redis()
    await disconnect_db()
    await connect_db()
    await connect_redis()

    db = get_db()
    redis = get_redis()
    assert redis is not None
    return db, redis


@pytest.mark.asyncio
async def test_release_api_lifecycle_queue_cleanup_and_readiness():
    db, redis = await _ensure_connections()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        email = f"release_{uuid.uuid4().hex[:10]}@example.com"
        password = "ReleaseGate123!"

        # Liveness/readiness reflect real CI Mongo + Redis connectivity.
        live = await client.get("/health/live")
        assert live.status_code == 200
        ready = await client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["checks"]["mongodb"] == "ok"
        assert ready.json()["checks"]["redis"] == "ok"

        # Register and use the returned short-lived bearer token.
        register = await client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Release User"},
        )
        assert register.status_code == 201
        payload = register.json()
        access_token = payload["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        user_id = payload["user"]["id"]

        me = await client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == email

        patch = await client.patch(
            "/auth/me",
            headers=headers,
            json={"name": "Release Verified User"},
        )
        assert patch.status_code == 200
        assert patch.json()["name"] == "Release Verified User"

        summary = await client.get("/analytics/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["total_tasks"] == 0

        # Task creation must persist and enqueue a real Redis payload.
        created = await client.post(
            "/tasks",
            headers=headers,
            json={
                "title": "Release queue contract",
                "description": "Validate API, MongoDB, Redis queueing and cancellation.",
                "budget_usd": 0.25,
                "max_steps": 2,
                "use_knowledge_base": False,
            },
        )
        assert created.status_code == 201
        task_id = created.json()["id"]

        queued = await redis.lrange("task_queue", 0, -1)
        assert any(
            json.loads(raw).get("task_id") == task_id
            for raw in queued
        )

        task = await client.get(f"/tasks/{task_id}", headers=headers)
        assert task.status_code == 200
        assert task.json()["status"] == "pending"

        summary_after = await client.get("/analytics/summary", headers=headers)
        assert summary_after.status_code == 200
        assert summary_after.json()["total_tasks"] == 1

        cancelled = await client.post(f"/tasks/{task_id}/cancel", headers=headers)
        assert cancelled.status_code == 200

        # OAuth callback exchange codes are one-time even though this test
        # seeds the exchange directly instead of contacting a provider.
        exchange_code = f"release-{uuid.uuid4().hex}{uuid.uuid4().hex}"
        await redis.set(
            _oauth_exchange_key(exchange_code),
            "synthetic-access-token",
            ex=60,
        )
        exchanged = await client.post(
            "/auth/oauth/exchange",
            headers={"Origin": "http://localhost:3000"},
            json={"code": exchange_code},
        )
        assert exchanged.status_code == 200
        assert exchanged.json()["access_token"] == "synthetic-access-token"

        replay = await client.post(
            "/auth/oauth/exchange",
            headers={"Origin": "http://localhost:3000"},
            json={"code": exchange_code},
        )
        assert replay.status_code == 401

        # Deleting the account must remove persisted data and queued jobs.
        deleted = await client.delete("/auth/me", headers=headers)
        assert deleted.status_code == 200

        assert await db.users.find_one({"_id": user_id}) is None
        assert await db.tasks.find_one({"_id": task_id}) is None

        queued_after = await redis.lrange("task_queue", 0, -1)
        processing_after = await redis.lrange("task_processing", 0, -1)
        assert not any(
            json.loads(raw).get("task_id") == task_id
            for raw in [*queued_after, *processing_after]
        )

        old_token = await client.get("/auth/me", headers=headers)
        assert old_token.status_code == 401


@pytest.mark.asyncio
async def test_required_release_indexes_exist():
    db, _redis = await _ensure_connections()

    sessions = await db.sessions.index_information()
    assert sessions["refresh_token_hash_1"]["unique"] is True

    reports = await db.reports.index_information()
    assert reports["task_id_1"]["unique"] is True

    memory_edges = await db.memory_edges.index_information()
    compound = [
        spec
        for spec in memory_edges.values()
        if spec.get("key")
        == [
            ("user_id", 1),
            ("from_node_id", 1),
            ("to_node_id", 1),
            ("relation", 1),
        ]
    ]
    assert compound
