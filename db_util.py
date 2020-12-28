# -*- coding: utf-8 -*-
"""Utility functions to manage the MySQL database, includes SQLAlchemy
classes and functionality.
"""
import os
from sqlalchemy import create_engine, Column, CHAR, VARCHAR, BigInteger, \
    Integer, Float
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URI = os.environ['DOTA_DB_URI']
Base = declarative_base()

# ----------------------------------------------------------------------------
# ORM Classes
# ----------------------------------------------------------------------------
# pylint: disable=too-few-public-methods,no-member


class Configuration(Base):
    """Contains database configuration data include version number"""
    __tablename__ = 'configuration'
    config_id = Column(CHAR(64), primary_key=True)
    value = Column(VARCHAR(256))

    def __repr__(self):
        return '<%s>' % self.config_id


class Match(Base):
    """Base class for match results"""
    __tablename__ = 'dota_matches'

    match_id = Column(BigInteger, primary_key=True)
    start_time = Column(BigInteger)
    radiant_heroes = Column(CHAR(32))
    dire_heroes = Column(CHAR(32))
    radiant_win = Column(TINYINT)
    api_skill = Column(Integer)
    items = Column(VARCHAR(1024))
    gold_spent = Column(VARCHAR(1024))

    def __repr__(self):
        return '<Match %r Radiant %r Dire %r>' % (
            self.match_id, self.radiant_heroes, self.dire_heroes)


class FetchSummary(Base):
    """Base class for fetch summary stats"""
    __tablename__ = 'fetch_summary'
    date_hour_skill = Column(CHAR(32), primary_key=True)
    skill = Column(Integer)
    rec_count = Column(Integer)


class WinRatePickRate(Base):
    """Base class for fetch_win_rate object."""

    __tablename__ = "fetch_win_rate"
    hero_skill = Column(CHAR(128), primary_key=True)
    skill = Column(TINYINT)
    hero = Column(CHAR(128))
    time_range = Column(CHAR(128))
    radiant_win = Column(Integer)
    radiant_total = Column(Integer)
    radiant_win_pct = Column(Float)
    dire_win = Column(Integer)
    dire_total = Column(Integer)
    dire_win_pct = Column(Float)
    win = Column(Integer)
    total = Column(Integer)
    win_pct = Column(Float)


class WinByPosition(Base):
    """Win rates by position for all heroes"""
    __tablename__ = 'win_by_position'

    timestamp_hero_skill = Column(VARCHAR(128), primary_key=True,
                                  nullable=False)
    hero = Column(VARCHAR(64), nullable=False)
    pos1 = Column(Float, nullable=True)
    pos2 = Column(Float, nullable=True)
    pos3 = Column(Float, nullable=True)
    pos4 = Column(Float, nullable=True)
    pos5 = Column(Float, nullable=True)

# pylint: enable=too-few-public-methods, no-member
# -----------------------------------------------------------------------------
# Database Functions
# -----------------------------------------------------------------------------


def connect_database():
    """Connect to database and return session"""
    engine = create_engine(DB_URI, echo=False)
    s_maker = sessionmaker()
    s_maker.configure(bind=engine)
    session = s_maker()

    return engine, session


def get_max_start_time():

    """Return the most recent start time"""
    engine, _ = connect_database()
    with engine.connect() as conn:
        rows = conn.execute("select max(start_time) from dota_matches")
    return int(rows.first()[0])


def create_database():
    """Create the clean database tables"""

    engine, _ = connect_database()
    with engine.connect() as conn:
        for table in engine.table_names():
            conn.execute("DROP TABLE {};".format(table))

# pylint: disable=too-few-public-methods, no-member
    Configuration.__table__.create(engine)
    Match.__table__.create(engine)
    FetchSummary.__table__.create(engine)
    WinRatePickRate.__table__.create(engine)
    WinByPosition.__table__.create(engine)
# pylint: enable=too-few-public-methods, no-member


if __name__ == "__main__":
    pass
