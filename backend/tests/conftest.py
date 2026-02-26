import sys
import pytest
from unittest.mock import MagicMock, patch

# Define Mock classes to capture arguments
class MockColumn:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

class MockType:
    def __init__(self, name=None, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        # Allow calling types like String(50) to return a new instance with args
        # Propagate the name
        return MockType(self.name, *args, **kwargs)

    def __repr__(self):
        return f"MockType(name={self.name}, args={self.args}, kwargs={self.kwargs})"

    def __eq__(self, other):
        if isinstance(other, MockType):
            return self.name == other.name and self.args == other.args and self.kwargs == other.kwargs
        return False

@pytest.fixture
def mock_db_dependency():
    """
    Patches sys.modules to inject mock sqlalchemy and other dependencies.
    Yields the mock objects for verification.
    """
    # Create the main mock object for sqlalchemy
    mock_sqlalchemy = MagicMock()

    # Set up Column mock
    mock_sqlalchemy.Column = MagicMock(side_effect=MockColumn)

    # Set up Type mocks
    mock_sqlalchemy.Integer = MockType("Integer")
    mock_sqlalchemy.String = MockType("String")
    mock_sqlalchemy.Numeric = MockType("Numeric")
    mock_sqlalchemy.DateTime = MockType("DateTime")
    mock_sqlalchemy.ForeignKey = MockType("ForeignKey")
    mock_sqlalchemy.JSON = MockType("JSON")

    # Mock declarative_base
    class MockBase:
        pass

    mock_declarative_base = MagicMock(return_value=MockBase)
    mock_sqlalchemy.ext.declarative.declarative_base = mock_declarative_base

    # Mock JSONB for postgresql dialect
    mock_postgresql = MagicMock()
    mock_postgresql.JSONB = MockType("JSONB")
    mock_sqlalchemy.dialects.postgresql = mock_postgresql

    # Patch sys.modules
    modules_to_patch = {
        "sqlalchemy": mock_sqlalchemy,
        "sqlalchemy.ext.declarative": mock_sqlalchemy.ext.declarative,
        "sqlalchemy.orm": MagicMock(),
        "sqlalchemy.dialects.postgresql": mock_postgresql
    }

    # Ensure backend.database is reloaded for each test
    if "backend.database" in sys.modules:
        del sys.modules["backend.database"]

    with patch.dict(sys.modules, modules_to_patch):
        yield mock_sqlalchemy

    # Clean up backend.database to avoid polluting other tests
    if "backend.database" in sys.modules:
        del sys.modules["backend.database"]
