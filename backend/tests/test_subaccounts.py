import pytest
from unittest.mock import MagicMock
from decimal import Decimal
import datetime
from fastapi import HTTPException

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
    
    mock_db = MagicMock()
    
    # Mock finding the main account
    main_acc = MockAccount(100, 1, Decimal("100"), True, None, "Main")
    
    def query_side_effect(model):
        q = MagicMock()
        if model == accounts_router.Account:
            # For the first query (Main Account)
            q.filter.return_value.first.return_value = main_acc
            # For the count query (Sub-accounts count)
            q.filter.return_value.count.return_value = 10 # Already has 10!
            return q
        return MagicMock()
        
    mock_db.query.side_effect = query_side_effect
    
    req = accounts_router.SubAccountCreate(name="Trip Fund")
    
    try:
        import asyncio
        fn = getattr(accounts_router.create_sub_account, "__wrapped__", accounts_router.create_sub_account)
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn(req, current_user, mock_db))
        else:
            fn(req, current_user, mock_db)
        pytest.fail("Should have raised HTTPException for max limit")
    except Exception as e:
        assert getattr(e, "status_code", 0) == 400
        assert "Maximum of 10 sub-accounts reached" in str(getattr(e, "detail", ""))

def test_subaccount_creation_invalid_name(mock_fastapi_dependency):
    import main
    import routers.accounts as accounts_router
    
    try:
        import asyncio
        req = accounts_router.SubAccountCreate(name="Trip_Fund!@#")
        current_user = MagicMock()
        mock_db = MagicMock()
        fn = getattr(accounts_router.create_sub_account, "__wrapped__", accounts_router.create_sub_account)
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn(req, current_user, mock_db))
        else:
            fn(req, current_user, mock_db)
        pytest.fail("Should have raised HTTPException for invalid name")
    except Exception as e:
        assert getattr(e, "status_code", 0) == 400
        assert "Name can only contain letters, numbers, and spaces" in str(getattr(e, "detail", ""))

def test_internal_transfer_success(mock_fastapi_dependency):
    import main
    import routers.accounts as accounts_router
    import uuid
    
    current_user = MagicMock()
    current_user.id = 1
    current_user.email = "test@test.com"
    
    mock_db = MagicMock()
    
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
    
    acc_iter = iter([acc1, acc2])
    def db_query(model):
        q = MagicMock()
        if model == accounts_router.Account:
            locked_q = MagicMock()
            locked_q.first.side_effect = acc_iter
            q.filter.return_value.with_for_update.return_value = locked_q
        return q
        
    mock_db.query.side_effect = db_query
        
    req = accounts_router.InternalTransferRequest(
        from_account_id=100,
        to_account_id=101,
        amount=Decimal("20.00")
    )
    
    import asyncio
    
    fn = getattr(accounts_router.internal_transfer, "__wrapped__", accounts_router.internal_transfer)
    if asyncio.iscoroutinefunction(fn):
        res = asyncio.run(fn(req, current_user, mock_db))
    else:
        res = fn(req, current_user, mock_db)
    
    assert res["status"] == "success"
    assert acc1.balance == Decimal("80.00")
    assert acc2.balance == Decimal("70.00")
    assert mock_db.commit.call_count == 1
    assert mock_db.add.call_count == 2 # 2 transactions written

def test_internal_transfer_insufficient_funds(mock_fastapi_dependency):
    import main
    import routers.accounts as accounts_router
    
    current_user = MagicMock()
    current_user.id = 1
    
    mock_db = MagicMock()
    
    acc1 = MockAccount(100, 1, Decimal("10.00"), True, None, "Main") # Try to send 20
    acc2 = MockAccount(101, 1, Decimal("50.00"), False, 100, "Sub")
    
    acc_iter = iter([acc1, acc2])
    def db_query(model):
        q = MagicMock()
        if model == accounts_router.Account:
            locked_q = MagicMock()
            locked_q.first.side_effect = acc_iter
            q.filter.return_value.with_for_update.return_value = locked_q
        return q
    mock_db.query.side_effect = db_query
        
    req = accounts_router.InternalTransferRequest(
        from_account_id=100,
        to_account_id=101,
        amount=Decimal("20.00")
    )
    
    import asyncio
    try:
        fn = getattr(accounts_router.internal_transfer, "__wrapped__", accounts_router.internal_transfer)
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn(req, current_user, mock_db))
        else:
            fn(req, current_user, mock_db)
        pytest.fail("Should have raised HTTPException for funds")
    except Exception as e:
        assert getattr(e, "status_code", 0) == 400
        assert "Insufficient funds in source account" in str(getattr(e, "detail", ""))
        assert mock_db.rollback.call_count == 1
