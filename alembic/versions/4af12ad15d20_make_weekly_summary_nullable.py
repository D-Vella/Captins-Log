"""make weekly_summary nullable

Revision ID: 4af12ad15d20
Revises: 51e07a79f1f0
Create Date: 2026-07-06 19:10:52.880812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4af12ad15d20'
down_revision: Union[str, Sequence[str], None] = '51e07a79f1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('log_enrichment') as batch_op:
        batch_op.alter_column('weekly_summary',
                   existing_type=sa.TEXT(),
                   nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('log_enrichment') as batch_op:
        batch_op.alter_column('weekly_summary',
                   existing_type=sa.TEXT(),
                   nullable=False)
