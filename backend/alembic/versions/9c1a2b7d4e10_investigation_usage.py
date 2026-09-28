"""token usage per investigation

Revision ID: 9c1a2b7d4e10
Revises: 721fc27cd604
Create Date: 2026-09-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c1a2b7d4e10'
down_revision: Union[str, Sequence[str], None] = '721fc27cd604'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('investigations',
                  sa.Column('usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('investigations', 'usage')
