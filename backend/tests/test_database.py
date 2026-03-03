import sys
import os
import pytest
from unittest.mock import MagicMock

def test_user_model_structure(mock_db_dependency):
    """
    Test that the User model has the correct table name and columns defined.
    """
    from backend.database import User

    # Verify Table Name
    assert User.__tablename__ == "users"

    # Verify ID Column
    # id = Column(Integer, primary_key=True, index=True)
    assert hasattr(User, "id")
    # User.id is a MockColumn instance
    # User.id.args[0] should be the type (Integer)
    assert User.id.args[0].name == "Integer"
    assert User.id.kwargs.get("primary_key") is True
    assert User.id.kwargs.get("index") is True

    # Verify First Name Column
    # first_name = Column(String(50), nullable=False)
    assert hasattr(User, "first_name")
    assert User.first_name.args[0].name == "String"
    assert User.first_name.args[0].args == (50,)
    assert User.first_name.kwargs.get("nullable") is False

    # Verify Last Name Column
    # last_name = Column(String(50), nullable=False)
    assert hasattr(User, "last_name")
    assert User.last_name.args[0].name == "String"
    assert User.last_name.args[0].args == (50,)
    assert User.last_name.kwargs.get("nullable") is False

    # Verify Email Column
    # email = Column(String(100), unique=True, index=True, nullable=False)
    assert hasattr(User, "email")
    assert User.email.args[0].name == "String"
    assert User.email.args[0].args == (100,)
    assert User.email.kwargs.get("unique") is True
    assert User.email.kwargs.get("index") is True
    assert User.email.kwargs.get("nullable") is False

    # Verify Password Hash Column
    # password_hash = Column(String(255), nullable=False)
    assert hasattr(User, "password_hash")
    assert User.password_hash.args[0].name == "String"
    assert User.password_hash.args[0].args == (255,)
    assert User.password_hash.kwargs.get("nullable") is False

    # Verify Created At Column
    # created_at = Column(DateTime, default=datetime.datetime.utcnow)
    assert hasattr(User, "created_at")
    assert User.created_at.args[0].name == "DateTime"
    assert "default" in User.created_at.kwargs

def test_account_model_structure(mock_db_dependency):
    """
    Test that the Account model has the correct structure.
    """
    from backend.database import Account

    assert Account.__tablename__ == "accounts"

    # id = Column(Integer, primary_key=True, index=True)
    assert Account.id.args[0].name == "Integer"
    assert Account.id.kwargs.get("primary_key") is True

    # user_id = Column(Integer, ForeignKey("users.id"))
    assert Account.user_id.args[0].name == "Integer"
    # ForeignKey is the second argument
    assert Account.user_id.args[1].name == "ForeignKey"
    assert Account.user_id.args[1].args == ("users.id",)

    # balance = Column(Numeric(15, 2), default=0.00)
    assert Account.balance.args[0].name == "Numeric"
    assert Account.balance.args[0].args == (15, 2)
    assert "default" in Account.balance.kwargs

def test_transaction_model_structure(mock_db_dependency):
    """
    Test that the Transaction model has the correct structure.
    """
    from backend.database import Transaction

    assert Transaction.__tablename__ == "transactions"

    # id = Column(String, primary_key=True)
    assert Transaction.id.args[0].name == "String"
    assert Transaction.id.kwargs.get("primary_key") is True

    # amount = Column(Numeric(15, 2))
    assert Transaction.amount.args[0].name == "Numeric"
    assert Transaction.amount.args[0].args == (15, 2)

    # status = Column(String, default="pending")
    assert Transaction.status.args[0].name == "String"
    assert Transaction.status.kwargs.get("default") == "pending"
