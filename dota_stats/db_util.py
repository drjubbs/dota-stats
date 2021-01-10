# -*- coding: utf-8 -*-
"""Utility functions to manage the MySQL database, includes SQLAlchemy
classes and functionality.
"""
import os
import argparse
from sqlalchemy import create_engine, Column, CHAR, VARCHAR, BigInteger, \
    Integer, String
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_URI = os.environ['DOTA_DB_URI']
Base = declarative_base()

# ----------------------------------------------------------------------------
# ORM Classes
# ----------------------------------------------------------------------------
# pylint: disable=too-few-public-methods,no-member


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
    __tablename__ = 'dota_fetch_summary'
    date_hour_skill = Column(CHAR(32), primary_key=True)
    skill = Column(Integer)
    rec_count = Column(Integer)


class HeroWinRate(Base):
    """Win rate/pick rate revised table"""
    __tablename__ = "dota_hero_win_rate"

    time_hero_skill = Column(String(128), primary_key=True)
    time = Column(BigInteger)
    hero = Column(Integer)
    skill = Column(Integer)
    radiant_win = Column(Integer)
    radiant_total = Column(Integer)
    dire_win = Column(Integer)
    dire_total = Column(Integer)

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

    # Drop all of the tables
    engine, _ = connect_database()
    with engine.connect() as conn:
        for table in engine.table_names():
            conn.execute("DROP TABLE {};".format(table))

        # dota_matches
        stmt = "CREATE TABLE dota_matches (match_id BIGINT PRIMARY KEY, " \
               "start_time BIGINT, radiant_heroes CHAR(32), dire_heroes " \
               "CHAR(32), radiant_win BOOLEAN, api_skill INTEGER, " \
               "items VARCHAR(1024), gold_spent VARCHAR(1024)) ENGINE = " \
               "'MyISAM'; "
        conn.execute(stmt)

        # fetch_history
        stmt = "CREATE TABLE fetch_history (match_id BIGINT PRIMARY KEY, " \
               "start_time BIGINT) ENGINE = 'MyISAM'; "
        conn.execute(stmt)

        # fetch_summary
        stmt = "CREATE TABLE fetch_summary (date_hour_skill CHAR(32) PRIMARY " \
               "KEY, skill INT, rec_count INT) ENGINE='MyISAM'; "
        conn.execute(stmt)

        # fetch_win_rate
        stmt = "CREATE TABLE fetch_win_rate (hero_skill CHAR(128) PRIMARY " \
               "KEY, skill TINYINT, hero CHAR(128), time_range CHAR(128), " \
               "radiant_win INT, radiant_total INT, radiant_win_pct FLOAT, " \
               "dire_win INT, dire_total INT, dire_win_pct FLOAT, win INT, " \
               "total INT, win_pct FLOAT) ENGINE='MyISAM'; "
        conn.execute(stmt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database utilities")
    parser.add_argument('--create', action='store_true',
                        help='Create a new database, this will DELETE ALL '
                             'DATABASE DATA.')
    opts = parser.parse_args()

    if opts.create:
        create_database()
    else:
        parser.print_help()
