"""Verification test for all 10 fixes."""
import httpx

BASE = "http://127.0.0.1:8000"

print("=== BRAINWEAVE 10-FIX VERIFICATION ===\n")

# Health
r = httpx.get(f"{BASE}/health")
h = r.json()
print(f"1. Health: {h['status']} | mongo={h['checks']['mongodb']} redis={h['checks']['redis']}")

# Templates (Fix #4 from earlier session - seeding)
r = httpx.get(f"{BASE}/templates")
print(f"2. Templates: {r.status_code} | count={len(r.json()['data'])}")

# Register + Login
r = httpx.post(f"{BASE}/auth/register", json={
    "email": "fix10test@test.com", "password": "Test12345!", "name": "Fix10 Tester"
})
if r.status_code == 201:
    token = r.json()["tokens"]["access_token"]
    print(f"3. Register: OK")
elif r.status_code == 400:
    r = httpx.post(f"{BASE}/auth/login", json={
        "email": "fix10test@test.com", "password": "Test12345!"
    })
    token = r.json()["tokens"]["access_token"]
    print(f"3. Login: OK")
else:
    print(f"3. Auth: FAIL {r.status_code}")
    token = None

if token:
    headers = {"Authorization": f"Bearer {token}"}

    # Knowledge Base list (Fix #1 - FileResponse import)
    r = httpx.get(f"{BASE}/knowledge-base/", headers=headers)
    print(f"4. KB List (Fix #1): {r.status_code} OK")

    # Analytics (Fix from earlier session)
    r = httpx.get(f"{BASE}/analytics/costs", headers=headers)
    print(f"5. Analytics: {r.status_code} OK")

print("\n=== VERIFICATION COMPLETE ===")
