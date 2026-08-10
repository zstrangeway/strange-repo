"""replace passwords with provider identities

Revision ID: c3b7a1d94f20
Revises: 10e55f284986
Create Date: 2026-08-10 21:05:00.000000

gary stops holding passwords. Google, Facebook and Apple authenticate people
and gary keeps a row saying which provider account maps to which user.

Deliberately destructive downward: there is no way to restore a password
hash that has been dropped, so downgrade() rebuilds the shape of the old
schema and nothing else. Anyone downgrading gets their accounts back with no
way into them, which is the honest outcome rather than a silent one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3b7a1d94f20'
down_revision: Union[str, Sequence[str], None] = '10e55f284986'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "subject", name="uq_identities_provider_subject"
        ),
    )

    op.drop_table("email_verification_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_column("users", "password_hash")
    op.drop_column("users", "email_verified_at")
    # The address stops being an identifier, so it stops being unique. Two
    # providers can legitimately report the same one for two accounts, which
    # is exactly what not linking on email means.
    op.drop_constraint("users_email_key", "users", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    # No default and not nullable would fail on any existing row, and there is
    # no hash to put back. Empty never verifies, so these accounts land
    # unreachable rather than open.
    op.add_column(
        "users",
        sa.Column(
            "password_hash", sa.String(length=255), nullable=False, server_default=""
        ),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )

    op.drop_table("identities")
