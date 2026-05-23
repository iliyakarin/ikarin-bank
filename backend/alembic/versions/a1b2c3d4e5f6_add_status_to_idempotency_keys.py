"""add_status_to_idempotency_keys

Revision ID: a1b2c3d4e5f6
Revises: 2c95366b4974
Create Date: 2026-05-22 00:00:00.000000

Adds a status column to idempotency_keys to support two-phase idempotency:
  - 'pending'   — key created, operation in-flight
  - 'completed' — operation finished, response saved

Existing rows (created before this migration) default to 'completed' so they
remain valid cache entries and no data is lost.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '2c95366b4974'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("idempotency_keys")]
    if "status" not in columns:
        op.add_column(
            "idempotency_keys",
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="completed",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("idempotency_keys")]
    if "status" in columns:
        op.drop_column("idempotency_keys", "status")
