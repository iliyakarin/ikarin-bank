"""sync_production_schema

Revision ID: 2c95366b4974
Revises: f3e8b1d2c3f4
Create Date: 2026-03-18 21:38:52.651619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c95366b4974'
down_revision: Union[str, Sequence[str], None] = 'f3e8b1d2c3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to match models, ensuring idempotency."""
    conn = op.get_bind()
    from sqlalchemy.engine.reflection import Inspector
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # 1. Ensure contacts.contact_email is nullable
    if "contacts" in existing_tables:
        columns = inspector.get_columns("contacts")
        contact_email_col = next((c for c in columns if c["name"] == "contact_email"), None)
        if contact_email_col and not contact_email_col["nullable"]:
            op.alter_column('contacts', 'contact_email',
               existing_type=sa.String(length=100),
               nullable=True)
            print("Fixed contacts.contact_email: set to NULLABLE")

    # 2. Ensure all other tables exist (idempotent)
    # We'll use more targeted checks for common missing tables in production
    if "subscriptions" not in existing_tables:
        op.create_table('subscriptions',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('plan_name', sa.String(length=100), server_default='Karin Black', nullable=False),
            sa.Column('amount', sa.BigInteger(), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
            sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        print("Created subscriptions table")

    if "payment_requests" not in existing_tables:
        op.create_table('payment_requests',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('requester_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('target_email', sa.String(length=100), nullable=False),
            sa.Column('amount', sa.BigInteger(), nullable=False),
            sa.Column('purpose', sa.String(), nullable=True),
            sa.Column('status', sa.String(length=50), server_default='pending_target', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        print("Created payment_requests table")

    # 3. Ensure critical columns in accounts exist
    if "accounts" in existing_tables:
        columns = [c["name"] for c in inspector.get_columns("accounts")]
        if "account_uuid" not in columns:
            op.add_column('accounts', sa.Column('account_uuid', sa.String(length=36), nullable=True))
            op.create_index(op.f('ix_accounts_account_uuid'), 'accounts', ['account_uuid'], unique=True)
            print("Added account_uuid to accounts table")

def downgrade() -> None:
    """Downgrade schema (optional/noop for this sync)."""
    pass
