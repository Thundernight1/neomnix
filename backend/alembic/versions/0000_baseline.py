"""Create the pre-cleanup schema on fresh installations.

Existing installations are preserved; the historical cleanup follows.
"""
from alembic import op
import sqlalchemy as sa
from src.db.models import Base

revision = "0000_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    for table, column, datatype in [
        ("scan_jobs", "completed_at", sa.DateTime()),
        ("scan_jobs", "final_intensity", sa.Integer()),
        ("tenants", "stripe_customer_id", sa.String()),
        ("tenants", "logo_url", sa.String()),
    ]:
        if column not in {item["name"] for item in inspector.get_columns(table)}:
            op.add_column(table, sa.Column(column, datatype, nullable=True))
    if "ix_tenants_stripe_customer_id" not in {item["name"] for item in inspector.get_indexes("tenants")}:
        op.create_index("ix_tenants_stripe_customer_id", "tenants", ["stripe_customer_id"], unique=True)
    if "subscriptions" not in inspector.get_table_names():
        op.create_table("subscriptions", sa.Column("id", sa.String(), primary_key=True),
                        sa.Column("tenant_id", sa.String()))
        op.create_index("ix_subscriptions_id", "subscriptions", ["id"])
        op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])


def downgrade():
    raise RuntimeError("Baseline rollback is intentionally blocked to preserve customer data")
