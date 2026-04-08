"""add_bilibili_dynamics_table

Revision ID: add_bilibili_dynamics
Revises: c67d89f3ec8e
Create Date: 2026-04-07 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_bilibili_dynamics"
down_revision: Union[str, None] = "c67d89f3ec8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bilibili_dynamics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("dynamic_id", sa.String(length=50), nullable=False),
        sa.Column("uid", sa.String(length=50), nullable=True),
        sa.Column("uname", sa.String(length=100), nullable=True),
        sa.Column("face", sa.String(length=500), nullable=True),
        sa.Column("type", sa.Integer(), nullable=True),
        sa.Column("content_nodes", sa.Text(), nullable=True),
        sa.Column("images", sa.Text(), nullable=True),
        sa.Column("repost_content", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("stat", sa.Text(), nullable=True),
        sa.Column("topic", sa.String(length=200), nullable=True),
        sa.Column("is_top", sa.Boolean(), nullable=True),
        sa.Column("raw_data", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dynamic_id"),
    )
    op.create_index(
        "ix_bilibili_dynamics_channel_id", "bilibili_dynamics", ["channel_id"]
    )
    op.create_index(
        "ix_bilibili_dynamics_channel_published",
        "bilibili_dynamics",
        ["channel_id", "published_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bilibili_dynamics_channel_published", table_name="bilibili_dynamics"
    )
    op.drop_index("ix_bilibili_dynamics_channel_id", table_name="bilibili_dynamics")
    op.drop_table("bilibili_dynamics")
