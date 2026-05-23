"""Tests for ownership check locality.

Behaviour under test: a single get_owned_account function in account_service
must be the canonical ownership check.  Local re-implementations in routers
fragment the invariant (e.g. different HTTP status codes, missing ownership
filter) and make ownership bugs invisible.
"""
import ast
import pathlib

ACCOUNTS_ROUTER = pathlib.Path("backend/routers/accounts.py")
ACCOUNT_SERVICE = pathlib.Path("backend/services/account_service.py")
TRANSFER_SERVICE = pathlib.Path("backend/services/transfer_service.py")


def _names_defined(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _imports_from(source: str, module_suffix: str) -> set[str]:
    """Return all names imported from any module whose name ends with module_suffix."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith(module_suffix):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def test_account_service_exports_get_owned_account():
    """account_service must define get_owned_account."""
    source = ACCOUNT_SERVICE.read_text()
    assert "get_owned_account" in _names_defined(source), (
        "get_owned_account is not defined in account_service — add it there"
    )


def test_accounts_router_does_not_define_check_account_owner():
    """The router must not define its own ownership helper."""
    source = ACCOUNTS_ROUTER.read_text()
    assert "check_account_owner" not in _names_defined(source), (
        "accounts router still defines check_account_owner locally; "
        "it should import get_owned_account from account_service instead"
    )


def test_accounts_router_imports_get_owned_account_from_service():
    """The router must import get_owned_account from account_service."""
    source = ACCOUNTS_ROUTER.read_text()
    imported = _imports_from(source, "account_service")
    assert "get_owned_account" in imported, (
        "accounts router does not import get_owned_account from account_service"
    )
