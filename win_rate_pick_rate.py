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



def fetch_records(begin, end):
    pass


def parse_records(matches):
    """Create summary table as a pandas DataFrame"""

    summary = pd.DataFrame({
        'hero' : meta.HEROES,
        'radiant_win': meta.NUM_HEROES*[0],
        'radiant_total': meta.NUM_HEROES*[0],
        'dire_win': meta.NUM_HEROES*[0],
        'dire_total': meta.NUM_HEROES*[0],
    })
    ihero = 0
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


def write_to_database(session, summary, skill, end_time, text_time):
    """Update win rate data in database"""

    for idx, row in summary.iterrows():

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


def main(days):
    """Main entry point"""

    text, begin, end = db_util.get_hour_blocks(
        db_util.get_max_start_time(),
        int(days*24)
    )

    # Get database connection
    engine, session = db_util.connect_database()

    with engine.connect() as conn:
        for skill in [3, 2, 1]:
            for ttime, btime, etime in zip(text, begin, end):
                stmt = "select radiant_win, radiant_heroes, dire_heroes from " \
                       "dota_matches where start_time>={0} and start_time<={1}"\
                       " and api_skill={2};".format(btime, etime, skill)
                matches = conn.execute(stmt)
                log.info("Skill level: {0} Time: {1} Count: {2}".\
                         format(skill, ttime, matches.rowcount))

                print(stmt)

                df_hero = parse_records(matches)
                write_to_database(session, df_hero, skill, etime, ttime)


if __name__ == "__main__":

    # Parse command line and enter main entry point
    parser = argparse.ArgumentParser(
        description='Calculate win rate vs. pick rate at all skill levels.')
    parser.add_argument('days', type=int)
    args = parser.parse_args()
    main(args.days)
