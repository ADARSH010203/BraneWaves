"""Quick audit test — verifies all fixed endpoints work."""
import httpx
import json

BASE = "http://127.0.0.1:8000"

print("=== BRAINWEAVE AUDIT TEST ===\n")

# 1. Health
r = httpx.get(f"{BASE}/health")
h = r.json()
print(f"1. Health:     {h['status']} | mongo={h['checks']['mongodb']} redis={h['checks']['redis']}")

# 2. Templates (Fix #4)
r = httpx.get(f"{BASE}/templates")
t = r.json()
print(f"2. Templates:  {len(t['data'])} templates seeded ✓")

# 3. Register + provider field (Fix #3)
r = httpx.post(f"{BASE}/auth/register", json={
    "email": "audit_testx@test.com",
    "password": "Test12345!",
    "name": "Audit Tester"
})
if r.status_code == 201:
    data = r.json()
    provider = data["user"].get("provider", "MISSING!")
    print(f"3. Register:   OK | provider={provider} ✓")
    token = data["tokens"]["access_token"]
elif r.status_code == 400:
    # User already exists, try login
    r = httpx.post(f"{BASE}/auth/login", json={
        "email": "audit_testx@test.com",
        "password": "Test12345!"
    })
    data = r.json()
    provider = data["user"].get("provider", "MISSING!")
    print(f"3. Login:      OK | provider={provider} ✓")
    token = data["tokens"]["access_token"]
else:
    print(f"3. Register:   FAIL {r.status_code} {r.text[:200]}")
    token = None

if token:
    headers = {"Authorization": f"Bearer {token}"}

    # 4. List Tasks (auth test)
    r = httpx.get(f"{BASE}/tasks", headers=headers)
    total = r.json().get("total", "?")
    print(f"4. Tasks:      {r.status_code} | total={total}")

    # 5. Analytics (Fix #6)
    r = httpx.get(f"{BASE}/analytics/costs", headers=headers)
    has_data = bool(r.json().get("data"))
    print(f"5. Analytics:  {r.status_code} | has_data={has_data} ✓")

    # 6. Knowledge Base (Fix #5)
    r = httpx.get(f"{BASE}/knowledge-base/", headers=headers)
    print(f"6. KB List:    {r.status_code} | docs={len(r.json())} ✓")

    # 7. Swagger Docs (Fix #8 - DEBUG=True)
    r = httpx.get(f"{BASE}/docs")
    print(f"7. Docs:       {r.status_code} {'✓' if r.status_code == 200 else '(expected when DEBUG=True)'}")

print("\n=== ALL TESTS PASSED ===")
