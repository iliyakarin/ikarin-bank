import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
import datetime
from fastapi import HTTPException
import asyncio

# Need to import our routers and models. Since we mock dependencies, we'll
# use the same structure as in test_p2p_transfer.

class MockAccount:
    def __init__(self, id, user_id, balance, is_main, parent_account_id=None, name=""):
        self.id = id
        self.user_id = user_id
        self.balance = balance
        self.is_main = is_main
        self.parent_account_id = parent_account_id
        self.name = name

def test_subaccount_creation_limit(mock_fastapi_dependency):
    import main
    import routers.accounts as accounts_router
    
    current_user = MagicMock()
    current_user.id = 1
    
    from unittest.mock import AsyncMock
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
    
    # Mock finding the main account
    main_acc = MockAccount(100, 1, Decimal("100"), True, None, "Main")
    
    
    call_count = 0
    def execute_side_effect(stmt, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        if call_count == 1:
            mock_result.scalar.return_value = 10
            return mock_result
            
        mock_scalars.first.return_value = main_acc
        mock_result.scalar.return_value = 0
        return mock_result
        
    mock_db.execute.side_effect = execute_side_effect

    
    req = accounts_router.SubAccountCreate(name="Trip Fund")
    
    with patch("routers.accounts.assign_account_credentials", new_callable=AsyncMock) as mock_assign, \
         patch("account_service.assign_account_credentials", new_callable=AsyncMock):
        import asyncio
        fn = getattr(accounts_router.create_sub_account, "__wrapped__", accounts_router.create_sub_account)
        
        with pytest.raises(accounts_router.HTTPException) as excinfo:
            if asyncio.iscoroutinefunction(fn):
                asyncio.run(fn(request=req, current_request=MagicMock(), current_user=current_user, db=mock_db))
            else:
                fn(request=req, current_request=MagicMock(), current_user=current_user, db=mock_db)
        
        assert excinfo.value.status_code == 400
        assert "Maximum of 10 sub-accounts reached" in str(excinfo.value.detail)

def test_subaccount_creation_invalid_name(mock_fastapi_dependency):
    import main
    import routers.accounts as accounts_router
    
    import asyncio
    req = accounts_router.SubAccountCreate(name="Trip_Fund!@#")
    current_user = MagicMock()
    from unittest.mock import AsyncMock
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
    fn = getattr(accounts_router.create_sub_account, "__wrapped__", accounts_router.create_sub_account)
    with pytest.raises(accounts_router.HTTPException) as excinfo:
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn(request=req, current_request=MagicMock(), current_user=current_user, db=mock_db))
        else:
            fn(request=req, current_request=MagicMock(), current_user=current_user, db=mock_db)
    
    assert excinfo.value.status_code == 400
    assert "Name can only contain letters, numbers, and spaces" in str(excinfo.value.detail)

def test_internal_transfer_success(mock_fastapi_dependency):
    import main
    import routers.accounts as accounts_router
    import uuid
    
    current_user = MagicMock()
    current_user.id = 1
    current_user.email = "test@test.com"
    
    from unittest.mock import AsyncMock
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    acc1 = MockAccount(100, 1, Decimal("100.00"), True, None, "Main")
    acc2 = MockAccount(101, 1, Decimal("50.00"), False, 100, "Sub")
    
    mock_q = MagicMock()
    
    def query_filter_side_effect(*args):
        # We need to simulate locking.
        # find in DB
        res = MagicMock()
        if len(args) > 0:
            # simulate getting both accounts
            # the _get_account_locked helper finds by ID
            pass
        return res

    mock_db.query.return_value = mock_q
    # We will mock the _get_account_locked helper directly for simplicity, or just let DB mock handle it.
    
    # Actually, it's easier to mock _get_account_locked if we can.
    # Otherwise simulate DB query iterator like in test_p2p_transfer
    account_lookup = {
        100: acc1,
        101: acc2
    }
    
    acc_iter = iter([acc1, acc2, acc1, acc2, acc1, acc2, acc1, acc2])
    
    def execute_side_effect(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        if "count(" in stmt_str:
            mock_result.scalar.return_value = 10
            return mock_result
            
        try:
            val = next(acc_iter)
        except Exception:
            val = None
            
        mock_scalars.first.return_value = val
        return mock_result
        
    mock_db.execute.side_effect = execute_side_effect

        
    req = accounts_router.InternalTransferRequest(
        from_account_id=100,
        to_account_id=101,
        amount=Decimal("20.00")
    )
    
    import asyncio
    
    fn = getattr(accounts_router.internal_transfer, "__wrapped__", accounts_router.internal_transfer)
    if asyncio.iscoroutinefunction(fn):
        res = asyncio.run(fn(request=req, current_request=MagicMock(), current_user=current_user, db=mock_db))
    else:
        res = fn(request=req, current_request=MagicMock(), current_user=current_user, db=mock_db)
    
    assert res["status"] == "success"
    assert acc1.balance == Decimal("80.00")
    assert acc2.balance == Decimal("70.00")
    assert mock_db.commit.call_count == 1
    assert mock_db.add.call_count >= 2

def test_internal_transfer_insufficient_funds(mock_fastapi_dependency):
    import main
    import routers.accounts as accounts_router
    
    current_user = MagicMock()
    current_user.id = 1
    
    from unittest.mock import AsyncMock
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    acc1 = MockAccount(100, 1, Decimal("10.00"), True, None, "Main") # Try to send 20
    acc2 = MockAccount(101, 1, Decimal("50.00"), False, 100, "Sub")
    
    acc_iter = iter([acc1, acc2, acc1, acc2, acc1, acc2, acc1, acc2])
    
    def execute_side_effect(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        if "count(" in stmt_str:
            mock_result.scalar.return_value = 10
            return mock_result
            
        try:
            val = next(acc_iter)
        except Exception:
            val = None
            
        mock_scalars.first.return_value = val
        return mock_result
        
    mock_db.execute.side_effect = execute_side_effect

        
    req = accounts_router.InternalTransferRequest(
        from_account_id=100,
        to_account_id=101,
        amount=Decimal("20.00")
    )
    
    with pytest.raises(accounts_router.HTTPException) as excinfo:
        fn = getattr(accounts_router.internal_transfer, "__wrapped__", accounts_router.internal_transfer)
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn(request=req, current_request=MagicMock(), current_user=current_user, db=mock_db))
        else:
            fn(request=req, current_request=MagicMock(), current_user=current_user, db=mock_db)
    
    assert excinfo.value.status_code == 400
    assert "Insufficient funds in source account" in str(excinfo.value.detail)
    assert mock_db.rollback.call_count == 1
