"""add tenant environment column and environment_connections table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


tenant_environment_type = postgresql.ENUM("dev", "prod", name="tenant_environment")
tenant_environment_col = postgresql.ENUM(
    "dev", "prod", name="tenant_environment", create_type=False
)


def upgrade() -> None:
    tenant_environment_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "cloud_tenants",
        sa.Column("environment", tenant_environment_col, nullable=False, server_default="dev"),
    )
    op.alter_column("cloud_tenants", "environment", server_default=None)

    # Delegated-mode SSO config moves from per-tenant to per-(environment,
    # provider) - see EnvironmentConnection. No live tenant has completed a
    # popup login yet (last session's per-tenant design was never
    # exercised end-to-end), so this is a clean drop, not a data migration.
    op.drop_column("cloud_tenants", "sso_login_url")
    op.drop_column("cloud_tenants", "delegated_token_cache")

    op.create_table(
        "environment_connections",
        sa.Column("environment", tenant_environment_col, nullable=False),
        sa.Column(
            "provider",
            postgresql.ENUM("aws", "azure", "gcp", "oci", name="cloud_provider", create_type=False),
            nullable=False,
        ),
        sa.Column("sso_login_url", sa.String(length=500), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("extra_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("delegated_token_cache", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("environment", "provider", name="uq_env_connection"),
    )


def downgrade() -> None:
    op.drop_table("environment_connections")
    op.add_column(
        "cloud_tenants", sa.Column("delegated_token_cache", sa.Text(), nullable=True)
    )
    op.add_column(
        "cloud_tenants", sa.Column("sso_login_url", sa.String(length=500), nullable=True)
    )
    op.drop_column("cloud_tenants", "environment")
    tenant_environment_type.drop(op.get_bind(), checkfirst=True)
