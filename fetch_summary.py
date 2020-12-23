# -*- coding: utf-8 -*-
"""fetch_summary - Update table containing record counts cache in database,
used to monitor the health of the fetch job.

HORIZON_DAYS controls how far back in history is reprocessed each time
the script runs.
"""
import argparse
import datetime as dt
import pandas as pd
from db_util import FetchSummary, connect_database


def fetch_rows(horizon_days, engine):
    """Get the match_ids, skill level, and start times from the database
    within `horizon_days` of current time.
    """

    # Get UTC timestamps spanning horizon_days ago to today
    start_time = int((dt.datetime.utcnow()-dt.timedelta(
        days=horizon_days)).timestamp())
    end_time = int(dt.datetime.utcnow().timestamp())

    with engine.connect() as conn:
        stmt = "select start_time, match_id, api_skill from dota_matches " \
               "where start_time>={} and start_time<={};".format(start_time,
                                                                 end_time)
        rows = conn.execute(stmt)

    return rows


def main():
    """Main program execution"""

    parser = argparse.ArgumentParser(description='Update table containing '
                                                 'record count by hour.')
    parser.add_argument("horizon_days", type=int)
    opts = parser.parse_args()

    engine, session = connect_database()
    rows = fetch_rows(opts.horizon_days, engine)
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
        session.merge(fetch)
    session.commit()


if __name__ == "__main__":
    main()
