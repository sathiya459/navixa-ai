"""enforce one AWS tenant per connection (partial unique index)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-05 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AWS's delegated SSO session has no separate "tenant" concept the way
    # Azure AD does (see tenant_registry/aws_import.py's module docstring) -
    # it collapses to one CloudTenant per connection, with accounts as
    # scopes under it. Without a DB-level constraint, two near-simultaneous
    # "Add Tenant" imports (e.g. a fast double-click before the button's
    # disabled state takes effect) can both query "does a tenant exist for
    # this connection?", both see no, and both create one - this happened
    # in practice. This partial unique index (Azure/GCP/OCI still allow
    # multiple tenants per connection - only AWS is restricted) turns that
    # race into a clean IntegrityError the app can catch and recover from
    # by re-fetching the tenant that won the race.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cloud_tenants_aws_connection
        ON cloud_tenants (connection_id)
        WHERE provider = 'aws' AND connection_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_cloud_tenants_aws_connection")
