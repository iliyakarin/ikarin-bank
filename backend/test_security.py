import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock FastAPI and other dependencies
sys.modules['fastapi'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['aiokafka'] = MagicMock()
sys.modules['pydantic'] = MagicMock()
sys.modules['database'] = MagicMock()
sys.modules['fastapi.middleware.cors'] = MagicMock()
sys.modules['confluent_kafka'] = MagicMock()
sys.modules['confluent_kafka.admin'] = MagicMock()
sys.modules['clickhouse_connect'] = MagicMock()
sys.modules['passlib'] = MagicMock()
sys.modules['passlib.context'] = MagicMock()
sys.modules['jose'] = MagicMock()
sys.modules['fastapi.security'] = MagicMock()

class MockHTTPException(Exception):
    def __init__(self, status_code, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

with patch('fastapi.FastAPI'), patch('fastapi.security.OAuth2PasswordBearer'), patch('passlib.context.CryptContext'):
    import main
    main.HTTPException = MockHTTPException
    from main import admin_only

class MockUser:
    def __init__(self, email, is_admin=None):
        self.email = email
        if is_admin is not None:
            self.is_admin = is_admin

class TestSecurityFix(unittest.TestCase):
    def test_admin_only_with_authorized_email(self):
        user = MockUser("admin@example.com")
        with patch('main.ADMIN_EMAILS', ["admin@example.com"]):
            result = admin_only(user)
            self.assertEqual(result, user)

    def test_admin_only_with_unauthorized_email(self):
        user = MockUser("attacker@example.com")
        with patch('main.ADMIN_EMAILS', ["admin@example.com"]):
            with self.assertRaises(MockHTTPException) as cm:
                admin_only(user)
            self.assertEqual(cm.exception.status_code, 403)

    def test_admin_only_with_db_flag(self):
        user = MockUser("someone@example.com", is_admin=True)
        with patch('main.ADMIN_EMAILS', ["admin@example.com"]):
            result = admin_only(user)
            self.assertEqual(result, user)

    def test_sql_validation_logic(self):
        import re
        def validate(query):
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                return False
            forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE", "RENAME"]
            for word in forbidden:
                if re.search(r"\b" + word + r"\b", query_upper):
                    return False
            return True

        self.assertTrue(validate("SELECT * FROM transactions"))
        # This is expected to be False because of the keyword check, even if it's in a string
        self.assertFalse(validate("SELECT * FROM users WHERE name = 'John; DROP TABLE users'"))
        self.assertFalse(validate("DROP TABLE users"))
        self.assertFalse(validate("SELECT * FROM users; DROP TABLE users"))
        self.assertFalse(validate("UPDATE users SET balance = 100"))
        self.assertTrue(validate("SELECT * FROM desktop_users"))

if __name__ == '__main__':
    unittest.main()
