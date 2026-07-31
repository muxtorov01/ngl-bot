"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role = sa.Enum("user", "premium", "super_admin", name="user_role")
    message_type = sa.Enum("text", "photo", "voice", name="message_type")
    message_direction = sa.Enum("inbound", "reply", name="message_direction")
    payment_status = sa.Enum("pending", "paid", "failed", "refunded", name="payment_status")
    report_status = sa.Enum("open", "reviewed", "dismissed", name="report_status")
    broadcast_status = sa.Enum("pending", "running", "done", "failed", name="broadcast_status")

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("full_name", sa.String(256), nullable=True),
        sa.Column("role", user_role, nullable=False, server_default="user"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("premium_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_link_token", sa.String(64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])
    op.create_index("ix_users_active_link_token", "users", ["active_link_token"])

    op.create_table(
        "plans",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("stars_price", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plans_code", "plans", ["code"])

    op.create_table(
        "link_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_link_tokens_owner_id", "link_tokens", ["owner_id"])
    op.create_index("ix_link_tokens_token", "link_tokens", ["token"])

    op.create_table(
        "message_threads",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("receiver_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_message_threads_receiver_id", "message_threads", ["receiver_id"])
    op.create_index("ix_message_threads_sender_telegram_id", "message_threads", ["sender_telegram_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("thread_id", sa.BigInteger(), sa.ForeignKey("message_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receiver_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_username", sa.String(64), nullable=True),
        sa.Column("sender_full_name", sa.String(256), nullable=True),
        sa.Column("direction", message_direction, nullable=False),
        sa.Column("message_type", message_type, nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("file_id", sa.String(256), nullable=True),
        sa.Column("voice_duration", sa.BigInteger(), nullable=True),
        sa.Column("delivered_chat_message_id", sa.BigInteger(), nullable=True),
        sa.Column("can_reveal_sender", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_answered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_reported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"])
    op.create_index("ix_messages_receiver_id", "messages", ["receiver_id"])
    op.create_index("ix_messages_sender_telegram_id", "messages", ["sender_telegram_id"])
    op.create_index("ix_messages_delivered_chat_message_id", "messages", ["delivered_chat_message_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("stars_amount", sa.Integer(), nullable=False),
        sa.Column("status", payment_status, nullable=False, server_default="pending"),
        sa.Column("telegram_payment_charge_id", sa.String(256), nullable=True, unique=True),
        sa.Column("invoice_payload", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_plan_id", "payments", ["plan_id"])

    op.create_table(
        "premium_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_id", sa.BigInteger(), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("plan_id", sa.BigInteger(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_premium_events_user_id", "premium_events", ["user_id"])

    op.create_table(
        "blocks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("blocked_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_blocks_owner_id", "blocks", ["owner_id"])
    op.create_index("ix_blocks_blocked_telegram_id", "blocks", ["blocked_telegram_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("message_id", sa.BigInteger(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reporter_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", report_status, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reports_message_id", "reports", ["message_id"])
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("photo_file_id", sa.String(256), nullable=True),
        sa.Column("status", broadcast_status, nullable=False, server_default="pending"),
        sa.Column("total_targets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "broadcast_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("broadcast_id", sa.BigInteger(), sa.ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_broadcast_logs_broadcast_id", "broadcast_logs", ["broadcast_id"])
    op.create_index("ix_broadcast_logs_user_id", "broadcast_logs", ["user_id"])

    op.create_table(
        "settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("broadcast_logs")
    op.drop_table("broadcasts")
    op.drop_table("reports")
    op.drop_table("blocks")
    op.drop_table("premium_events")
    op.drop_table("payments")
    op.drop_table("messages")
    op.drop_table("message_threads")
    op.drop_table("link_tokens")
    op.drop_table("plans")
    op.drop_table("users")

    sa.Enum(name="broadcast_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="report_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="payment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="message_direction").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="message_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
