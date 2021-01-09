# -*- coding: utf-8 -*-
"""Calculate summary win rate statistics for each hero, radiant vs. dire. This
should be automated in a cron job.
"""
import argparse
import logging
import os
import sys
import datetime as dt
import json
import pandas as pd
import db_util
import dotautil
import meta


# Logging
log = logging.getLogger("prwr")
if int(os.environ['DOTA_LOGGING']) == 0:
    log.setLevel(logging.INFO)
else:
    log.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
fmt = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%S %Z")
ch.setFormatter(fmt)
log.addHandler(ch)


def parse_records(matches):
    """Alternative version"""

    rad_heroes = []
    radiant_win = []
    radiant_count = []
    dire_heroes = []
    dire_win = []
    dire_count = []

    for match in matches:
        rhs = json.loads(match.radiant_heroes)
        dhs = json.loads(match.dire_heroes)

        for hero in rhs:
            rad_heroes.append(hero)
            radiant_count.append(1)
            if match.radiant_win == 1:
                radiant_win.append(1)
            else:
                radiant_win.append(0)

        for hero in dhs:
            dire_heroes.append(hero)
            dire_count.append(1)
            if match.radiant_win == 1:
                dire_win.append(0)
            else:
                dire_win.append(1)

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

    df_total = pd.DataFrame({'hero':  meta.HEROES})

    df_total = df_total.merge(df_radiant, how='left', on='hero').\
        merge(df_dire, how='left', on='hero')
    df_total = df_total.fillna(0)

    return df_total


def write_to_database(session, summary, skill, end_time):
    """Update win rate data in database"""

    rows = []
    engine, session = db_util.connect_database()

    # Coerce to integers
    summary = summary.astype('int')

    for _, row in summary.iterrows():
        time_hero_skill = "{0}_H{1:03}_S{2}".format(end_time, row['hero'], skill)

        rows.append((
                time_hero_skill,
                end_time,
                row['hero'],
                skill,
                row['radiant_win'],
                row['radiant_total'],
                row['dire_win'],
                row['dire_total']))

    conn = engine.raw_connection()
    cursor = conn.cursor()
    stmt = "REPLACE INTO dota_hero_win_rate VALUES (%s, %s, %s, %s, %s, %s, " \
           "%s, %s)"
    cursor.executemany(stmt, rows)


def get_current_win_rate_table(days):
    """Sets a summary table for current win rates, spanning `days` worth of
    time"""

    engine, _ = db_util.connect_database()
    end = int(db_util.get_max_start_time())
    begin = int(end - days * 24 * 3600)

    stmt = "SELECT * FROM dota_hero_win_rate WHERE time>={0} AND time<={1};".\
        format(begin, end)
    summary = pd.read_sql(stmt, engine)

    # Columns to re-arrange into... used later for now construct blank
    # dataframe if needed
    cols = ['hero_skill', 'skill', 'hero', 'time_range', 'radiant_win',
            'radiant_total', 'radiant_win_pct', 'dire_win', 'dire_total',
            'dire_win_pct', 'win', 'total', 'win_pct']

    summary = summary[['hero', 'skill', 'radiant_win', 'radiant_total',
                       'dire_win', 'dire_total']]
    grpd = summary.groupby(["hero", "skill"]).sum()
    grpd.reset_index(inplace=True)

    # Actual hero names & legacy label field
    grpd['hero'] = [meta.HERO_DICT[a] for a in grpd['hero']]
    grpd['hero_skill'] = [a.upper()+"_"+str(b) for a, b in
                          zip(grpd['hero'], grpd['skill'])]

    # Time string
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


def main(days):
    """Main entry point"""

    text, begin, end = dotautil.TimeMethods.get_hour_blocks(
        db_util.get_max_start_time(),
        int(days*24)
    )

    # Get database connection
    engine, session = db_util.connect_database()

    with engine.connect() as conn:
        for skill in [1, 2, 3]:
            for ttime, btime, etime in zip(text, begin, end):
                stmt = "select radiant_win, radiant_heroes, dire_heroes from " \
                       "dota_matches where start_time>={0} and start_time<={1}"\
                       " and api_skill={2};".format(btime, etime, skill)
                matches = conn.execute(stmt)
                log.info("Skill level: %d Time: %s Count: %d", skill, ttime,
                         matches.rowcount)

                df_hero = parse_records(matches)
                write_to_database(session, df_hero, skill, etime)


if __name__ == "__main__":

    # Parse command line and enter main entry point
    parser = argparse.ArgumentParser(
        description='Calculate win rate vs. pick rate at all skill levels.')
    parser.add_argument('days', type=int)
    args = parser.parse_args()
    main(args.days)
