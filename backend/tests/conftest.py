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
    mock_sqlalchemy = MagicMock()
    mock_sqlalchemy.Column = MagicMock(side_effect=MockColumn)
    mock_sqlalchemy.Integer = MockType("Integer")
    mock_sqlalchemy.String = MockType("String")
    mock_sqlalchemy.Numeric = MockType("Numeric")
    mock_sqlalchemy.DateTime = MockType("DateTime")
    mock_sqlalchemy.ForeignKey = MockType("ForeignKey")
    mock_sqlalchemy.JSON = MockType("JSON")

    class MockBase:
        pass

    mock_declarative_base = MagicMock(return_value=MockBase)
    mock_sqlalchemy.ext.declarative.declarative_base = mock_declarative_base

    mock_postgresql = MagicMock()
    mock_postgresql.JSONB = MockType("JSONB")
    mock_sqlalchemy.dialects.postgresql = mock_postgresql

    modules_to_patch = {
        "sqlalchemy": mock_sqlalchemy,
        "sqlalchemy.ext.declarative": mock_sqlalchemy.ext.declarative,
        "sqlalchemy.orm": MagicMock(),
        "sqlalchemy.dialects.postgresql": mock_postgresql
    }

    if "backend.database" in sys.modules:
        del sys.modules["backend.database"]
    if "database" in sys.modules:
        del sys.modules["database"]


    # Make mocks support comparisons for SQLAlchemy filter building
    def mock_comp(*args, **kwargs): return MagicMock()
    
    # We can't easily add methods to single instances of MagicMock 
    # if they are already created, but we can configure the return values of special methods.
    
    # Actually, the best way is to do this for the specific models
    for model in [mock_database.Transaction, mock_database.Account, mock_database.User, mock_database.IdempotencyKey]:
        for attr in ['created_at', 'id', 'user_id', 'account_id', 'transaction_side', 'email', 'balance']:
            col = getattr(model, attr)
            col.__ge__.side_effect = mock_comp
            col.__le__.side_effect = mock_comp
            col.__gt__.side_effect = mock_comp
            col.__lt__.side_effect = mock_comp
            col.__eq__.side_effect = mock_comp
            col.__ne__.side_effect = mock_comp
            # Support .in_()
            col.in_.side_effect = mock_comp

    with patch.dict(sys.modules, modules_to_patch):
        yield mock_sqlalchemy

    if "backend.database" in sys.modules:
        del sys.modules["backend.database"]
    if "database" in sys.modules:
        del sys.modules["database"]

@pytest.fixture
def mock_fastapi_dependency():
    """
    Patches sys.modules to inject mock fastapi and other dependencies for API testing.
    """
    mock_fastapi = MagicMock()

    def passthrough_decorator(*args, **kwargs):
        def wrapper(func):
            return func
        return wrapper

    mock_app_instance = MagicMock()
    mock_app_instance.get.side_effect = passthrough_decorator
    mock_app_instance.post.side_effect = passthrough_decorator
    mock_app_instance.put.side_effect = passthrough_decorator
    mock_app_instance.delete.side_effect = passthrough_decorator
    mock_app_instance.patch.side_effect = passthrough_decorator
    mock_app_instance.add_middleware = MagicMock()

    mock_fastapi.FastAPI.return_value = mock_app_instance
    
    mock_router_instance = MagicMock()
    mock_router_instance.get.side_effect = passthrough_decorator
    mock_router_instance.post.side_effect = passthrough_decorator
    mock_router_instance.put.side_effect = passthrough_decorator
    mock_router_instance.delete.side_effect = passthrough_decorator
    mock_router_instance.patch.side_effect = passthrough_decorator
    
    mock_fastapi.APIRouter.return_value = mock_router_instance

    mock_fastapi.Depends = MagicMock()

    class MockHTTPException(Exception):
        def __init__(self, status_code, detail=None, headers=None):
            self.status_code = status_code
            self.detail = detail
            self.headers = headers
    mock_fastapi.HTTPException = MockHTTPException

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
    mock_database = MagicMock()

    mock_sqlalchemy = MagicMock()
    mock_sqlalchemy_orm = MagicMock()
    mock_sqlalchemy_ext = MagicMock()
    mock_sqlalchemy_ext_asyncio = MagicMock()
    mock_sqlalchemy_exc = MagicMock()

    mock_sync_checker = MagicMock()

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
        "backend.database": mock_database,
        "database": mock_database,
        "sqlalchemy": mock_sqlalchemy,
        "sqlalchemy.orm": mock_sqlalchemy_orm,
        "sqlalchemy.ext": mock_sqlalchemy_ext,
        "sqlalchemy.ext.asyncio": mock_sqlalchemy_ext_asyncio,
        "sqlalchemy.exc": mock_sqlalchemy_exc,
        "sync_checker": mock_sync_checker,
        "backend.sync_checker": mock_sync_checker
    }

    if "main" in sys.modules:
        del sys.modules["main"]

    for m in list(sys.modules.keys()):
        if m.startswith("backend.routers") or m.startswith("routers.") or m.startswith("backend.services") or m.startswith("services."):
            del sys.modules[m]



    # Make mocks support comparisons for SQLAlchemy filter building
    def mock_comp(*args, **kwargs): return MagicMock()
    
    # We can't easily add methods to single instances of MagicMock 
    # if they are already created, but we can configure the return values of special methods.
    
    # Actually, the best way is to do this for the specific models
    for model in [mock_database.Transaction, mock_database.Account, mock_database.User, mock_database.IdempotencyKey]:
        for attr in ['created_at', 'id', 'user_id', 'account_id', 'transaction_side', 'email', 'balance']:
            col = getattr(model, attr)
            col.__ge__.side_effect = mock_comp
            col.__le__.side_effect = mock_comp
            col.__gt__.side_effect = mock_comp
            col.__lt__.side_effect = mock_comp
            col.__eq__.side_effect = mock_comp
            col.__ne__.side_effect = mock_comp
            # Support .in_()
            col.in_.side_effect = mock_comp

    with patch.dict(sys.modules, modules_to_patch):
        import main
        main.HTTPException = MockHTTPException
        yield main

    if "main" in sys.modules:
        del sys.modules["main"]

    for m in list(sys.modules.keys()):
        if m.startswith("backend.routers") or m.startswith("routers.") or m.startswith("backend.services") or m.startswith("services."):
            del sys.modules[m]

