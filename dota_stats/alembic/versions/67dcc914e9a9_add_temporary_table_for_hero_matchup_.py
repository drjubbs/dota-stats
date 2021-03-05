"""Add temporary table for hero matchup table purge trial

Revision ID: 67dcc914e9a9
Revises: 2d739361db17
Create Date: 2021-03-05 10:25:32.581886

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67dcc914e9a9'
down_revision = '2d739361db17'
branch_labels = None
depends_on = None


def upgrade():
    """Create new table and index"""
    op.create_table("dota_hero_matchup_tmp",
                    sa.Column('match_hero_hero', sa.String(30),
                              primary_key=True),
                    sa.Column('start_time', sa.BigInteger),
                    sa.Column('api_skill', sa.Integer),
                    sa.Column('hero1', sa.Integer),
                    sa.Column('hero2', sa.Integer),
                    sa.Column('win', sa.Integer))

    
def downgrade():
    op.drop_table('dota_hero_matchup_tmp')
