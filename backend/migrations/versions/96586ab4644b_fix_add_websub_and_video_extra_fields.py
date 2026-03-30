"""fix_add_websub_and_video_extra_fields

Revision ID: 96586ab4644b
Revises: d14f54ba048a
Create Date: 2026-03-30 15:40:42.421168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '96586ab4644b'
down_revision: Union[str, None] = 'd14f54ba048a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # ---- videos extra columns (for ORM Video model) ----
    video_cols = [row[1] for row in bind.execute(text("PRAGMA table_info(videos)")).fetchall()]

    if "duration_secs" not in video_cols:
        op.add_column("videos", sa.Column("duration_secs", sa.Integer(), nullable=True))
    if "like_count" not in video_cols:
        op.add_column("videos", sa.Column("like_count", sa.BigInteger(), nullable=True))
    if "live_chat_id" not in video_cols:
        op.add_column("videos", sa.Column("live_chat_id", sa.String(length=100), nullable=True))
    if "scheduled_at" not in video_cols:
        op.add_column("videos", sa.Column("scheduled_at", sa.DateTime(), nullable=True))
    if "live_started_at" not in video_cols:
        op.add_column("videos", sa.Column("live_started_at", sa.DateTime(), nullable=True))
    if "live_ended_at" not in video_cols:
        op.add_column("videos", sa.Column("live_ended_at", sa.DateTime(), nullable=True))

    # ---- websub subscriptions table ----
    has_websub = bind.execute(
        text(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='websub_subscriptions'"
        )
    ).fetchone()

    if not has_websub:
        op.create_table(
            "websub_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
            sa.Column(
                "channel_id",
                sa.Integer(),
                sa.ForeignKey("channels.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("topic_url", sa.String(length=300), nullable=False),
            sa.Column("hub_url", sa.String(length=300), nullable=False),
            sa.Column("secret", sa.String(length=100), nullable=True),
            sa.Column("verified", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("subscribed_at", sa.DateTime(), nullable=True),
            sa.Column("last_push_at", sa.DateTime(), nullable=True),
            sa.Column("push_count", sa.Integer(), nullable=True, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()

    video_cols = [row[1] for row in bind.execute(text("PRAGMA table_info(videos)")).fetchall()]
    if "live_ended_at" in video_cols:
        op.drop_column("videos", "live_ended_at")
    if "live_started_at" in video_cols:
        op.drop_column("videos", "live_started_at")
    if "scheduled_at" in video_cols:
        op.drop_column("videos", "scheduled_at")
    if "live_chat_id" in video_cols:
        op.drop_column("videos", "live_chat_id")
    if "like_count" in video_cols:
        op.drop_column("videos", "like_count")
    if "duration_secs" in video_cols:
        op.drop_column("videos", "duration_secs")

    has_websub = bind.execute(
        text(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='websub_subscriptions'"
        )
    ).fetchone()

    if has_websub:
        op.drop_table("websub_subscriptions")
