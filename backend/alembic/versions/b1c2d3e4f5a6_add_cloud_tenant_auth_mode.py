"""add cloud tenant auth mode and app registration fields

Revision ID: b1c2d3e4f5a6
Revises: a903175f9941
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a903175f9941'
branch_labels = None
depends_on = None


def upgrade() -> None:
    cloud_auth_mode = sa.Enum('delegated', 'app_only', name='cloud_auth_mode')
    cloud_auth_mode.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'cloud_tenants',
        sa.Column('auth_mode', cloud_auth_mode, nullable=False, server_default='delegated'),
    )
    op.add_column(
        'cloud_tenants',
        sa.Column('app_registration_client_id', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'cloud_tenants',
        sa.Column('app_registration_tenant_id', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'cloud_tenants',
        sa.Column('app_registration_redirect_uri', sa.String(length=500), nullable=True),
    )
    # Drop the server_default after backfilling existing rows - new rows
    # should rely on the ORM-level default going forward, not a DB default.
    op.alter_column('cloud_tenants', 'auth_mode', server_default=None)


def downgrade() -> None:
    op.drop_column('cloud_tenants', 'app_registration_redirect_uri')
    op.drop_column('cloud_tenants', 'app_registration_tenant_id')
    op.drop_column('cloud_tenants', 'app_registration_client_id')
    op.drop_column('cloud_tenants', 'auth_mode')

    cloud_auth_mode = sa.Enum('delegated', 'app_only', name='cloud_auth_mode')
    cloud_auth_mode.drop(op.get_bind(), checkfirst=True)
