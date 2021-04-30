# -*- coding: utf-8 -*-
"""Code to create new database and compacting existings ones"""
import argparse
from datetime import datetime as dt
from dota_stats.log_conf import get_logger
from dota_stats import db_util
log = get_logger("db_tools")


def purge_database(days, use_current_time=True):
    """Purge all records older than `days` relative to current time. If
    `utc` is get to false it will use most recent entry in database.
    """

    if use_current_time is True:
        now = dt.utcnow().timestamp()
    else:
        now = db_util.get_max_start_time()

    cutoff = int(now - (days*24*60*60))

    mongo_db = db_util.connect_mongo()
    query = {'start_time': {'$lte': cutoff}}
    match_count = mongo_db.matches.count_documents(query)
    log.info("Purging %d from %s", match_count, "matches")
    mongo_db.matches.delete_many(query)

    query = {'time': {'$lte': cutoff}}
    hero_win_rate_count = mongo_db.hero_win_rate.count_documents(query)
    log.info("Purging %d from %s", hero_win_rate_count, "hero_win_rate_count")
    mongo_db.hero_win_rate.delete_many(query)

    return match_count, hero_win_rate_count


def create_database():
    """Create the clean database tables"""

    mongo_db = db_util.connect_mongo()
    for collection in mongo_db.list_collection_names():
        log.info("MongoDB Dropping %s", collection)
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
