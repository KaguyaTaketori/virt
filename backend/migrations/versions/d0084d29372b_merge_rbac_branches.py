"""merge rbac branches

Revision ID: d0084d29372b
Revises: add_bilibili_fields_001, add_group_and_status_fields
Create Date: 2026-04-04 14:29:55.642115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0084d29372b'
down_revision: Union[str, None] = ('add_bilibili_fields_001', 'add_group_and_status_fields')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
