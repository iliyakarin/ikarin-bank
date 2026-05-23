"""Tests for two-phase idempotency structural contracts.

Behaviour under test:
- IdempotencyKey model must have a status column
- idempotency module must expose complete_idempotency
- The transfers router must call complete_idempotency after a successful transfer
  so that a replayed request gets the original response rather than a generic skip
"""
import ast
import pathlib

IDEMPOTENCY_MODULE = pathlib.Path("backend/idempotency.py")
TRANSFERS_ROUTER = pathlib.Path("backend/routers/transfers.py")
TRANSACTION_MODEL = pathlib.Path("backend/models/transaction.py")


def _names_defined(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _get_class_source(source: str, class_name: str) -> str:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return ast.get_source_segment(source, node) or ""
    return ""


def _imports_from(source: str, module_suffix: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith(module_suffix):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def test_idempotency_key_model_has_status_column():
    """IdempotencyKey model must define a status column."""
    source = TRANSACTION_MODEL.read_text()
    class_src = _get_class_source(source, "IdempotencyKey")
    assert class_src, "IdempotencyKey class not found in models/transaction.py"
    assert "status" in class_src, (
        "IdempotencyKey model missing 'status' column — needed for two-phase idempotency"
    )


def test_idempotency_module_exports_complete_idempotency():
    """idempotency.py must define complete_idempotency for phase 2."""
    source = IDEMPOTENCY_MODULE.read_text()
    assert "complete_idempotency" in _names_defined(source), (
        "idempotency module does not define complete_idempotency"
    )


def test_transfers_router_imports_complete_idempotency():
    """The transfers router must import complete_idempotency to record responses."""
    source = TRANSFERS_ROUTER.read_text()
    imported = _imports_from(source, "idempotency")
    assert "complete_idempotency" in imported, (
        "transfers router does not import complete_idempotency from idempotency module"
    )


def test_p2p_transfer_calls_complete_idempotency():
    """create_p2p_transfer must call complete_idempotency after success."""
    source = TRANSFERS_ROUTER.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "create_p2p_transfer":
            func_src = ast.get_source_segment(source, node) or ""
            assert "complete_idempotency" in func_src, (
                "create_p2p_transfer does not call complete_idempotency — "
                "replay requests will get a generic skip instead of the original response"
            )
            return
    assert False, "create_p2p_transfer not found in transfers router"
