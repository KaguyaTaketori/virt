"""add_bilibili_user_credentials

Revision ID: add_bilibili_user_creds
Revises: d0084d29372b
Create Date: 2026-04-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_bilibili_user_creds"
down_revision: Union[str, None] = "d0084d29372b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("bilibili_sessdata", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("bilibili_bili_jct", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("bilibili_buvid3", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("bilibili_dedeuserid", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "bilibili_dedeuserid")
    op.drop_column("users", "bilibili_buvid3")
    op.drop_column("users", "bilibili_bili_jct")
    op.drop_column("users", "bilibili_sessdata")
