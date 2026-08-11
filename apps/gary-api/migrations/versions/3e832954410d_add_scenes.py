"""'add scenes'

Revision ID: 3e832954410d
Revises: 1ff531109c39
Create Date: 2026-08-11 17:00:50.084755

Hand-finished from autogenerate, which produced a NOT NULL ``turns.scene_id``
added to a table that may already have rows — correct against an empty
database and a failed deploy against any other. Every turn that already exists
belongs to a scene retrospectively, so the column arrives nullable, every
campaign is given the first scene its turns were always in, and only then is
the column tightened.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e832954410d'
down_revision: Union[str, Sequence[str], None] = '1ff531109c39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'scenes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('recap', sa.Text(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'number', name='uq_scenes_campaign_number'),
    )

    op.add_column('turns', sa.Column('scene_id', sa.Uuid(), nullable=True))
    op.add_column('world_events', sa.Column('scene_id', sa.Uuid(), nullable=True))

    # Every campaign that already exists gets the scene it has been playing
    # all along. Untitled, because nobody named it and inventing one here
    # would put a sentence in the game that no part of the game wrote.
    op.execute(
        """
        INSERT INTO scenes (id, campaign_id, number, title, created_at)
        SELECT gen_random_uuid(), campaigns.id, 1, '', now() FROM campaigns
        """
    )
    op.execute(
        """
        UPDATE turns SET scene_id = scenes.id
        FROM scenes
        WHERE scenes.campaign_id = turns.campaign_id AND scenes.number = 1
        """
    )
    # Including the events that belong to no turn — the opening move that
    # places a party where its module starts. That happened in the first
    # scene as surely as anything said in it did.
    op.execute(
        """
        UPDATE world_events SET scene_id = scenes.id
        FROM scenes
        WHERE scenes.campaign_id = world_events.campaign_id
          AND scenes.number = 1
        """
    )

    op.alter_column('turns', 'scene_id', nullable=False)

    op.create_foreign_key(
        'fk_turns_scene_id', 'turns', 'scenes', ['scene_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_world_events_scene_id', 'world_events', 'scenes', ['scene_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_world_events_scene_id', 'world_events', type_='foreignkey')
    op.drop_column('world_events', 'scene_id')
    op.drop_constraint('fk_turns_scene_id', 'turns', type_='foreignkey')
    op.drop_column('turns', 'scene_id')
    op.drop_table('scenes')
