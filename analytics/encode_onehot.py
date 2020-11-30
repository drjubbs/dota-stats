# -*- coding: utf-8 -*-
"""Extract matches over a date range and one-hot encodes in a format suitable
for machine learning."""
import sys
import datetime as dt
import argparse
import os
import json
import pandas as pd
import mariadb
import numpy as np

sys.path.append("..")
from dotautil import MLEncoding # pylint: disable=import-error, wrong-import-position

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Extract matches over a date "\
        "range and one-hot encodes in a format suitable for machine learning.")
    parser.add_argument("begin", help="Time to begin YYYYMMDD")
    parser.add_argument("end", help="Time to end YYYYMMDD")
    parser.add_argument("skill", help="Skill level {1, 2, 3}", type=int)

    opts = parser.parse_args()

    try:
        begin = dt.datetime.strptime(opts.begin, "%Y%m%d")
        end = dt.datetime.strptime(opts.end, "%Y%m%d")

        # Fetch all rows
        begin = (begin - dt.datetime(1970,1,1)).total_seconds()
        end = (end - dt.datetime(1970,1,1)).total_seconds()

    except ValueError:
        parser.error("Cannot read begin or end dates")

    if opts.skill not in [1, 2, 3]:
        parser.error("Bad skill level %d" % opts.skill)

    # Database fetch
    conn = mariadb.connect(
        user=os.environ['DOTA_USERNAME'],
        password=os.environ['DOTA_PASSWORD'],
        host=os.environ['DOTA_HOSTNAME'],
        database=os.environ['DOTA_DATABASE'])
    cursor=conn.cursor()

    stmt="SELECT start_time, match_id, radiant_heroes, dire_heroes, "
    stmt+="radiant_win FROM dota_matches WHERE start_time>={0} and "
    stmt+="start_time<{1} and api_skill={2}"
    stmt=stmt.format(
        int(begin),
        int(end),
        opts.skill)
    print(stmt)

    cursor.execute(stmt)
    rows=cursor.fetchall()
    print("Records: {}".format(len(rows)))

    # Display records by day
    times = [dt.datetime.utcfromtimestamp(t[0]) for t in rows]
    days = [dt.datetime(t.year, t.month, t.day) for t in times]
    df_days =  pd.DataFrame(columns=["days"], data=days)
    df_days['count'] = 1
    print(df_days.groupby("days").count())

    # Setup the targets
    radiant_win=np.array([t[-1] for t in rows])

    # First order effects
    rad_heroes = [json.loads(t[2]) for t in rows]
    dire_heroes = [json.loads(t[3]) for t in rows]

    y_data, x1_data, x2_data, x3_data = MLEncoding.create_features(\
        rad_heroes, dire_heroes, radiant_win)

    # Write to file
    if not os.path.exists("output"):
        os.mkdir("output")
    begin=dt.datetime.utcfromtimestamp(begin)
    token = begin.strftime("%Y%m%d")

    np.save(os.path.join("output", "ydata_"+str(opts.skill)+"_"+token), y_data)
    np.save(os.path.join("output", "x1_data_"+str(opts.skill)+"_"+token), x1_data)
    np.save(os.path.join("output", "x2_data_"+str(opts.skill)+"_"+token), x2_data)
    np.save(os.path.join("output", "x3_data_"+str(opts.skill)+"_"+token), x3_data)


if __name__ == "__main__":
    main()
