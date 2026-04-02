"""add_user_login_logs_table

Revision ID: add_login_logs_001
Revises: add_rbac_001
Create Date: 2026-04-02 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "add_login_logs_001"
down_revision: Union[str, None] = "add_rbac_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_login_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("isp", sa.String(length=100), nullable=True),
        sa.Column("login_at", sa.DateTime(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("fail_reason", sa.String(length=200), nullable=True),
    )
    op.create_index(
        "ix_user_login_log_user_login_at", "user_login_logs", ["user_id", "login_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_login_log_user_login_at", table_name="user_login_logs")
    op.drop_table("user_login_logs")
