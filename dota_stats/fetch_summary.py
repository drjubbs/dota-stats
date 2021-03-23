# -*- coding: utf-8 -*-
"""fetch_summary - Update table containing record counts cache in database,
used to monitor the health of the fetch job.

HORIZON_DAYS controls how far back in history is reprocessed each time
the script runs.
"""
import argparse
import datetime as dt
import pandas as pd
import pytz
from dota_stats.db_util import connect_mongo, get_max_start_time
from dota_stats import dotautil



def isoformat_with_tz(time_obj, utc_hour):
    """Format to 8601 with timezone offset"""

    txt = time_obj.strftime("%Y-%m-%dT%H:%M:%S")
    txt = "{0}{1:+03d}:00".format(txt, utc_hour)
    return txt


def get_health_summary(days, timezone, hour=True, use_current_time=True):
    """Returns a Pandas dataframe summarizing number of matches processed
    over an interval of days. Defaults to by hour, can we chaned to daily
    view through use of optional `hour` argument`.
    """

    # Database connection
    mongo_db = connect_mongo()

    # Get TZ offsets, do everything relative to current TZ offset
    local_tz = pytz.timezone(timezone)
    utc_offset = local_tz.utcoffset(dt.datetime.now())
    utc_hour = int(utc_offset.total_seconds() / 3600)

    if use_current_time:
        now = dt.datetime.utcnow()
    else:
        now = dt.datetime.fromtimestamp(get_max_start_time())

    now = now + utc_offset

    # Create a blank dataframe for the time range of interest, starting with
    # times.
    if hour:
        now_rnd = dt.datetime(now.year, now.month, now.day, now.hour, 0, 0)
        times = [isoformat_with_tz(now_rnd - dt.timedelta(hours=i), utc_hour)
                 for i in range(24 * days)]

    else:
        now_rnd = dt.datetime(now.year, now.month, now.day, 0, 0, 0)
        times = [isoformat_with_tz(now_rnd - dt.timedelta(days=i), utc_hour)
                 for i in range(days)]

    # Blank dataframe, one entry for each skill level...
    df_blank = pd.DataFrame(index=times, data={
        1: [0] * len(times),
        2: [0] * len(times),
        3: [0] * len(times),
    })

    # Fetch from database, convert to DataFrame
    begin = int((now_rnd - dt.timedelta(days=days)).timestamp())
    query = {"start_time": {"$gte": begin}}
    projection = {"start_time": 1, "api_skill": 1}

    matches = mongo_db.matches.find(query, projection)
    rows = pd.DataFrame(matches)

    # Trim columns and renamed
    rows = rows[['start_time', 'api_skill']]
    rows = rows.rename(columns={
        'start_time': 'time',
        'api_skill': 'skill'
    })

    if len(rows) == 0:
        df_summary = df_blank
    else:
        # Apply UTC offset
        rows['time_local'] = rows['time'] + utc_hour*3600
        rows['time_local_rnd'] = [
            dotautil.TimeMethods.get_time_nearest(t, hour=hour)[0]
            for t in rows['time_local']]
        rows['rec_count'] = 1

        df_summary = rows[["time_local_rnd", "skill", "rec_count"]]
        df_summary = df_summary.groupby(["time_local_rnd", "skill"]).sum()
        df_summary.reset_index(inplace=True)
        df_summary = df_summary.pivot(index='time_local_rnd', columns='skill',
                                      values='rec_count')

        dt2 = [dt.datetime.utcfromtimestamp(float(t)) for t in df_summary.index]
        dt3 = [isoformat_with_tz(t, utc_hour) for t in dt2]
        df_summary.index = dt3

        # Add them together
        df_summary = df_blank.add(df_summary, fill_value=0)

    # Rename columns
    df_summary = df_summary[[1, 2, 3]]
    df_summary.columns = ['normal', 'high', 'very_high']
    df_summary = df_summary.sort_index(ascending=False)

    # For summary table
    rows = zip(df_summary.index,
               df_summary['normal'].values,
               df_summary['high'].values,
               df_summary['very_high'].values)

    return df_summary, rows


def fetch_rows(mongo_db, horizon_days, use_current_time):
    """Get the match_ids, skill level, and start times from the database
    within `horizon_days` of current time.

    If use_current_time is True (default), get time slices relative to current
    time, otherwise, use the max time found in the database
    """

    # Get UTC timestamps spanning horizon_days ago to today
    if use_current_time:
        now = dt.datetime.utcnow()
    else:
        now = dt.datetime.fromtimestamp(get_max_start_time())

    start_time = int((now-dt.timedelta(
        days=horizon_days)).timestamp())
    end_time = int(now.timestamp())

    query = {"start_time": {"$gte": start_time, "$lte": end_time}}
    count = mongo_db.matches.count_documents(query)
    rows = mongo_db.matches.find(query)

    return rows, count


def main(days, use_current_time=True):
    """Main program execution"""

    mongo_db = connect_mongo()
    rows, count = fetch_rows(mongo_db, days, use_current_time)

    print("Records: {}".format(count))

    times = []
    match_ids = []
    skills = []
    for row in rows:
        # Round off timestamps to the nearest hour, create data frame and
        # aggregate on counts.
        round_time = dt.datetime.fromtimestamp(row['start_time']).strftime(
            "%Y-%m-%dT%H:00")
        times.append(int(dt.datetime.strptime(round_time,
                                              "%Y-%m-%dT%H:%M").timestamp()))
        match_ids.append(row['match_id'])
        skills.append(row['api_skill'])

    df_matches = pd.DataFrame({'date_hour': times, 'skill': skills,
                              'match_ids': match_ids})
    summary = df_matches.groupby(["date_hour", "skill"]).count()
    summary.reset_index(inplace=True)

    # Write to database, overwriting old records
    for _, row in summary.iterrows():

        doc = {
            "_id": int(row['date_hour']),
            "skill": int(row['skill']),
            "match_ids": int(row['match_ids']),
        }
        mongo_db.fetch_summary.replace_one(
            {"_id": doc['_id']}, doc, upsert=True)


if __name__ == "__main__":
    """Main program execution"""

    parser = argparse.ArgumentParser(description='Update table containing '
                                                 'record count by hour.')
    parser.add_argument("horizon_days", type=int)
    opts = parser.parse_args()

    main(opts.horizon_days)
