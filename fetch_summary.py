# -*- coding: utf-8 -*-
"""fetch_summary - Update table containing record counts cache in database,
used to monitor the health of the fetch job.

HORIZON_DAYS controls how far back in history is reprocessed each time
the script runs.
"""
import datetime as dt
import sys
import pandas as pd
from server.server import db
from db_util import FetchSummary, connect_database


def usage():
    """Display command line help"""
    print()
    print("fetch_summary <horizon>")
    print()
    print("Horizon represents days to summarize database over.")
    print()
    sys.exit(-1)


def main():
    """Main program execution"""
    if len(sys.argv) != 2:
        usage()

    horizon_days = 1
    try:
        horizon_days = int(sys.argv[1])
    except ValueError:
        usage()

    # Get UTC timestamps spanning HORIZON_DAYS ago to today
    start_time = int((dt.datetime.utcnow()-dt.timedelta(
        days=horizon_days)).timestamp())
    end_time = int(dt.datetime.utcnow().timestamp())

    engine, session = connect_database()
    with engine.connect() as conn:
        stmt = "select start_time, match_id, api_skill from dota_matches " \
               "where start_time>={} and start_time<={};".format(start_time,
                                                                 end_time)
        rows = conn.execute(stmt)

    print("Records: {}".format(rows.rowcount))

    times = []
    match_ids = []
    skills = []
    for row in rows:
        # Round off timestamps to the nearest hour, create data frame and
        # aggregate on counts.
        round_time = dt.datetime.fromtimestamp(row.start_time).strftime(
            "%Y-%m-%dT%H:00")
        times.append(int(dt.datetime.strptime(round_time,
                                              "%Y-%m-%dT%H:%M").timestamp()))
        match_ids.append(row.match_id)
        skills.append(row.api_skill)

    df_matches = pd.DataFrame({'date_hour': times, 'skill': skills,
                              'match_ids': match_ids})
    summary = df_matches.groupby(["date_hour", "skill"]).count()
    summary.reset_index(inplace=True)

    # Write to database, overwriting old records
    for _, row in summary.iterrows():

        fetch = FetchSummary()
        fetch.date_hour_skill = "{0:10d}_{1}".format(row['date_hour'],
                                                     row['skill'])
        fetch.rec_count = row['match_ids']

        db.session.merge(fetch)

    db.session.commit()


if __name__ == "__main__":
    main()
