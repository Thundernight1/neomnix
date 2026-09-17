"""Enforce unambiguous login identities.

Duplicate legacy identities block migration; resolve them explicitly rather
than deleting customer data or choosing an arbitrary account.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_unique_user_email"
down_revision = "1e518a1fd67f"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    duplicates = bind.execute(sa.text(
        "SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates:
        raise RuntimeError("Duplicate login emails exist; reconcile identities before migrating")
    op.create_index("uq_users_email", "users", ["email"], unique=True)


def downgrade():
    op.drop_index("uq_users_email", table_name="users")
