"""add ai_analysis value to finding_module enum

Revision ID: c2f9a1b8e7d3
Revises: ddc13cb00a79
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c2f9a1b8e7d3'
down_revision = 'ddc13cb00a79'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside the same transaction that
    # also uses the new value, but is safe on its own (Postgres 12+).
    # AUTOCOMMIT isolation avoids Alembic's wrapping transaction for this
    # single statement.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE finding_module ADD VALUE IF NOT EXISTS 'ai_analysis'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums; downgrading would require
    # recreating the type, which is out of scope for this additive change.
    pass
