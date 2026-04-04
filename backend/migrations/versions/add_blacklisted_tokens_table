"""add_blacklisted_tokens_table

Revision ID: add_blacklisted_tokens
Revises: add_group_and_status_fields
Create Date: 2026-04-04

修复内容：
  [致命] JWT Token 无法撤销：添加 blacklisted_tokens 表存储已撤销的 Token。
  token_blacklist.py 服务在启动时将此表加载到内存，实现 O(1) 撤销检查。
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "add_blacklisted_tokens"
down_revision: Union[str, None] = "add_group_and_status_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blacklisted_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expired_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_blacklisted_tokens_jti",
        "blacklisted_tokens",
        ["jti"],
        unique=True,
    )
    op.create_index(
        "ix_blacklisted_tokens_expired_at",
        "blacklisted_tokens",
        ["expired_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_blacklisted_tokens_expired_at", table_name="blacklisted_tokens")
    op.drop_index("ix_blacklisted_tokens_jti", table_name="blacklisted_tokens")
    op.drop_table("blacklisted_tokens")