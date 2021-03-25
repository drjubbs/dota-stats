# -*- coding: utf-8 -*-
"""Calculate summary win rate statistics for each hero, radiant vs. dire. This
should be automated in a cron job.
"""
import argparse
import sys
import time
import datetime as dt
import pandas as pd
from dota_stats import db_util, dotautil, meta
from dota_stats.log_conf import get_logger

log = get_logger("win_rate_pick_rate")


def parse_records(matches):
    """Alternative version"""

    rad_heroes = []
    radiant_win = []
    radiant_count = []
    dire_heroes = []
    dire_win = []
    dire_count = []
    count = 0

    for match in matches:

        rhs = match['radiant_heroes']
        dhs = match['dire_heroes']

        for hero in rhs:
            rad_heroes.append(hero)
            radiant_count.append(1)
            if match['radiant_win'] == 1:
                radiant_win.append(1)
            else:
                radiant_win.append(0)

        for hero in dhs:
            dire_heroes.append(hero)
            dire_count.append(1)
            if match['radiant_win'] == 1:
                dire_win.append(0)
            else:
                dire_win.append(1)

        count += 1

    df_radiant = pd.DataFrame({'hero': rad_heroes,
                               'radiant_win': radiant_win,
                               'radiant_total': radiant_count})
    df_radiant = df_radiant.groupby("hero").sum()
    df_radiant.reset_index(inplace=True)

    df_dire = pd.DataFrame({'hero': dire_heroes,
                            'dire_win': dire_win,
                            'dire_total': dire_count})
    df_dire = df_dire.groupby("hero").sum()
    df_dire.reset_index(inplace=True)

    df_total = pd.DataFrame({'hero': meta.HEROES})

    df_total = df_total.merge(df_radiant, how='left', on='hero'). \
        merge(df_dire, how='left', on='hero')
    df_total = df_total.fillna(0)

    return df_total, count


def write_to_database(mongo_db, summary, skill, end_time):
    """Update win rate data in database"""

    # Coerce to integers
    summary = summary.astype('int')

    for _, row in summary.iterrows():
        doc_id = "{0:1}_{1:10}_{2:03}".format(skill, end_time, row['hero'])
        doc = {
            '_id': doc_id,
            'time': end_time,
            'hero': int(row['hero']),
            'skill': skill,
            'radiant_win': int(row['radiant_win']),
            'radiant_total': int(row['radiant_total']),
            'dire_win': int(row['dire_win']),
            'dire_total': int(row['dire_total']),
        }
        mongo_db.hero_win_rate.replace_one({"_id": doc_id}, doc, upsert=True)


def get_default_summary():
    """Return a DataFrame with null entries to ensure code works if the
     database is left blank or a skill level is missing"""

    numh = meta.NUM_HEROES
    df_default = pd.DataFrame({
        'hero': 3 * list(meta.HERO_DICT.keys()),
        'skill': numh*[1] + numh*[2] + numh*[3],
        'radiant_win': 3 * meta.NUM_HEROES * [0],
        'radiant_total': 3 * meta.NUM_HEROES * [0],
        'dire_win': 3 * meta.NUM_HEROES * [0],
        'dire_total': 3 * meta.NUM_HEROES * [0],
    })

    return df_default


def get_current_win_rate_table(mongo_db, days):
    """Sets a summary table for current win rates, spanning `days` worth of
    time"""
    summary = pd.DataFrame(mongo_db.hero_win_rate.find())

    # Columns to re-arrange into... used later for now construct blank
    # dataframe if needed
    cols = ['hero_skill', 'skill', 'hero', 'time_range', 'radiant_win',
            'radiant_total', 'radiant_win_pct', 'dire_win', 'dire_total',
            'dire_win_pct', 'win', 'total', 'win_pct']

    summary = summary[['hero', 'skill', 'radiant_win', 'radiant_total',
                       'dire_win', 'dire_total']]

    # Blank/zero entries for each hero/skill so the code doesn't crash if a
    # hero or skill level is missing or the database has no entries.

    default_summary = get_default_summary()
    summary = pd.concat([summary, default_summary])

    grpd = summary.groupby(["hero", "skill"]).sum()
    grpd.reset_index(inplace=True)

    # Actual hero names & legacy label field
    grpd['hero'] = [meta.HERO_DICT[a] for a in grpd['hero']]
    grpd['hero_skill'] = [a.upper() + "_" + str(b) for a, b in
                          zip(grpd['hero'], grpd['skill'])]

    # Time string
    end = int(db_util.get_max_start_time())
    begin = int(end - days * 24 * 3600)

    sbegin = dt.datetime.utcfromtimestamp(begin).isoformat()
    send = dt.datetime.utcfromtimestamp(end).isoformat()
    grpd['time_range'] = "{0} to {1}".format(sbegin, send)

    # Maths
    grpd['win'] = grpd['radiant_win'] + grpd['dire_win']
    grpd['total'] = grpd['radiant_total'] + grpd['dire_total']

    grpd['radiant_win_pct'] = 100.0 * grpd['radiant_win'] / grpd[
        'radiant_total']
    grpd['dire_win_pct'] = 100.0 * grpd['dire_win'] / grpd['dire_total']
    grpd['win_pct'] = 100.0 * grpd['win'] / grpd['total']
    grpd = grpd.fillna(0)

    grpd = grpd[cols]

    return grpd


def main(days, skill):
    """Main entry point"""

    mongo_db = db_util.connect_mongo()
    text, begin, end = dotautil.TimeMethods.get_hour_blocks(
        db_util.get_max_start_time(),
        int(days * 24)
    )

    for ttime, btime, etime in zip(text, begin, end):
        qbegin = time.time()

        matches = mongo_db.matches.find(
            {'_id': {
                '$gte': db_util.get_key(skill, btime, 0),
                '$lte': db_util.get_key(skill, etime, 0)
            }}
        )
        df_hero, count = parse_records(matches)
        write_to_database(mongo_db, df_hero, skill, etime)

        qend = time.time()
        log.info("Skill level: %d Match Time: %s Count: %7d Processing: %f",
                 skill, ttime, count, qend - qbegin)


if __name__ == "__main__":

    # Parse command line and enter main entry point
    parser = argparse.ArgumentParser(
        description='Calculate win rate vs. pick rate at all skill levels.')
    parser.add_argument('days', type=int)
    parser.add_argument('skill', type=int)
    args = parser.parse_args()

    if args.skill not in [1, 2, 3]:
        parser.print_help()
        sys.exit(-1)

    main(args.days, args.skill)
