"""create payment_methods table

Revision ID: c1d2e3f4a5b6
Revises: e1f2a3b4c5d6
Create Date: 2026-10-10 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    if "payment_methods" not in existing_tables:
        op.create_table(
            "payment_methods",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("gateway_pm_id", sa.String(length=100), unique=True, nullable=True),
            sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("card_number_encrypted", sa.String(length=255), nullable=False),
            sa.Column("expiry_date_encrypted", sa.String(length=255), nullable=False),
            sa.Column("cvc_encrypted", sa.String(length=255), nullable=True),
            sa.Column("cardholder_name_encrypted", sa.String(length=255), nullable=True),
            sa.Column("card_last_4", sa.String(length=4), nullable=False),
            sa.Column("card_brand", sa.String(length=20), server_default="unknown", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_payment_methods_id", "payment_methods", ["id"])
        op.create_index("ix_payment_methods_gateway_pm_id", "payment_methods", ["gateway_pm_id"])
        op.create_index("ix_payment_methods_account_id", "payment_methods", ["account_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    if "payment_methods" in inspector.get_table_names():
        op.drop_table("payment_methods")
