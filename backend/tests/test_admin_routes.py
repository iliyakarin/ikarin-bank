import pytest
import asyncio
from unittest.mock import MagicMock, patch
from auth_utils import admin_only

@pytest.mark.asyncio
async def test_admin_only_dependency_logic(mock_fastapi_dependency):
    main = mock_fastapi_dependency
    main.status.HTTP_403_FORBIDDEN = 403
    main.status.HTTP_401_UNAUTHORIZED = 401

    class MockUser:
        def __init__(self, email, is_admin=False, role="user"):
            self.email = email
            self.is_admin = bool(is_admin)
            self.role = str(role)

    admin_user = MockUser("admin@example.com", is_admin=True, role="admin")
    regular_user = MockUser("user@example.com", is_admin=False, role="user")

    if asyncio.iscoroutinefunction(admin_only):
        result = await admin_only(admin_user)
    else:
        result = admin_only(admin_user)
    assert result == admin_user

    try:
        if asyncio.iscoroutinefunction(admin_only):
            await admin_only(regular_user)
        else:
            admin_only(regular_user)
        pytest.fail("Should have raised HTTPException")
    except Exception as e:
        assert getattr(e, "status_code", 0) == 403

@pytest.mark.asyncio
async def test_get_ch_logs_requires_admin(mock_fastapi_dependency):
    from routers.admin import get_ch_logs
    main = mock_fastapi_dependency
    main.status.HTTP_403_FORBIDDEN = 403

    admin_user = MagicMock()
    admin_user.role = "admin"

    mock_client = MagicMock()
    mock_result = MagicMock()
    # Mock named_results to return a list of dicts
    mock_result.named_results.return_value = [{"event_time": "2023-01-01", "other": "data"}]
    mock_client.query.return_value = mock_result

    # Patch the utility function used by main.py
    with patch('routers.admin.get_ch_client', return_value=mock_client):
        logs = get_ch_logs(current_user=admin_user)
        assert len(logs) == 1
        # The endpoint adds status="cleared" and created_at=event_time
        assert logs[0]["status"] == "cleared"
        assert logs[0]["created_at"] == "2023-01-01"

@pytest.mark.asyncio
async def test_get_kafka_status_requires_admin(mock_fastapi_dependency):
    from routers.admin import get_kafka_status
    main = mock_fastapi_dependency

    admin_user = MagicMock()
    admin_user.role = "admin"

    mock_metadata = MagicMock()
    mock_metadata.topics = {"topic1": {}, "topic2": {}}

    with patch('routers.admin.AdminClient') as mock_admin_cls:
        mock_admin_instance = mock_admin_cls.return_value
        mock_admin_instance.list_topics.return_value = mock_metadata

        result = get_kafka_status(current_user=admin_user)
        assert result == {"topics": ["topic1", "topic2"]}

@pytest.mark.asyncio
async def test_simulate_traffic_api(mock_fastapi_dependency):
    from routers.admin import simulate_traffic
    main = mock_fastapi_dependency

    admin_user = MagicMock()
    admin_user.role = "admin"

    # Use real Pydantic model if available, else mock
    try:
        from schemas.admin import SimulationRequest
        req = SimulationRequest(batch_size=10, tps=10, count=100)
    except:
        req = MagicMock()
        req.batch_size = 10
        req.count = 1


    mock_bg = MagicMock()

    if asyncio.iscoroutinefunction(simulate_traffic):
        result = await simulate_traffic(req, background_tasks=mock_bg, current_user=admin_user)
    else:
        result = simulate_traffic(req, background_tasks=mock_bg, current_user=admin_user)
    assert result["status"] == "simulation_started"
    # In main.py, it calls background_tasks.add_task
    assert mock_bg.add_task.called
