"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-11-05
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def upgrade() -> None:
    # Use String for UUIDs on SQLite, native UUID on PostgreSQL
    if _is_sqlite():
        uuid_type = sa.String(36)
    else:
        from sqlalchemy.dialects.postgresql import UUID
        uuid_type = UUID(as_uuid=True)

    # ── categories ───────────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("subject", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_subject", "users", ["subject"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── documents ────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("owner_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("category_id", uuid_type, sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("current_version_id", uuid_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # ── document_versions ────────────────────────────────────────────────────
    op.create_table(
        "document_versions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("document_id", uuid_type, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("object_key", sa.String(255), nullable=False, unique=True),
        sa.Column("encrypted_dek", sa.Text, nullable=False),
        sa.Column("kek_version", sa.String(50), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("verified_content_type", sa.String(255), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("scan_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("uploader_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])

    # ── document_grants ──────────────────────────────────────────────────────
    op.create_table(
        "document_grants",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("document_id", uuid_type, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("grantee_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("grantor_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("permission", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.Text, nullable=False, server_default=""),
    )
    op.create_index("ix_document_grants_document_id", "document_grants", ["document_id"])
    op.create_index("ix_document_grants_grantee_id", "document_grants", ["grantee_id"])
    op.create_index("ix_document_grants_revoked_at", "document_grants", ["revoked_at"])

    # ── audit_events ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("sequence", sa.BigInteger, nullable=False, unique=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("outcome", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=True),
        sa.Column("target_id", sa.String(255), nullable=True),
        sa.Column("correlation_id", sa.String(255), nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_audit_events_sequence", "audit_events", ["sequence"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])

    # ── audit_checkpoints ────────────────────────────────────────────────────
    op.create_table(
        "audit_checkpoints",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("from_sequence", sa.BigInteger, nullable=False),
        sa.Column("to_sequence", sa.BigInteger, nullable=False),
        sa.Column("chain_head_hash", sa.String(64), nullable=False),
        sa.Column("event_count", sa.BigInteger, nullable=False),
        sa.Column("signature", sa.Text, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_checkpoints")
    op.drop_table("audit_events")
    op.drop_table("document_grants")
    op.drop_table("document_versions")
    op.drop_table("documents")
    op.drop_table("users")
    op.drop_table("categories")
