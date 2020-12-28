# -*- coding: utf-8 -*-
"""Simple utility to create a snapshot of the database."""
import os
import re
import sys
import argparse
from datetime import datetime
import db_util


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Create snapshot of the database")
    parser.add_argument('days', type=float,
                        help='Number of days of history to include, '
                             'fractional values accepted')

    opts = parser.parse_args(sys.argv[1:])

    # Parse out connection parameters from URI string
    rmatch = re.match(".*//(.*):(.*)@(.*)/(.*)", os.environ['DOTA_DB_URI'])
    username = rmatch.group(1)
    password = rmatch.group(2)
    database = rmatch.group(4)

    # Get begin and end time
    end = db_util.get_max_start_time()
    begin = int(end - 3600 * 24 * opts.days)
    time_str = datetime.utcfromtimestamp(end).strftime("%Y%m%d_%H%M")

    # Create DB directory if it doesn't exist
    if not os.path.exists("snapshots"):
        os.mkdir("snapshots")

    filename = os.path.join("snapshots", "dota_matches_{}.sql".format(time_str))
    cmd = 'mysqldump --databases {0} --tables dota_matches --where="start_time '
    cmd += 'between {1} and {2}" --user={3} --password={4} > {5}'
    cmd = cmd.format(database, begin, end, username, password, filename)
    print(cmd)
    os.system(cmd)

    filename = os.path.join("snapshots", "db_others_{}.sql".format(time_str))
    cmd = 'mysqldump --databases {0} --ignore-table={0}.dota_matches ' \
          '--user={1} --password={2} > {3}'
    cmd = cmd.format(database, username, password, filename)
    print(cmd)
    os.system(cmd)


if __name__ == "__main__":
    main()
