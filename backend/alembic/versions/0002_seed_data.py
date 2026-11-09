"""Seed demo data — categories and placeholder users

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05
"""

from typing import Sequence, Union
from datetime import datetime, UTC

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_ID  = "00000000-0000-0000-0000-000000000001"
ALICE_ID  = "00000000-0000-0000-0000-000000000002"
BOB_ID    = "00000000-0000-0000-0000-000000000003"
CAROL_ID  = "00000000-0000-0000-0000-000000000004"

CATEGORY_FINANCE = "10000000-0000-0000-0000-000000000001"
CATEGORY_LEGAL   = "10000000-0000-0000-0000-000000000002"
CATEGORY_HR      = "10000000-0000-0000-0000-000000000003"


def upgrade() -> None:
    now = datetime.now(UTC).isoformat()
    conn = op.get_bind()

    conn.execute(sa.text(
        "INSERT INTO categories (id, name, description, created_at) VALUES "
        "(:f_id, 'Finance', 'Financial documents', :now)"
    ), {"f_id": CATEGORY_FINANCE, "now": now})

    conn.execute(sa.text(
        "INSERT INTO categories (id, name, description, created_at) VALUES "
        "(:l_id, 'Legal', 'Legal documents', :now)"
    ), {"l_id": CATEGORY_LEGAL, "now": now})

    conn.execute(sa.text(
        "INSERT INTO categories (id, name, description, created_at) VALUES "
        "(:h_id, 'HR', 'HR documents', :now)"
    ), {"h_id": CATEGORY_HR, "now": now})

    users = [
        (ADMIN_ID,  "demo-admin-subject", "admin@trustvault.local", "TrustVault Admin",  "admin",  1),
        (ALICE_ID,  "demo-alice-subject", "alice@trustvault.local", "Alice (Owner)",     "owner",  1),
        (BOB_ID,    "demo-bob-subject",   "bob@trustvault.local",   "Bob (Viewer)",      "viewer", 1),
        (CAROL_ID,  "demo-carol-subject", "carol@trustvault.local", "Carol (No Access)", "viewer", 1),
    ]
    for uid, subject, email, display_name, role, is_active in users:
        conn.execute(sa.text(
            "INSERT INTO users (id, subject, email, display_name, role, is_active, created_at, updated_at) "
            "VALUES (:id, :subject, :email, :display_name, :role, :is_active, :now, :now)"
        ), {"id": uid, "subject": subject, "email": email,
            "display_name": display_name, "role": role,
            "is_active": is_active, "now": now})


def downgrade() -> None:
    conn = op.get_bind()
    for uid in (ADMIN_ID, ALICE_ID, BOB_ID, CAROL_ID):
        conn.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": uid})
    for cid in (CATEGORY_FINANCE, CATEGORY_LEGAL, CATEGORY_HR):
        conn.execute(sa.text("DELETE FROM categories WHERE id = :id"), {"id": cid})
