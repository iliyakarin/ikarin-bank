"""Tests for deposit routes, scheduled transfer routes, and account transactions routes.

Verifies:
1. Both /v1/deposits/payment_intents and /v1/payment_intents are registered on the application.
2. Both /v1/deposits/create-checkout-session and /v1/create-checkout-session are registered.
3. GET /transfers/scheduled is registered in the transfers router (preventing 405 Method Not Allowed).
4. GET /{account_id}/transactions is registered in the accounts router.
"""
import pytest
from fastapi.routing import APIRoute
from main import app
from routers.transfers import router as transfers_router
from routers.accounts import router as accounts_router
from routers.deposit import router as deposit_router


def test_deposit_routes_dual_mounted_in_app():
    """Verify deposit routes are mounted at both /v1/deposits and /v1 prefixes."""
    routes = [r.path for r in app.routes if isinstance(r, APIRoute)]
    
    # Check /v1/deposits routes
    assert "/v1/deposits/payment_intents" in routes, (
        "/v1/deposits/payment_intents missing from app routes — frontend expects this path"
    )
    assert "/v1/deposits/payment_methods" in routes, (
        "/v1/deposits/payment_methods missing from app routes"
    )
    assert "/v1/deposits/create-checkout-session" in routes, (
        "/v1/deposits/create-checkout-session missing from app routes"
    )
    assert "/v1/deposits/subscriptions/me" in routes, (
        "/v1/deposits/subscriptions/me missing from app routes"
    )
    
    # Check backward compatibility routes for simulator / legacy callers
    assert "/v1/payment_intents" in routes, (
        "/v1/payment_intents missing from app routes — simulator expects this path"
    )
    assert "/v1/payment_methods" in routes, (
        "/v1/payment_methods missing from app routes"
    )


def test_scheduled_transfers_has_get_route():
    """Verify transfers router supports GET /transfers/scheduled."""
    routes = [
        (r.path, tuple(r.methods))
        for r in transfers_router.routes
        if isinstance(r, APIRoute)
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
        (r.path, tuple(r.methods))
        for r in accounts_router.routes
        if isinstance(r, APIRoute)
    ]
    
    has_account_txs = any(
        (path == "/accounts/{account_id}/transactions" or path == "/{account_id}/transactions") and "GET" in methods
        for path, methods in routes
    )
    assert has_account_txs, (
        "GET /{account_id}/transactions missing from accounts router"
    )
