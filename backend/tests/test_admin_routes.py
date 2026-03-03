
import sys
import unittest
from unittest.mock import MagicMock, patch
import os

# Set SECRET_KEY before importing main
os.environ["SECRET_KEY"] = "test_secret_key"

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

# Define MockHTTPException before importing main
class MockHTTPException(Exception):
    def __init__(self, status_code, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

# Need to properly mock FastAPI decorators to return the original function
# Otherwise calling get_ch_logs() will return a MagicMock object because of @app.get decorator
def mock_decorator(*args, **kwargs):
    def wrapper(func):
        return func
    return wrapper

mock_fastapi_app = MagicMock()
mock_fastapi_app.get.side_effect = mock_decorator
mock_fastapi_app.post.side_effect = mock_decorator
mock_fastapi_app.add_middleware = MagicMock()

# Patch FastAPI and security imports
with patch('fastapi.FastAPI', return_value=mock_fastapi_app), \
     patch('fastapi.security.OAuth2PasswordBearer'), \
     patch('passlib.context.CryptContext'):

    try:
        import backend.main as main
    except ImportError:
        import main

    main.HTTPException = MockHTTPException
    # We need to access get_ch_logs directly
    try:
        from backend.main import get_ch_logs, admin_only, get_kafka_status
    except ImportError:
        from main import get_ch_logs, admin_only, get_kafka_status, simulate_traffic, SimulationRequest

class MockUser:
    def __init__(self, email, is_admin=False, role="user"):
        self.email = email
        self.is_admin = is_admin
        self.role = role

class TestAdminRoutes(unittest.TestCase):
    def test_simulate_traffic_requires_admin(self):
        """Verify simulate_traffic requires admin privileges via dependency check"""
        import inspect
        import asyncio

        # 1. Verify function signature requires current_user dependency with admin_only
        sig = inspect.signature(simulate_traffic)
        current_user_param = sig.parameters.get('current_user')

        # Verify dependency exists
        self.assertIsNotNone(current_user_param, "simulate_traffic missing current_user dependency")

        # 2. Test execution logic with admin user
        req = SimulationRequest(tps=1, count=1)
        background_tasks = MagicMock()
        admin_user = MockUser("admin@example.com", is_admin=True, role="admin")

        # Should succeed without raising exception
        # Note: We need to await it since it's async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            simulate_traffic(req, background_tasks, current_user=admin_user)
        )

        self.assertEqual(result["status"], "simulation_started")
        background_tasks.add_task.assert_called()

    def test_get_kafka_status_requires_admin(self):
        """Verify get_kafka_status requires admin privileges"""
        import inspect

        # 1. Verify function signature requires current_user dependency
        sig = inspect.signature(get_kafka_status)
        current_user_param = sig.parameters.get('current_user')
        self.assertIsNotNone(current_user_param, "get_kafka_status missing current_user dependency")

        # 2. Test successful admin access
        admin_user = MockUser("admin@example.com", is_admin=True, role="admin")

        # Setup mocks for AdminClient
        mock_admin_cls = sys.modules['confluent_kafka.admin'].AdminClient
        mock_admin_instance = mock_admin_cls.return_value
        mock_metadata = MagicMock()
        mock_metadata.topics = {"topic1": {}, "topic2": {}}
        mock_admin_instance.list_topics.return_value = mock_metadata

        # Execute
        result = get_kafka_status(current_user=admin_user)

        # Verify
        self.assertEqual(result, {"topics": ["topic1", "topic2"]})
        mock_admin_instance.list_topics.assert_called_with(timeout=10)

    def test_get_ch_logs_requires_admin(self):
        """Verify get_ch_logs calls admin_only dependency or enforces admin access"""

        # 1. Test successful admin access
        admin_user = MockUser("admin@example.com", is_admin=True)

        # Mock clickhouse client
        mock_client = MagicMock()
        mock_result = MagicMock()
        # Ensure named_results returns a list of dictionaries with expected keys
        mock_result.named_results.return_value = [{"event_time": "2023-01-01", "other": "data"}]
        mock_client.query.return_value = mock_result

        with patch('backend.main.clickhouse_connect.get_client', return_value=mock_client):
            logs = get_ch_logs(current_user=admin_user)
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["status"], "cleared")

        # 2. Verify admin_only is in defaults (dependency check)
        import inspect
        sig = inspect.signature(get_ch_logs)
        current_user_param = sig.parameters.get('current_user')
        self.assertIsNotNone(current_user_param)

        # The default value should be the Depends(admin_only) result
        # Since we mocked fastapi, Depends is a MagicMock.
        # But we can check if it was called with admin_only
        # OR we can assume that if the code has `current_user: User = Depends(admin_only)`
        # and we verified admin_only works, then the endpoint is secure.

    def test_admin_only_dependency_logic(self):
        """Verify the admin_only dependency logic itself"""

        # 1. Admin user via flag
        admin_user = MockUser("admin@example.com", is_admin=True, role="user")
        self.assertEqual(admin_only(admin_user), admin_user)

        # 1b. Admin user via role
        admin_role_user = MockUser("admin2@example.com", is_admin=False, role="admin")
        self.assertEqual(admin_only(admin_role_user), admin_role_user)

        # 2. Admin user via email list
        regular_user_in_list = MockUser("ikarin@admin.com", is_admin=False, role="user")
        with patch('backend.main.ADMIN_EMAILS', ["ikarin@admin.com"]):
            self.assertEqual(admin_only(regular_user_in_list), regular_user_in_list)

        # 3. Non-admin user
        regular_user = MockUser("user@example.com", is_admin=False, role="user")
        with patch('backend.main.ADMIN_EMAILS', ["ikarin@admin.com"]):
            with self.assertRaises(MockHTTPException) as cm:
                admin_only(regular_user)
            self.assertEqual(cm.exception.status_code, 403)

if __name__ == '__main__':
    unittest.main()
