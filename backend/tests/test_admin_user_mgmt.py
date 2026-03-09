import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from database import User, Account

@pytest.mark.asyncio
async def test_search_user_by_email_admin(mock_fastapi_dependency):
    """Verify that an admin can search for a user by email."""
    main = mock_fastapi_dependency
    search_user_by_email = main.search_user_by_email
    
    admin_user = MagicMock(spec=User)
    admin_user.role = "admin"
    
    target_user = MagicMock(spec=User)
    target_user.email = "target@example.com"
    target_user.id = 123
    
    db = AsyncMock()
    res = MagicMock()
    res.scalars().first.return_value = target_user
    db.execute.return_value = res
    
    result = await search_user_by_email(email="target@example.com", db=db, current_user=admin_user)
    assert result == target_user
    db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_search_user_by_email_not_found(mock_fastapi_dependency):
    """Verify 404 is returned if user is not found."""
    main = mock_fastapi_dependency
    search_user_by_email = main.search_user_by_email
    
    admin_user = MagicMock(spec=User)
    admin_user.role = "admin"
    
    db = AsyncMock()
    res = MagicMock()
    res.scalars().first.return_value = None
    db.execute.return_value = res
    
    with pytest.raises(main.HTTPException) as excinfo:
        await search_user_by_email(email="nonexistent@example.com", db=db, current_user=admin_user)
    assert excinfo.value.status_code == 404

@pytest.mark.asyncio
async def test_search_user_by_email_unauthorized(mock_fastapi_dependency):
    """
    Verify that regular users cannot search. 
    Note: The RoleChecker dependency actually handles this, 
    but we can test the function directly if needed, 
    or just rely on the dependency test in test_admin_routes.py.
    """
    pass
