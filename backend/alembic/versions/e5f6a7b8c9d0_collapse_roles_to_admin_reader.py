"""collapse auditor/viewer roles into a single reader role

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Rename viewer -> reader (keeps existing user_role assignments intact).
    conn.execute(sa.text("UPDATE roles SET name = 'reader' WHERE name = 'viewer'"))

    # Ensure a reader role row exists even if 'viewer' never did.
    conn.execute(
        sa.text(
            "INSERT INTO roles (id, name) SELECT gen_random_uuid(), 'reader' "
            "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'reader')"
        )
    )

    # Reassign anyone holding 'auditor' to 'reader' instead, then drop the
    # now-unused auditor role row (ON DELETE CASCADE on user_roles handles
    # the join rows).
    reader_id = conn.execute(sa.text("SELECT id FROM roles WHERE name = 'reader'")).scalar()
    auditor_id = conn.execute(sa.text("SELECT id FROM roles WHERE name = 'auditor'")).scalar()
    if auditor_id is not None:
        conn.execute(
            sa.text(
                "INSERT INTO user_roles (user_id, role_id) "
                "SELECT user_id, :reader_id FROM user_roles WHERE role_id = :auditor_id "
                "ON CONFLICT DO NOTHING"
            ),
            {"reader_id": reader_id, "auditor_id": auditor_id},
        )
        conn.execute(sa.text("DELETE FROM roles WHERE id = :auditor_id"), {"auditor_id": auditor_id})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE roles SET name = 'viewer' WHERE name = 'reader'"))
    conn.execute(
        sa.text(
            "INSERT INTO roles (id, name) SELECT gen_random_uuid(), 'auditor' "
            "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = 'auditor')"
        )
    )
