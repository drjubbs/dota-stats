"""dota_hero_matchup

Revision ID: 2d739361db17
Revises: c71c3f058b8c
Create Date: 2021-01-11 15:00:51.679244

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d739361db17'
down_revision = 'c71c3f058b8c'
branch_labels = None
depends_on = None


def upgrade():
    """Create new table and index"""
    op.create_table("dota_hero_matchup",
                    sa.Column('match_hero_hero', sa.String(30),
                              primary_key=True),
                    sa.Column('start_time', sa.BigInteger),
                    sa.Column('api_skill', sa.Integer),
                    sa.Column('hero1', sa.Integer),
                    sa.Column('hero2', sa.Integer),
                    sa.Column('win', sa.Integer))

    op.create_index('ix_start_time', 'dota_hero_matchup', ['start_time'])
    op.create_index('ix_api_skill', 'dota_hero_matchup', ['api_skill'])
    op.create_index('ix_hero1', 'dota_hero_matchup', ['hero1'])
    op.create_index('ix_hero2', 'dota_hero_matchup', ['hero2'])
    op.create_index('ix_hero12', 'dota_hero_matchup', ['hero1', 'hero2'])


def downgrade():
    """Remove new table and index"""
    op.drop_index('ix_start_time', 'dota_hero_matchup')
    op.drop_index('ix_api_skill', 'dota_hero_matchup')
    op.drop_index('ix_hero1', 'dota_hero_matchup')
    op.drop_index('ix_hero2', 'dota_hero_matchup')
    op.drop_index('ix_hero12', 'dota_hero_matchup')
    op.drop_table('dota_hero_matchup')
