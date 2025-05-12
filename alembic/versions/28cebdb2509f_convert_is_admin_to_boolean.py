"""convert_is_admin_to_boolean

Revision ID: 28cebdb2509f
Revises: 5fcc2cafc8a3
Create Date: 2025-05-12 20:57:24.151734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28cebdb2509f'
down_revision: Union[str, None] = '5fcc2cafc8a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
