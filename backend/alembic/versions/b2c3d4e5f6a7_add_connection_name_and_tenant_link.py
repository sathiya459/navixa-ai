"""add name to environment_connections, allow multiple per provider, link cloud_tenants to their connection

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "environment_connections",
        sa.Column("name", sa.String(length=255), nullable=True),
    )
    # Backfill: today's data is guaranteed one row per (environment,
    # provider), so a provider-derived default label is safe and unique.
    op.execute(
        "UPDATE environment_connections SET name = provider || ' connection' WHERE name IS NULL"
    )
    op.alter_column("environment_connections", "name", nullable=False)

    op.drop_constraint("uq_env_connection", "environment_connections", type_="unique")
    op.create_unique_constraint(
        "uq_env_connection_name", "environment_connections", ["environment", "provider", "name"]
    )

    op.add_column(
        "cloud_tenants",
        sa.Column("connection_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_cloud_tenants_connection_id",
        "cloud_tenants",
        "environment_connections",
        ["connection_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Backfill existing delegated-mode tenants to the single pre-existing
    # connection for their (environment, provider) - was guaranteed 1:1
    # before this migration.
    op.execute(
        """
        UPDATE cloud_tenants t
        SET connection_id = ec.id
        FROM environment_connections ec
        WHERE t.environment = ec.environment
          AND t.provider = ec.provider
          AND t.connection_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_cloud_tenants_connection_id", "cloud_tenants", type_="foreignkey")
    op.drop_column("cloud_tenants", "connection_id")

    op.drop_constraint("uq_env_connection_name", "environment_connections", type_="unique")
    op.create_unique_constraint(
        "uq_env_connection", "environment_connections", ["environment", "provider"]
    )
    op.drop_column("environment_connections", "name")
