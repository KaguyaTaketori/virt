"""merge_bilibili_dynamics_and_blacklisted_tokens

Revision ID: 38c3599d6cfb
Revises: add_bilibili_dynamics, add_blacklisted_tokens
Create Date: 2026-04-08 18:36:15.037109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38c3599d6cfb'
down_revision: Union[str, None] = ('add_bilibili_dynamics', 'add_blacklisted_tokens')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
