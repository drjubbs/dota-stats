# -*- coding: utf-8 -*-
"""Simple utility to create a snapshot of the database."""
import os
import sys
import argparse
from datetime import datetime


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Create snapshot of the database")
    parser.add_argument('days', type=float,
                        help='Number of days of history to include, '
                             'fractional values accepted')

    opts = parser.parse_args(sys.argv[1:])

    # Main table: dota_matches
    time_str = datetime.utcnow().strftime("%Y%m%d_%H%S")
    end = int((datetime.utcnow()-datetime(1970, 1, 1)).total_seconds())
    begin = int(end - 3600 * 24 * opts.days)

    # Create DB directory if it doesn't exist
    if not os.path.exists("snapshots"):
        os.mkdir("snapshots")

    filename = os.path.join("snapshots", "db_matches_{}.sql".format(time_str))
    cmd = 'mysqldump --databases {0} --tables dota_matches --where="start_time '
    cmd += 'between {1} and {2}" --user={3} --password={4} > {5}'
    cmd = cmd.format(
        os.environ['DOTA_DATABASE'],
        begin,
        end,
        os.environ['DOTA_USERNAME'],
        os.environ['DOTA_PASSWORD'],
        filename)
    print(cmd)
    os.system(cmd)

    filename = os.path.join("snapshots", "db_others_{}.sql".format(time_str))
    cmd = 'mysqldump --databases {0} --tables fetch_summary '
    cmd += 'fetch_history fetch_win_rate --user={1} --password={2} > {3}'
    cmd = cmd.format(
            os.environ['DOTA_DATABASE'],
            os.environ['DOTA_USERNAME'],
            os.environ['DOTA_PASSWORD'],
            filename)
    print(cmd)
    os.system(cmd)


if __name__ == "__main__":
    main()
