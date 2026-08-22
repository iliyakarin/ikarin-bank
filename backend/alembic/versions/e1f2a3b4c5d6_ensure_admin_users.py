"""ensure_admin_users

Revision ID: e1f2a3b4c5d6
Revises: 4d6b1e2c3f4a, a1b2c3d4e5f6
Create Date: 2026-08-22 15:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = ('4d6b1e2c3f4a', 'a1b2c3d4e5f6')
branch_labels = None
depends_on = None


def upgrade():
    # Ensure ikarin@admin.com is assigned the admin role
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE users 
        SET role = 'admin' 
        WHERE LOWER(email) = 'ikarin@admin.com';
    """))


def downgrade():
    pass
