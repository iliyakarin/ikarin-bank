import sys
import pytest
from unittest.mock import MagicMock, patch

# No longer needing to define fixture here, using the one from conftest.py

def test_admin_stats_exists(mock_fastapi_dependency):
    """
    Test that the /admin/stats endpoint is defined.
    """
    # mock_fastapi_dependency returns the mocked backend.main module
    app_module = mock_fastapi_dependency
    app = app_module.app

    found_stats = False

    # Check calls to app.get
    for call in app.get.call_args_list:
        args, kwargs = call
        if args and args[0] == "/v1/admin/stats":
            found_stats = True

    assert found_stats, "Could not find /admin/stats endpoint definition"

def test_metrics_removal_verification(mock_fastapi_dependency):
    """
    Test that ensures /admin/metrics is NOT present (after we remove it).
    """
    app_module = mock_fastapi_dependency
    app = app_module.app

    found_metrics = False
    for call in app.get.call_args_list:
        args, kwargs = call
        if args and args[0] == "/admin/metrics":
            found_metrics = True

    assert not found_metrics, "/admin/metrics endpoint should be removed"
