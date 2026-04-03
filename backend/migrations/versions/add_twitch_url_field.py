"""add_twitch_url_field

Revision ID: add_twitch_url_field
Revises: add_users_and_channel_fields
Create Date: 2026-04-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_twitch_url_field"
down_revision: Union[str, None] = "add_login_logs_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("channels", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("twitch_url", sa.String(length=200), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("channels", schema=None) as batch_op:
        batch_op.drop_column("twitch_url")
