# -*- coding: utf-8 -*-
"""Utility functions to manage the MySQL database"""
from server.server import db, WinByPosition, Match

# pylint: disable=no-member
#----------------------------------------------------------------------------
# BEGIN SQLAlchemy Classes
#----------------------------------------------------------------------------
class Configuration(db.Model):
    """Contains database configuration data include version number"""
    __tablename__ = 'configuration'
    config_id = db.Column(db.CHAR(64), primary_key=True)
    value = db.Column(db.VARCHAR(256))

    def __repr__(self):
        return '<%s>' % self.config_id


#----------------------------------------------------------------------------
# END SQLAlchemy Classes
#----------------------------------------------------------------------------

#---------------------------------------------------------------------------
# Database version upgrades
#---------------------------------------------------------------------------

def get_version():
    """Return current database version"""
    if not db.engine.dialect.has_table(db.engine, "configuration"):
        return "001"
    else:
        version = Configuration.query.filter_by(config_id='VERSION').first().value
        return version


def create_version_001():
    """Create the initial database version"""

    if db.engine.dialect.has_table(db.engine, "dota_matches"):
        Match.__table__.drop(db.engine)
    Match.__table__.create(db.engine)


def update_version_002():
    """Add bitmask fields and table for winrate by position"""

    if get_version() != "001":
        return

    Configuration.__table__.create(db.engine)
    config = Configuration()
    config.config_id = "VERSION"
    config.value = "002"

    db.session.add(config)
    db.session.commit()

    # Create win position table
    if db.engine.dialect.has_table(db.engine, "win_by_position"):
        WinByPosition.__table__.drop(db.engine)
    WinByPosition.__table__.create(db.engine)

    return

def main():
    """Main entry point"""
    update_version_002()

# pylint: enable=no-member

if __name__ == "__main__":
    main()
