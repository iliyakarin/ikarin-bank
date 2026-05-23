"""Tests for transfers router structural contracts.

Behaviour under test: every transfer path must go through
emit_transactional_event so that Transaction, Outbox, AND Activity records
are all created.  A route that manually constructs Outbox rows bypasses the
seam and silently drops the activity log.
"""
import ast
import pathlib

ROUTER_PATH = pathlib.Path("backend/routers/transfers.py")


def _get_function_source(source: str, func_name: str) -> str:
    """Return the source text of the named async def, or empty string."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == func_name:
            return ast.get_source_segment(source, node) or ""
    return ""


def test_create_transfer_does_not_directly_instantiate_outbox():
    """create_transfer must not build Outbox rows manually."""
    source = ROUTER_PATH.read_text()
    func_src = _get_function_source(source, "create_transfer")
    assert func_src, "create_transfer not found in transfers router"
    assert "Outbox(" not in func_src, (
        "create_transfer directly instantiates Outbox — "
        "it must delegate to emit_transactional_event instead"
    )


def test_create_transfer_delegates_to_event_emitter():
    """create_transfer must call emit_transactional_event."""
    source = ROUTER_PATH.read_text()
    func_src = _get_function_source(source, "create_transfer")
    assert "emit_transactional_event" in func_src, (
        "create_transfer must call emit_transactional_event "
        "so that the Activity log is always written"
    )


def test_create_transfer_does_not_manually_add_transaction():
    """Transaction record creation must happen inside emit_transactional_event."""
    source = ROUTER_PATH.read_text()
    func_src = _get_function_source(source, "create_transfer")
    assert "Transaction(" not in func_src, (
        "create_transfer manually creates a Transaction record; "
        "this should be handled by emit_transactional_event"
    )
