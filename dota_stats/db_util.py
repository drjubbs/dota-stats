# -*- coding: utf-8 -*-
"""Utility functions to manage the MySQL database, includes SQLAlchemy
classes and functionality.
"""
import os
import argparse
import logging
import sys
from datetime import datetime as dt
from sqlalchemy import create_engine, Column, CHAR, VARCHAR, BigInteger, \
    Integer, String
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient


# Logging
log = logging.getLogger("db_util")
if int(os.environ['DOTA_LOGGING']) == 0:
    log.setLevel(logging.INFO)
else:
    log.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
fmt = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%S %Z")
ch.setFormatter(fmt)
log.addHandler(ch)


def connect_mongo():
    """Connect to MongoDB"""
    mongo = MongoClient(os.environ['DOTA_MONGO_URI'])
    return mongo[os.environ['DOTA_MONGO_DB']]


def get_key(skill, time, match):
    """Generate MongdoDB _id for skill/time/match trio"""
    return "{0:1d}_{1:010d}_{2:012d}".format(skill, time, match)


def get_max_start_time():
    """Return the most recent start time"""

    mongo_db = connect_mongo()
    last = mongo_db.matches.find().sort("start_time", -1)[0]

    return last['start_time']


def purge_database(days):
    """Purge all records older than `days` relative to current time."""

    now = dt.utcnow().timestamp()
    cutoff = int(now - (days*24*60*60))

    mongo_db = connect_mongo()
    query = {'start_time': {'$lte': cutoff}}
    match_count = mongo_db.matches.count_documents(query)
    log.info("Purging %d from %s" % (match_count, "matches"))
    mongo_db.matches.delete_many(query)

    query = {'time': {'$lte': cutoff}}
    hero_win_rate_count = mongo_db.hero_win_rate.count_documents(query)
    log.info("Purging %d from %s" % (hero_win_rate_count,
                                     "hero_win_rate_count"))
    mongo_db.hero_win_rate.delete_many(query)

    return match_count, hero_win_rate_count


def create_database():
    """Create the clean database tables"""

    mongo_db = connect_mongo()
    for collection in mongo_db.list_collection_names():
        log.info("MongoDB Dropping '{0}'".format(collection))
        mongo_db[collection].drop()

    # Create indcies
    mongo_db.matches.create_index([('start_time', -1)])
    mongo_db.hero_win_rate.create_index([('time', -1)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database utilities")
    parser.add_argument('--create', action='store_true',
                        help='Create a new database, this will DELETE ALL '
                             'DATABASE DATA.')
    parser.add_argument('--purge', action='store', type=int,
                        help='Purge the database of records older than PURGE '
                             'from the current time.')

    opts = parser.parse_args()

    if opts.create:
        create_database()
    elif opts.purge is not None:
        purge_database(opts.purge)
    else:
        parser.print_help()
