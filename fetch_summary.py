# -*- coding: utf-8 -*-
"""fetch_summary - Update table containing record counts cache in database,
used to monitor the health of the fetch job.

HORIZON_DAYS controls how far back in history is reprocessed each time
the script runs.
"""
import os
import datetime as dt
import sys
import mariadb
import pandas as pd

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

    # Connect to database and fetch records
    conn = mariadb.connect(
        user=os.environ['DOTA_USERNAME'],
        password=os.environ['DOTA_PASSWORD'],
        host=os.environ['DOTA_HOSTNAME'],
        database=os.environ['DOTA_DATABASE'])
    cursor=conn.cursor()

    stmt="SELECT start_time, match_id, api_skill "
    stmt+="FROM dota_matches WHERE start_time>={0} and start_time<={1};"
    stmt=stmt.format(start_time, end_time)
    print(stmt)

    cursor.execute(stmt)
    rows=cursor.fetchall()
    print("Records: {}".format(len(rows)))

    # Round off timestamps to the nearest hour, create data frame and aggregate on counts
    times=[dt.datetime.fromtimestamp(t[0]).strftime("%Y-%m-%dT%H:00") for t in rows]

    date_hour=[dt.datetime.strptime(t,"%Y-%m-%dT%H:%M").timestamp() for t in times]
    match_ids=[t[1] for t in rows]
    skills=[t[2] for t in rows]

    df_matches=pd.DataFrame({'date_hour' : date_hour, 'skill': skills, 'match_ids' : match_ids})

    summary=df_matches.groupby(["date_hour","skill"]).count()

    # Write to database, overwriting old records
    for idx,row in summary.iterrows():
        stmt="INSERT INTO fetch_summary (date_hour_skill,rec_count) VALUES (?,?) ON DUPLICATE KEY UPDATE rec_count=(?)"
        cursor.execute(stmt,(
                "{0:10d}_{1}".format(int(idx[0]),int(idx[1])),
                int(row['match_ids']),
                int(row['match_ids'])))

    conn.close()

if __name__ == "__main__":
    main()
