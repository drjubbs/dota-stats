"""revise fetch_win_rate

Revision ID: 921d6d16a9ee
Revises: 
Create Date: 2020-12-27 15:22:29.954213

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '921d6d16a9ee'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create table hour by hour table for win rates to allow arbitrary time
    aggregations.
    """
    op.drop_table("fetch_win_rate")
    op.create_table("dota_hero_win_rate",
                    sa.Column('time_hero_skill', sa.String(128),
                              primary_key=True),
                    sa.Column('time', sa.BigInteger),
                    sa.Column('hero', sa.Integer),
                    sa.Column('skill', sa.Integer),
                    sa.Column('radiant_win', sa.Integer),
                    sa.Column('radiant_total', sa.Integer),
                    sa.Column('dire_win', sa.Integer),
                    sa.Column('dire_total', sa.Integer))
    op.create_index('ix_time_hero_skill', 'dota_hero_win_rate',
                    ['time', 'hero', 'skill'])


def downgrade():
    """Recreate the old win table structure"""
    op.drop_table("dota_hero_win_rate")
    op.create_table("fetch_win_rate",
                    sa.Column('hero_skill', sa.String(128), primary_key=True),
                    sa.Column('skill', sa.Integer),
                    sa.Column('hero', sa.String(128)),
                    sa.Column('time_range', sa.String(128)),
                    sa.Column('radiant_win', sa.Integer),
                    sa.Column('radiant_total', sa.Integer),
                    sa.Column('radiant_win_pct', sa.Float),
                    sa.Column('dire_win', sa.Integer),
                    sa.Column('dire_total', sa.Integer),
                    sa.Column('dire_win_pct', sa.Float),
                    sa.Column('win', sa.Integer),
                    sa.Column('total', sa.Integer),
                    sa.Column('win_pct', sa.Float))
