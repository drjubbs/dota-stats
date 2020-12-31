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
    """Create summary table as a pandas DataFrame"""

    summary = pd.DataFrame({
        'hero': meta.HEROES,
        'radiant_win': meta.NUM_HEROES*[0],
        'radiant_total': meta.NUM_HEROES*[0],
        'dire_win': meta.NUM_HEROES*[0],
        'dire_total': meta.NUM_HEROES*[0],
    })

    iradiant_win = 1
    iradiant_total = 2
    idire_win = 3
    idire_total = 4

    # Return if we have no records
    if matches.rowcount == 0:
        return summary

    for match in matches:
        rhs = json.loads(match.radiant_heroes)
        dhs = json.loads(match.dire_heroes)

        for hero in rhs:
            idx = meta.HEROES.index(hero)
            summary.iloc[idx, iradiant_total] += 1
            if match.radiant_win == 1:
                summary.iloc[idx, iradiant_win] += 1

        for hero in dhs:
            idx = meta.HEROES.index(hero)
            summary.iloc[idx, idire_total] += 1
            if match.radiant_win == 0:
                summary.iloc[idx, idire_win] += 1

    return summary


def write_to_database(session, summary, skill, end_time):
    """Update win rate data in database"""

    for _, row in summary.iterrows():

        hwr = db_util.HeroWinRate()
        hwr.time_hero_skill = "{0}_H{1:03}_S{2}".format(
            end_time, row['hero'], skill)

        hwr.time = end_time
        hwr.hero = row['hero']
        hwr.skill = skill
        hwr.radiant_win = row['radiant_win']
        hwr.radiant_total = row['radiant_total']
        hwr.dire_win = row['dire_win']
        hwr.dire_total = row['dire_total']

        session.merge(hwr)
    session.commit()


def get_current_win_rate_table(days):
    """Sets a summary table for current win rates, spanning `days` worth of
    time"""

    engine, _ = db_util.connect_database()
    end = int(db_util.get_max_start_time())
    begin = int(end - days * 24 * 3600)

    stmt = "SELECT * FROM dota_hero_win_rate WHERE time>={0} AND time<={1};".\
        format(begin, end)
    summary = pd.read_sql(stmt, engine)
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

    # Re-arrange
    cols = ['hero_skill', 'skill', 'hero', 'time_range', 'radiant_win',
            'radiant_total', 'radiant_win_pct', 'dire_win', 'dire_total',
            'dire_win_pct', 'win', 'total', 'win_pct']
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
