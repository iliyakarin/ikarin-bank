import sys
import pytest
from unittest.mock import MagicMock, patch
import os

# Set SECRET_KEY before importing main
os.environ["SECRET_KEY"] = "test_secret_key"

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

@pytest.fixture
def mock_fastapi_dependency():
    """
    Patches sys.modules to inject mock fastapi and other dependencies for API testing.
    """
    mock_fastapi = MagicMock()
    mock_fastapi.FastAPI = MagicMock()
    mock_fastapi.Depends = MagicMock()
    mock_fastapi.HTTPException = MagicMock()
    mock_fastapi.BackgroundTasks = MagicMock()
    mock_fastapi.Request = MagicMock()

    mock_middleware = MagicMock()
    mock_fastapi.middleware = mock_middleware
    mock_fastapi.middleware.cors = MagicMock()

    mock_security = MagicMock()
    mock_fastapi.security = mock_security
    mock_security.OAuth2PasswordBearer = MagicMock()
    mock_security.OAuth2PasswordRequestForm = MagicMock()

    mock_jose = MagicMock()
    mock_passlib = MagicMock()
    mock_passlib.context = MagicMock()

    mock_kafka = MagicMock()
    mock_kafka.AIOKafkaProducer = MagicMock()

    mock_confluent = MagicMock()
    mock_confluent.admin = MagicMock()
    mock_confluent.Consumer = MagicMock()

    mock_clickhouse = MagicMock()
    mock_pydantic = MagicMock()
    mock_database = MagicMock()

    # We also need to mock sqlalchemy for main.py imports
    mock_sqlalchemy = MagicMock()
    mock_sqlalchemy.orm = MagicMock()
    mock_sqlalchemy.func = MagicMock()

    modules_to_patch = {
        "fastapi": mock_fastapi,
        "fastapi.middleware": mock_middleware,
        "fastapi.middleware.cors": mock_fastapi.middleware.cors,
        "fastapi.security": mock_security,
        "jose": mock_jose,
        "passlib": mock_passlib,
        "passlib.context": mock_passlib.context,
        "aiokafka": mock_kafka,
        "confluent_kafka": mock_confluent,
        "confluent_kafka.admin": mock_confluent.admin,
        "clickhouse_connect": mock_clickhouse,
        "pydantic": mock_pydantic,
        "backend.database": mock_database,
        "database": mock_database,
        "sqlalchemy": mock_sqlalchemy,
        "sqlalchemy.orm": mock_sqlalchemy.orm
    }

    # Ensure backend.main is reloaded
    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]

    with patch.dict(sys.modules, modules_to_patch):
        # We verify that we can import main
        import backend.main
        yield backend.main

    if "backend.main" in sys.modules:
        del sys.modules["backend.main"]
