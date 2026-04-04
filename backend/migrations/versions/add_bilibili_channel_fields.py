"""add_bilibili_channel_fields

Revision ID: add_bilibili_fields_001
Revises: add_rbac_001
Create Date: 2026-04-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_bilibili_fields_001"
down_revision: Union[str, None] = "add_rbac_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "channels",
        sa.Column("bilibili_fans", sa.Integer(), nullable=True),
    )
    op.add_column(
        "channels",
        sa.Column("bilibili_sign", sa.Text(), nullable=True),
    )
    op.add_column(
        "channels",
        sa.Column("bilibili_archive_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "channels",
        sa.Column("bilibili_face", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "channels",
        sa.Column("bilibili_following", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("channels", "bilibili_following")
    op.drop_column("channels", "bilibili_face")
    op.drop_column("channels", "bilibili_archive_count")
    op.drop_column("channels", "bilibili_sign")
    op.drop_column("channels", "bilibili_fans")
