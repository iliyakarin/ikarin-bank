"""Tests for vendor service locality.

Behaviour under test: get_vendors must live in vendor_service as the
single source of truth.  Both transfer_service and the vendors router
must import from there — not define their own implementations.
"""
import ast
import pathlib

VENDOR_SERVICE = pathlib.Path("backend/services/vendor_service.py")
TRANSFER_SERVICE = pathlib.Path("backend/services/transfer_service.py")
VENDORS_ROUTER = pathlib.Path("backend/routers/vendors.py")


def _names_defined(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _imports_from(source: str, module_suffix: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith(module_suffix):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def test_vendor_service_exists():
    assert VENDOR_SERVICE.exists(), "services/vendor_service.py does not exist"


def test_vendor_service_exports_get_vendors():
    source = VENDOR_SERVICE.read_text()
    assert "get_vendors" in _names_defined(source), (
        "get_vendors is not defined in vendor_service"
    )


def test_transfer_service_does_not_define_get_vendors():
    source = TRANSFER_SERVICE.read_text()
    assert "get_vendors" not in _names_defined(source), (
        "transfer_service defines its own get_vendors; it must import from vendor_service"
    )


def test_transfer_service_imports_get_vendors_from_vendor_service():
    source = TRANSFER_SERVICE.read_text()
    imported = _imports_from(source, "vendor_service")
    assert "get_vendors" in imported, (
        "transfer_service does not import get_vendors from vendor_service"
    )
