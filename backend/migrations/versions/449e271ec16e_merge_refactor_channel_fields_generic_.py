"""merge refactor_channel_fields_generic into main

Revision ID: 449e271ec16e
Revises: 38c3599d6cfb, refactor_channel_fields_generic
Create Date: 2026-04-15 12:22:23.746084

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '449e271ec16e'
down_revision: Union[str, None] = ('38c3599d6cfb', 'refactor_channel_fields_generic')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
