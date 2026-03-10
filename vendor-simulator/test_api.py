import requests
import json

import os

BASE_URL = os.getenv("SIMULATOR_LOCAL_URL", "http://localhost:8001")
API_KEY = os.getenv("SIMULATOR_API_KEY")
HEADERS = {"X-API-KEY": API_KEY}

def test_auth():
    print("Testing Auth...")
    resp = requests.post(f"{BASE_URL}/billpay/validate-subscriber", headers={"X-API-KEY": "wrong-key"}, json={})
    assert resp.status_code == 401
    print("✅ Auth blocked invalid key")

def test_list_vendors():
    print("Testing List Vendors...")
    resp = requests.get(f"{BASE_URL}/vendors")
    assert resp.status_code == 200
    data = resp.json()
    assert "vendors" in data
    assert len(data["vendors"]) == 15
    print(f"✅ Found {len(data['vendors'])} vendors")

def test_billpay_validation():
    print("Testing Bill Pay Validation...")
    # Valid Merchant
    payload = {
        "merchant_id": "netflix-001",
        "subscriber_id": "SUB-12345"
    }
    resp = requests.post(f"{BASE_URL}/billpay/validate-subscriber", headers=HEADERS, json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "VALIDATED"
    print("✅ Valid subscriber successful")

    # Invalid Subscriber Simulation (ends in 00000)
    payload["subscriber_id"] = "SUB-00000"
    resp = requests.post(f"{BASE_URL}/billpay/validate-subscriber", headers=HEADERS, json=payload)
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "INVALID_SUBSCRIBER"
    print("✅ Invalid Subscriber triggered")

def test_billpay_execute():
    print("Testing Bill Pay Execute...")
    payload = {
        "merchant_id": "netflix-001",
        "subscriber_id": "SUB-12345",
        "amount": 15.99
    }
    resp = requests.post(f"{BASE_URL}/billpay/execute", headers=HEADERS, json=payload)
    assert resp.status_code == 200
    assert "trace_id" in resp.json()
    print("✅ Bill Pay execution successful")

if __name__ == "__main__":
    try:
        test_auth()
        test_list_vendors()
        test_billpay_validation()
        test_billpay_execute()
        print("\n✨ ALL VENDOR SIMULATOR TESTS PASSED ✨")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
