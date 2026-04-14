"""refactor_channel_fields_to_generic - 将 bilibili_* 字段重构为通用字段

Revision ID: refactor_channel_fields_generic
Revises: regenerate_channel_snowflake_ids
Create Date: 2026-04-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "refactor_channel_fields_generic"
down_revision: Union[str, None] = "regenerate_channel_snowflake_ids"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("channels", "bilibili_fans", new_column_name="follower_count")
    op.alter_column("channels", "bilibili_sign", new_column_name="bio")
    op.alter_column("channels", "bilibili_archive_count", new_column_name="video_count")
    op.alter_column("channels", "bilibili_following", new_column_name="following_count")

    op.drop_column("channels", "bilibili_face")

    op.add_column(
        "channels",
        sa.Column("extra_info", sa.JSON(), nullable=True),
    )
    op.add_column(
        "channels",
        sa.Column(
            "full_sync_completed", sa.Boolean(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "channels",
        sa.Column("full_sync_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("channels", "full_sync_at")
    op.drop_column("channels", "full_sync_completed")
    op.drop_column("channels", "extra_info")

    op.add_column(
        "channels",
        sa.Column("bilibili_face", sa.String(length=500), nullable=True),
    )

    op.alter_column("channels", "following_count", new_column_name="bilibili_following")
    op.alter_column("channels", "video_count", new_column_name="bilibili_archive_count")
    op.alter_column("channels", "bio", new_column_name="bilibili_sign")
    op.alter_column("channels", "follower_count", new_column_name="bilibili_fans")
