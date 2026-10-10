"""Tests for deposit routes, scheduled transfer routes, and account transactions routes.

Verifies:
1. Both /v1/deposits and /v1 prefixes are registered for deposit.router in backend/main.py.
2. deposit.router contains required endpoints (/payment_intents, /create-checkout-session, etc.).
3. GET /transfers/scheduled is registered in the transfers router (preventing 405 Method Not Allowed).
4. GET /{account_id}/transactions is registered in the accounts router.
"""
from pathlib import Path
import pytest
from fastapi import FastAPI

from routers.transfers import router as transfers_router
from routers.accounts import router as accounts_router
from routers.deposit import router as deposit_router


def test_deposit_routes_dual_mounted_in_app():
    """Verify backend/main.py mounts deposit.router under both /v1/deposits and /v1 prefixes."""
    main_py_candidates = [
        Path(__file__).resolve().parent.parent / "main.py",
        Path("backend/main.py"),
    ]
    main_py_file = next((p for p in main_py_candidates if p.exists()), None)
    assert main_py_file is not None, "backend/main.py not found"
    
    main_py = main_py_file.read_text()
    assert 'app.include_router(deposit.router, prefix="/v1/deposits")' in main_py, (
        'app.include_router(deposit.router, prefix="/v1/deposits") missing from backend/main.py'
    )
    assert (
        'app.include_router(deposit.router, prefix=api_v1_prefix)' in main_py
        or 'app.include_router(deposit.router, prefix="/v1")' in main_py
    ), 'app.include_router(deposit.router, prefix=api_v1_prefix) missing from backend/main.py'

    # Verify routes registered on deposit.router
    deposit_routes = [getattr(r, "path", "") for r in deposit_router.routes]
    assert "/payment_intents" in deposit_routes, "/payment_intents missing from deposit router"
    assert "/payment_methods" in deposit_routes, "/payment_methods missing from deposit router"
    assert "/create-checkout-session" in deposit_routes, "/create-checkout-session missing from deposit router"
    assert "/subscriptions/me" in deposit_routes, "/subscriptions/me missing from deposit router"

    # Verify mounted routes match expected paths
    test_app = FastAPI()
    test_app.include_router(deposit_router, prefix="/v1/deposits")
    test_app.include_router(deposit_router, prefix="/v1")
    app_routes = [getattr(r, "path", "") for r in test_app.routes]

    assert "/v1/deposits/payment_intents" in app_routes, (
        "/v1/deposits/payment_intents missing from app routes — frontend expects this path"
    )
    assert "/v1/deposits/payment_methods" in app_routes, (
        "/v1/deposits/payment_methods missing from app routes"
    )
    assert "/v1/deposits/create-checkout-session" in app_routes, (
        "/v1/deposits/create-checkout-session missing from app routes"
    )
    assert "/v1/deposits/subscriptions/me" in app_routes, (
        "/v1/deposits/subscriptions/me missing from app routes"
    )
    assert "/v1/payment_intents" in app_routes, (
        "/v1/payment_intents missing from app routes — simulator expects this path"
    )
    assert "/v1/payment_methods" in app_routes, (
        "/v1/payment_methods missing from app routes"
    )


def test_scheduled_transfers_has_get_route():
    """Verify transfers router supports GET /transfers/scheduled."""
    routes = [
        (getattr(r, "path", ""), tuple(getattr(r, "methods", [])))
        for r in transfers_router.routes
    ]
    
    get_scheduled = any(
        (path == "/transfers/scheduled" or path == "/scheduled") and "GET" in methods
        for path, methods in routes
    )
    assert get_scheduled, "GET /transfers/scheduled route missing from transfers router"
    
    # Explicitly check /transfers/scheduled supports GET
    has_transfers_scheduled_get = any(
        path == "/transfers/scheduled" and "GET" in methods
        for path, methods in routes
    )
    assert has_transfers_scheduled_get, (
        "GET /transfers/scheduled route missing (currently only POST or /scheduled exists)"
    )


def test_accounts_router_has_transactions_endpoint():
    """Verify accounts router supports GET /{account_id}/transactions."""
    routes = [
        (getattr(r, "path", ""), tuple(getattr(r, "methods", [])))
        for r in accounts_router.routes
    ]
    
    has_account_txs = any(
        (path == "/accounts/{account_id}/transactions" or path == "/{account_id}/transactions") and "GET" in methods
        for path, methods in routes
    )
    assert has_account_txs, (
        "GET /{account_id}/transactions missing from accounts router"
    )
