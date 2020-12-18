# -*- coding: utf-8 -*-
"""fetch_summary - Update table containing record counts cache in database,
used to monitor the health of the fetch job.

HORIZON_DAYS controls how far back in history is reprocessed each time
the script runs.
"""
import os
import datetime as dt
import sys
import pandas as pd
from server.server import db
from db_util import Match, FetchSummary

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
    if len(sys.argv) !=2:
        usage()

    try:
        horizon_days=int(sys.argv[1])
    except ValueError:
        usage()

    # Get UTC timestamps spanning HORIZON_DAYS ago to today
    start_time=int((dt.datetime.utcnow()-dt.timedelta(days=horizon_days)).timestamp())
    end_time=int(dt.datetime.utcnow().timestamp())

    results = db.session.query(Match).\
                    filter(Match.start_time>=start_time).\
                    filter(Match.start_time<=end_time)
    print("Records: {}".format(results.count()))
    rows=results.all()

    # Round off timestamps to the nearest hour, create data frame and aggregate on counts
    times=[dt.datetime.fromtimestamp(t.start_time).strftime("%Y-%m-%dT%H:00") for t in rows]

    date_hour = [dt.datetime.strptime(t,"%Y-%m-%dT%H:%M").timestamp() for t in times]
    match_ids = [t.match_id for t in rows]
    skills = [t.api_skill for t in rows]

    df_matches=pd.DataFrame({'date_hour' : date_hour, 'skill': skills, 'match_ids' : match_ids})
    summary=df_matches.groupby(["date_hour","skill"]).count()

    # Write to database, overwriting old records
    for idx,row in summary.iterrows():

        fetch = FetchSummary()
        fetch.date_hour_skill = "{0:10d}_{1}".format(int(idx[0]),int(idx[1]))
        fetch.rec_count = row['match_ids']

        db.session.merge(fetch)

    db.session.commit()

if __name__ == "__main__":
    main()
