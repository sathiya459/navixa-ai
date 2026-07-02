"""add delegated_token_cache to cloud_tenants

Revision ID: d4e5f6a7b8c9
Revises: c2f9a1b8e7d3
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c2f9a1b8e7d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('cloud_tenants', sa.Column('delegated_token_cache', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('cloud_tenants', 'delegated_token_cache')
