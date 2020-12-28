"""Add indices

Revision ID: c71c3f058b8c
Revises: 921d6d16a9ee
Create Date: 2020-12-28 09:16:05.512354

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c71c3f058b8c'
down_revision = '921d6d16a9ee'
branch_labels = None
depends_on = None


def upgrade():
    """Create index for start_time"""
    op.create_index('ix_start_time', 'dota_matches', ['start_time'])
    op.drop_table("configuration")


def downgrade():
    """Drop index for start_time"""
    op.drop_index('ix_start_time', 'dota_matches')
    op.create_table("configuration",
                    sa.Column("config_id", sa.String(64)),
                    sa.Column("value", sa.String(256)))
