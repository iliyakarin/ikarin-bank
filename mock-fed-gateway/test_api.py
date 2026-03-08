import requests
import json
import uuid

BASE_URL = "http://localhost:8002"
API_KEY = "fed-secret-key-2026"
HEADERS = {"X-API-KEY": API_KEY}

def test_auth():
    print("Testing Auth...")
    resp = requests.post(f"{BASE_URL}/fed/ach/originate", headers={"X-API-KEY": "wrong-key"})
    assert resp.status_code == 401
    print("✅ Auth blocked invalid key")

def test_ach_originate():
    print("Testing ACH Originate...")
    # Valid RTN (Chase)
    payload = {
        "routing_number": "021000021",
        "account_number": "123456789",
        "amount": 100.00,
        "type": "ACH"
    }
    resp = requests.post(f"{BASE_URL}/fed/ach/originate", headers=HEADERS, json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    print("✅ Valid ACH successful")

    # Invalid RTN
    payload["routing_number"] = "000000000"
    resp = requests.post(f"{BASE_URL}/fed/ach/originate", headers=HEADERS, json=payload)
    assert resp.status_code == 404
    print("✅ Invalid RTN blocked")

    # R01 NSF Simulation
    payload["routing_number"] = "021000021"
    payload["amount"] = 100.01
    resp = requests.post(f"{BASE_URL}/fed/ach/originate", headers=HEADERS, json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "R01"
    print("✅ R01 NSF Simulation triggered")

def test_billpay_validation():
    print("Testing Bill Pay Validation...")
    # Valid Merchant
    payload = {
        "merchant_id": "att-001",
        "subscriber_id": "ABC12345"
    }
    resp = requests.post(f"{BASE_URL}/billpay/validate-subscriber", headers=HEADERS, json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "VALIDATED"
    print("✅ Valid subscriber successful")

    # R03 Invalid Subscriber
    payload["subscriber_id"] = "ABC00000XYZ"
    resp = requests.post(f"{BASE_URL}/billpay/validate-subscriber", headers=HEADERS, json=payload)
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "INVALID_SUBSCRIBER"
    print("✅ R03 Invalid Subscriber triggered")

def test_billpay_execute():
    print("Testing Bill Pay Execute...")
    payload = {
        "merchant_id": "att-001",
        "subscriber_id": "ABC12345",
        "amount": 50.00
    }
    resp = requests.post(f"{BASE_URL}/billpay/execute", headers=HEADERS, json=payload)
    assert resp.status_code == 200
    assert "trace_id" in resp.json()
    print("✅ Bill Pay execution successful")

if __name__ == "__main__":
    try:
        test_auth()
        test_ach_originate()
        test_billpay_validation()
        test_billpay_execute()
        print("\n✨ ALL TESTS PASSED ✨")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
