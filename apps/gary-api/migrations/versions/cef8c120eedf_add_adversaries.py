"""add adversaries

A new table and one nullable column, so there is nothing to backfill and
nothing that can fail against rows already there.


Revision ID: cef8c120eedf
Revises: 4bdfc9004697
Create Date: 2026-08-11 23:32:33.101758

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cef8c120eedf'
down_revision: Union[str, Sequence[str], None] = '4bdfc9004697'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Named rather than left to autogenerate's None, which produces a constraint
# Postgres names for us and a downgrade that cannot find it again.
FK = "fk_rolls_adversary_id_adversaries"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('adversaries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('campaign_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('max_hp', sa.Integer(), nullable=False),
    sa.Column('armour_class', sa.Integer(), nullable=False),
    sa.Column('attack_bonus', sa.Integer(), nullable=False),
    sa.Column('damage', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('rolls', sa.Column('adversary_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        FK, 'rolls', 'adversaries', ['adversary_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(FK, 'rolls', type_='foreignkey')
    op.drop_column('rolls', 'adversary_id')
    op.drop_table('adversaries')
