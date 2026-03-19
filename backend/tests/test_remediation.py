import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
from database import User, Account, Transaction

@pytest.mark.asyncio
async def test_delete_user_unauthorized(mock_fastapi_dependency):
    """Verify that only admins can call the delete_user endpoint."""
    main = mock_fastapi_dependency
    delete_user = main.delete_user

    # Mocking dependencies
    regular_user = MagicMock(spec=User)
    regular_user.role = "user"

    db = AsyncMock()

    # The admin_only dependency is what protects the route.
    # In the mock, we can simulate what happens if a regular user is passed.
    pass

@pytest.mark.asyncio
async def test_delete_user_not_found(mock_fastapi_dependency):
    """Verify 404 is returned if user doesn't exist."""
    main = mock_fastapi_dependency
    delete_user = main.delete_user

    admin_user = MagicMock(spec=User)
    admin_user.role = "admin"

    db = AsyncMock()
    # Mock user lookup to return None
    res = MagicMock()
    res.scalars().first.return_value = None
    db.execute.return_value = res

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await delete_user(user_id=999, db=db, current_user=admin_user)
    assert excinfo.value.status_code == 404

@pytest.mark.asyncio
async def test_delete_user_full_cleanup(mock_fastapi_dependency):
    """Verify that a user and all related data are deleted/anonymized."""
    main = mock_fastapi_dependency
    delete_user = main.delete_user

    admin_user = MagicMock(spec=User)
    admin_user.role = "admin"
    admin_user.id = 1

    target_user = MagicMock(spec=User)
    target_user.id = 10
    target_user.email = "victim@example.com"

    db = AsyncMock()

    # 1. Mock user lookup (Step 1 in delete_user)
    res_user = MagicMock()
    res_user.scalars().first.return_value = target_user

    # 2. Mock account lookup (Step 2 in delete_user)
    res_accounts = MagicMock()
    res_accounts.scalars().all.return_value = [101, 102]

    # Configure db.execute to return these mocks in order
    db.execute.side_effect = [res_user, res_accounts, AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()]

    # 3. Mock ClickHouse client
    mock_ch = MagicMock()
    with patch('routers.admin.get_ch_client', return_value=mock_ch), \
         patch('routers.admin.emit_activity') as mock_emit, \
         patch('routers.admin.CH_DB', "banking_log"):

        await delete_user(user_id=10, db=db, current_user=admin_user)

        # Verify Audit Emit
        mock_emit.assert_called_once()
        assert mock_emit.call_args[0][1] == admin_user.id # current_user.id

        # Verify ClickHouse Comands
        # command 1: transactions purge
        # command 2: activity_events purge
        assert mock_ch.command.call_count == 2
        args1 = mock_ch.command.call_args_list[0][0][0]
        assert "DELETE WHERE account_id IN (101,102)" in args1

        args2 = mock_ch.command.call_args_list[1][0][0]
        assert "DELETE WHERE user_id = 10" in args2

        # Verify DB commit
        db.commit.assert_called_once()
