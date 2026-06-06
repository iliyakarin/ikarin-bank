"""add role to users

Revision ID: d9cc355b125e
Revises:
Create Date: 2023-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9cc355b125e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('role', sa.String(length=20), server_default='user', nullable=False))


def downgrade():
    op.drop_column('users', 'role')
