"""drop scheduled_discoveries, resource_changes (NAVIXA Watch removed)

Revision ID: a1b2c3d4e5f7
Revises: c3d4e5f6a7b8
Create Date: 2026-07-08 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f7'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('resource_changes')
    op.drop_table('scheduled_discoveries')
    sa.Enum(name='resource_change_type').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.create_table('scheduled_discoveries',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('scope_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('interval_minutes', sa.Integer(), nullable=False),
    sa.Column('hub_selection', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['cloud_tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('resource_changes',
    sa.Column('audit_job_id', sa.UUID(), nullable=False),
    sa.Column('compared_to_audit_job_id', sa.UUID(), nullable=False),
    sa.Column('resource_type', sa.String(length=50), nullable=False),
    sa.Column('native_id', sa.String(length=255), nullable=False),
    sa.Column('change_type', sa.Enum('added', 'removed', 'modified', name='resource_change_type'), nullable=False),
    sa.Column('previous_attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('current_attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['audit_job_id'], ['audit_jobs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['compared_to_audit_job_id'], ['audit_jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
