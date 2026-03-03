import requests
import json
import time

base_url = "http://localhost:8000"

# Register a new user
res = requests.post(f"{base_url}/register", json={
    "first_name": "Alice",
    "last_name": "Test",
    "email": "alice3@example.com",
    "password": "[REDACTED]"
})
print("Register:", res.json())

def login(email, password):
    res = requests.post(f"{base_url}/auth/login", data={"username": email, "password": password})
    return res.json().get("access_token")

token_ikarin = login("ikarin@example.com", "[REDACTED]")
token_alice = login("alice3@example.com", "[REDACTED]")

headers_ikarin = {"Authorization": f"Bearer {token_ikarin}"}
headers_alice = {"Authorization": f"Bearer {token_alice}"}

print("1. Creating request...")
res = requests.post(f"{base_url}/api/v1/requests/create", headers=headers_ikarin, json={
    "target_email": "alice3@example.com",
    "amount": 50.00,
    "purpose": "Dinner <script>alert(1)</script>"
})
req_data = res.json()
print("ReqData:", req_data)
if 'request_id' not in req_data:
    exit(1)
req_id = req_data["request_id"]

print("2. Alice counter-offers $40...")
res = requests.post(f"{base_url}/api/v1/requests/{req_id}/counter", headers=headers_alice, json={"amount": 40.00})
print("Counter1:", res.json())

print("3. Ikarin accepts $40...")
res = requests.post(f"{base_url}/api/v1/requests/{req_id}/counter", headers=headers_ikarin, json={"amount": 40.00})
print("Counter2:", res.json())

print("4. Alice pays the request...")
res = requests.post(f"{base_url}/p2p-transfer", headers=headers_alice, json={
    "recipient_email": "ikarin@example.com",
    "amount": 40.00,
    "commentary": "Here is the money <script>alert(2)</script>",
    "payment_request_id": req_id
})
print("Pay:", res.json())

res = requests.get(f"{base_url}/api/v1/requests", headers=headers_ikarin)
print("5. History:")
for r in res.json():
    if r["id"] == req_id:
        print(f"Status: {r['status']}, Amount: {r['amount']}")
