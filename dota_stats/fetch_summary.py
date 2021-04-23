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
from dota_stats import dotautil, db_util
from dota_stats.log_conf import get_logger

log = get_logger("fetch_summary")


def isoformat_with_tz(time_obj, utc_hour):
    """Format to 8601 with timezone offset"""

    txt = time_obj.strftime('%Y-%m-%dT%H:%M:%S')
    txt = "{0}{1:+03d}:00".format(txt, utc_hour)
    return txt


def get_blank_time_summary(days, hour, start, utc_hour):
    """Create a blank dataframe for the time range of interest.

    days: how many days to create a blank data frame for
    hours: boolean, if true hourly data, if false do daily data
    start: beginning time of data frame
    utc_hour: hourly offset to localize time (e.g. -4 for Eastern Std Time
    """

    if hour:
        now_rnd = dt.datetime(start.year, start.month, start.day,
                              start.hour, 0, 0)
        times = [isoformat_with_tz(now_rnd - dt.timedelta(hours=i), utc_hour)
                 for i in range(24 * days)]

    else:
        now_rnd = dt.datetime(start.year, start.month, start.day,
                              0, 0, 0)
        times = [isoformat_with_tz(now_rnd - dt.timedelta(days=i), utc_hour)
                 for i in range(days)]

    # Blank dataframe, one entry for each skill level...
    df_blank = pd.DataFrame(index=times, data={
        1: [0] * len(times),
        2: [0] * len(times),
        3: [0] * len(times),
    })

    begin = int((now_rnd - dt.timedelta(days=days)).timestamp())

    return df_blank, begin


def get_health_summary(mongo_db, days, timezone, hour=True,
                       use_current_time=True):
    """Returns a Pandas dataframe summarizing number of matches processed
    over an interval of hours or days. Defaults to by hour, can we chaned to
    daily view through use of optional `hour` argument`.

    mongo_db: Instance of Mongo client
    days: Number of days to summarize over
    timezone: Which timezone to localize data into
    hour: If true hourly summary, otherwise daily
    use_current_time: If true, use current time to create beginning of
                      otherwise use the most recent date in the database.
    """

    # Get TZ offsets, do everything relative to current TZ offset
    utc_offset = pytz.timezone(timezone).utcoffset(dt.datetime.now())
    utc_hour = int(utc_offset.total_seconds() / 3600)

    if use_current_time:
        now = dt.datetime.utcnow()
    else:
        now = dt.datetime.fromtimestamp(get_max_start_time())

    now = now + utc_offset

    df_blank, begin = get_blank_time_summary(days, hour, now, utc_hour)

    # Fetch from database, convert to DataFrame
    matches = mongo_db.matches.find(
        filter={"start_time": {"$gte": begin}},
        projection={"start_time": 1, "api_skill": 1}
    )
    rows = pd.DataFrame(matches)

    if len(rows) == 0:
        df_summary = df_blank
    else:

        # Trim columns and renamed
        rows = rows[['start_time', 'api_skill']]
        rows = rows.rename(columns={
            'start_time': 'time',
            'api_skill': 'skill'
        })

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


def main(days, use_current_time=True):
    """Main program execution"""

    mongo_db = connect_mongo()

    if use_current_time:
        now = dt.datetime.utcnow()
    else:
        now = dt.datetime.utcfromtimestamp(db_util.get_max_start_time())

    text, begin, end = dotautil.TimeMethods.get_hour_blocks(
        now.timestamp(),
        int(days * 24)
    )

    date_hours = []
    skills = []
    match_ids = []

    for ttime, btime, etime in zip(text, begin, end):
        for skill in [1, 2, 3]:
            query = {
                '_id': {
                    '$gte': db_util.get_key(skill, btime, 0),
                    '$lte': db_util.get_key(skill, etime, 0),
                }
            }

            date_hours.append(btime)
            skills.append(skill)
            match_ids.append(mongo_db.matches.count_documents(query))

    summary = pd.DataFrame({
        'date_hour': date_hours,
        'skill': skills,
        'match_ids': match_ids
    })

    log.info("Writing %d records to database", len(summary))

    # Write to database, overwriting old records
    for _, row in summary.iterrows():

        doc = {
            "_id": "{0:10d}_{1}".format(
                row['date_hour'],
                row['skill']),
            "rec_count": int(row['match_ids']),
        }

        mongo_db.fetch_summary.replace_one(
            {"_id": doc['_id']}, doc, upsert=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update table containing '
                                                 'record count by hour.')
    parser.add_argument("horizon_days", type=int)
    opts = parser.parse_args()

    main(opts.horizon_days)
