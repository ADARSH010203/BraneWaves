"""Integration tests for Auth Routes."""
import pytest
import uuid
import httpx
from app.main import app
from app.database import connect_db, connect_redis


@pytest.mark.asyncio
async def test_auth_full_lifecycle():
    await connect_db()
    await connect_redis()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        test_email = f"authtest_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePassword123!"

        # 1. Register new user
        reg_res = await client.post(
            "/auth/register",
            json={"email": test_email, "password": password, "name": "Auth Tester"},
        )
        assert reg_res.status_code == 201
        data = reg_res.json()
        assert "user" in data
        assert data["user"]["email"] == test_email
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" not in data["tokens"]
        assert client.cookies.get("arc_refresh_token")

        # 2. Duplicate registration fails (409)
        dup_res = await client.post(
            "/auth/register",
            json={"email": test_email, "password": password, "name": "Duplicate Tester"},
        )
        assert dup_res.status_code == 409

        # 3. Login with correct credentials
        login_res = await client.post(
            "/auth/login",
            json={"email": test_email, "password": password},
        )
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert login_data["user"]["email"] == test_email
        assert client.cookies.get("arc_refresh_token")

        # 4. Login with wrong password fails (401)
        bad_pw_res = await client.post(
            "/auth/login",
            json={"email": test_email, "password": "WrongPassword999!"},
        )
        assert bad_pw_res.status_code == 401

        # 5. Refresh token
        refresh_res = await client.post("/auth/refresh")
        assert refresh_res.status_code == 200
        ref_data = refresh_res.json()
        assert "access_token" in ref_data
        assert "refresh_token" not in ref_data
        assert client.cookies.get("arc_refresh_token")

        # 6. Logout user
        logout_res = await client.post("/auth/logout")
        assert logout_res.status_code == 200
        assert logout_res.json()["success"] is True

        # 7. Refresh after logout fails (401)
        post_logout_ref = await client.post("/auth/refresh")
        assert post_logout_ref.status_code == 401
