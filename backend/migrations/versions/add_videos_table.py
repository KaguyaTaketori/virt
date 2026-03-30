"""add_videos_table

Revision ID: add_videos_table
Revises: add_users_and_channel_fields
Create Date: 2026-03-30

"""

from alembic import op
import sqlalchemy as sa


revision = "add_videos_table"
down_revision = "add_users_and_channel_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column(
            "platform", sa.Enum("YOUTUBE", "BILIBILI", name="platform"), nullable=False
        ),
        sa.Column("video_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("duration", sa.String(length=20), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True, default=0),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True, default="archive"),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["channels.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_videos_video_id", "videos", ["video_id"])
    op.create_index(
        "ix_videos_channel_published", "videos", ["channel_id", "published_at"]
    )
    op.create_index(
        "ix_videos_unique", "videos", ["channel_id", "video_id"], unique=True
    )

    op.add_column(
        "channels", sa.Column("videos_last_fetched", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("channels", "videos_last_fetched")

    op.drop_index("ix_videos_unique", table_name="videos")
    op.drop_index("ix_videos_channel_published", table_name="videos")
    op.drop_index("ix_videos_video_id", table_name="videos")
    op.drop_table("videos")
