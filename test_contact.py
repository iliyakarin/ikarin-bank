import requests

def test_add_contact():
    # Login
    login_data = {
        "username": "admin@example.com",
        "password": "[REDACTED]"
    }
    r_login = requests.post("http://localhost:8000/auth/login", data=login_data)
    if r_login.status_code != 200:
        print("Login failed:", r_login.text)
        return

    token = r_login.json()["access_token"]
    
    # Add contact
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "contact_name": "Test User",
        "contact_email": "test@example.com"
    }
    r = requests.post("http://localhost:8000/api/v1/contacts", headers=headers, json=payload)
    print("Status:", r.status_code)
    print("Response:", r.text)

if __name__ == "__main__":
    test_add_contact()
