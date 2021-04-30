# -*- coding: utf-8 -*-
"""fetch_summary - Update table containing record counts cache in database,
used to monitor the health of the fetch job.

HORIZON_DAYS controls how far back in history is reprocessed each time
the script runs.
"""
import argparse
import datetime as dt
from dateutil import parser
import pandas as pd
from dota_stats.db_util import connect_mongo, get_max_start_time
from dota_stats import dotautil, db_util
from dota_stats.log_conf import get_logger

log = get_logger("fetch_summary")


def get_blank_time_summary(days, hour, start):
    """Create a blank dataframe for the time range of interest.

    days: how many days to create a blank data frame for
    hours: boolean, if true hourly data, if false do daily data
    start: beginning time of data frame
    """

    if hour:
        now_rnd = dt.datetime(start.year, start.month, start.day,
                              start.hour, 0, 0)
        times = [(now_rnd - dt.timedelta(hours=i)).isoformat()
                 for i in range(24 * days)]

    else:
        now_rnd = dt.datetime(start.year, start.month, start.day,
                              0, 0, 0)
        times = [(now_rnd - dt.timedelta(days=i)).isoformat()
                 for i in range(days)]

    # Blank dataframe, one entry for each skill level...
    df_blank = pd.DataFrame(index=times, data={
        1: [0] * len(times),
        2: [0] * len(times),
        3: [0] * len(times),
    })

    begin = int(parser.parse(df_blank.index[-1]).timestamp())
    end = int(parser.parse(df_blank.index[0]).timestamp())
    return df_blank, begin, end


def get_fetch_summary(mongo_db, begin, end, hour):
    """Fetch summary stastics and return as dataframe. Round times
    to nearest day if appropriate and pivot as approriate.
    """
    # Select records over the requested time horizon
    query = dict(start_time={'$gte': begin,
                             '$lte': end})

    # Fetch and unpack results
    fetch_summary = mongo_db.fetch_summary.find(query)
    times = []
    skills = []
    counts = []
    for fsum in fetch_summary:

        # Round to nearest hour or day
        this_time = dotautil.TimeMethods.get_time_nearest(
            fsum['start_time'], hour=hour)[0]
        times.append(this_time)
        skills.append(fsum['skill'])
        counts.append(fsum['rec_count'])

    df_fetch = pd.DataFrame({
        'time': times,
        'skill': skills,
        'rec_count': counts,
    })

    # If days was requested, we need to group and sum (fetch_summary table
    # contains hourly data
    df_fetch2 = df_fetch.groupby(["time", "skill"]).sum().reset_index()
    df_fetch3 = df_fetch2.pivot(index='time',
                                values="rec_count",
                                columns="skill")

    # Index on isoformat, useful for plotting
    df_fetch3.index = [dt.datetime.utcfromtimestamp(t).isoformat()
                       for t in df_fetch3.index]
    return df_fetch3


def get_health_summary(mongo_db, days, hour=True,
                       use_current_time=True):
    """Returns a Pandas dataframe summarizing number of matches processed
    over an interval of hours or days. Defaults to by hour, can we chaned to
    daily view through use of optional `hour` argument`.

    mongo_db: Instance of Mongo client
    days: Number of days to summarize over
    hour: If true hourly summary, otherwise daily
    use_current_time: If true, use current time to create beginning of
                      otherwise use the most recent date in the database.
    """

    if use_current_time:
        now = dt.datetime.utcnow()
    else:
        # If most recent time in database, add one day to ensure we get most
        # recent records (i.e. not lost to rounding)
        now = dt.datetime.fromtimestamp(get_max_start_time() + 86400)

    # Get zero'd out datafrane and add in results so missing days/hours
    # are report as zero
    df_blank, begin, end = get_blank_time_summary(days, hour, now)
    df_fetch = get_fetch_summary(mongo_db, begin, end, hour)

    # Add to blank and downcast to integer
    df_summary = df_blank.add(df_fetch, fill_value=0)
    df_summary = df_summary.astype('int')

    # Rename columns and sort
    df_summary = df_summary[[1, 2, 3]]
    df_summary.columns = ['normal', 'high', 'very_high']
    df_summary = df_summary.sort_index(ascending=False)

    return df_summary


def create_fetch_summary(mongo_db, now, days):
    """
    Create dataframe summarizing the number of records in hourly buckets
    starting with now.

    @param mongo_db: Instance of database connection
    @param now: datetime object representing the start of processing
    @param days: how many days to process relative to `now`
    @return: Pandas DataFrame
    """

    text, begin, end = dotautil.TimeMethods.get_hour_blocks(
        now.timestamp(),
        int(days * 24)
    )

    date_hours = []
    skills = []
    match_ids = []

    for _, btime, etime in zip(text, begin, end):
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

    return summary


def main(days, use_current_time=True):
    """Populate the database with updated record counts from the `fetch`
    routines. This effectively caches the record count for fast recall in
    the web front-end.

    @param days: Number of days backward to go in time
    @param use_current_time: Base results on current time, or last record in
    database. Last record generaly used for debugging only.
    @return: None
    """

    mongo_db = connect_mongo()

    if use_current_time:
        now = dt.datetime.utcnow()
    else:
        now = dt.datetime.utcfromtimestamp(db_util.get_max_start_time())

    summary = create_fetch_summary(mongo_db, now, days)

    log.info("Writing %d records to database", len(summary))

    # Write to database, overwriting old records
    for _, row in summary.iterrows():

        doc = {
            "_id": "{0:10d}_{1}".format(
                row['date_hour'],
                row['skill']),
            "start_time": int(row['date_hour']),
            "skill": int(row["skill"]),
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
