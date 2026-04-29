"""add updated_at to outbox

Revision ID: 4d6b1e2c3f4a
Revises: 2c95366b4974
Create Date: 2026-04-29 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '4d6b1e2c3f4a'
down_revision: Union[str, Sequence[str], None] = '2c95366b4974'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to match models, ensuring idempotency."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    tables_to_check = [
        "users", "subscriptions", "contacts", "scheduled_payments", 
        "outbox", "accounts", "payment_methods", "transactions", 
        "payment_requests", "idempotency_keys"
    ]

    for table in tables_to_check:
        if table in existing_tables:
            columns = [c["name"] for c in inspector.get_columns(table)]
            if "created_at" not in columns:
                op.add_column(table, sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
                print(f"Added created_at to {table} table")
            if "updated_at" not in columns:
                op.add_column(table, sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
                print(f"Added updated_at to {table} table")


def downgrade() -> None:
    """Downgrade schema."""
    pass

