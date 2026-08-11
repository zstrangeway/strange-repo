"""say whose roll it was

Both columns are nullable and stay that way, so there is nothing to backfill:
a roll made before this existed was made for somebody, but nothing wrote down
who, and inventing an answer would be worse than admitting the gap.

Revision ID: 4bdfc9004697
Revises: 9ce5b25ff4b3
Create Date: 2026-08-11 21:39:01.114288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bdfc9004697'
down_revision: Union[str, Sequence[str], None] = '9ce5b25ff4b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Named rather than left to autogenerate's None, which produces a constraint
# Postgres names for us and a downgrade that cannot find it again.
FK = "fk_rolls_character_id_characters"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('rolls', sa.Column('character_id', sa.Uuid(), nullable=True))
    op.add_column('rolls', sa.Column('ability', sa.String(length=20), nullable=True))
    op.create_foreign_key(
        FK, 'rolls', 'characters', ['character_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(FK, 'rolls', type_='foreignkey')
    op.drop_column('rolls', 'ability')
    op.drop_column('rolls', 'character_id')
