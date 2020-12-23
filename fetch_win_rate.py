# -*- coding: utf-8 -*-
"""Calculate summary win rate statistics for each hero, radiant vs. dire. This
should be automated in a cron job.
"""
import argparse
import meta
import pandas as pd
import datetime as dt
import json
from server.server import db
from db_util import WinRatePickRate, connect_database


def parse_records(matches):
    """Create summary table as a pandas DataFrame"""

    summary = {
        'radiant_win': [],
        'radiant_total': [],
        'dire_win': [],
        'dire_total': [],
    }
    counter = 0

    rowcount = matches.rowcount

    for match in matches:
        if counter % 10000 == 0:
            print("{} of {}".format(counter, rowcount))

        rhs = json.loads(match.radiant_heroes)
        dhs = json.loads(match.dire_heroes)

        for hero in rhs:
            summary['radiant_total'].append(meta.HERO_DICT[hero])
            if match.radiant_win == 1:
                summary['radiant_win'].append(meta.HERO_DICT[hero])
        for hero in dhs:
            summary['dire_total'].append(meta.HERO_DICT[hero])
            if match.radiant_win == 0:
                summary['dire_win'].append(meta.HERO_DICT[hero])

        counter += 1
    
    # Radiant Summary
    df_radiant_win = pd.DataFrame(summary['radiant_win'], columns=['hero'])
    df_radiant_win['radiant_win'] = 1
    df_radiant_win = df_radiant_win.groupby("hero").count()
    df_radiant_total = pd.DataFrame(summary['radiant_total'], columns=['hero'])
    df_radiant_total['radiant_total'] = 1
    df_radiant_total = df_radiant_total.groupby("hero").count()
    df1 = df_radiant_win.join(df_radiant_total, how='outer').fillna(0)
    df1['radiant_win_pct'] = 100.0*df1['radiant_win']/df1['radiant_total']

    # Dire Summary
    df_dire_win = pd.DataFrame(summary['dire_win'], columns=['hero'])
    df_dire_win['dire_win'] = 1
    df_dire_win = df_dire_win.groupby("hero").count()
    df_dire_total = pd.DataFrame(summary['dire_total'], columns=['hero'])
    df_dire_total['dire_total'] = 1
    df_dire_total = df_dire_total.groupby("hero").count()
    df2 = df_dire_win.join(df_dire_total, how='outer').fillna(0)
    df2['dire_win_pct'] = 100.0*df2['dire_win']/df2['dire_total']

    df_hero = df1.join(df2, how='outer').fillna(0)
    df_hero['win'] = df_hero['radiant_win']+df_hero['dire_win']
    df_hero['total'] = df_hero['radiant_total']+df_hero['dire_total']
    df_hero['win_pct'] = 100.0*df_hero['win']/df_hero['total']

    """
    # Integrity checks
    if not(int(df_hero.sum()['radiant_total']) == rowcount*5):
        raise ValueError("Data integrity check fail")
    if not(int(df_hero.sum()['dire_total']) == rowcount*5):
        raise ValueError("Data integrity check fail")
    if not(int(df_hero.sum()['radiant_win'])+int(df_hero.sum()['dire_win']) ==
           rowcount*5)):
        raise ValueError("Data integrity check fail")
    if not(int(df_hero.sum()['total']) == 10*len(matches)):
        raise ValueError("Data integrity check fail")
    if not(int(df_hero.sum()['win']) == 5*len(matches)):
        raise ValueError("Data integrity check fail")
    """

    return df_hero


def write_to_database(df_hero, skill, time_range):
    """Update win rate data in database"""

    for idx, row in df_hero.iterrows():

        wrpr = WinRatePickRate()

        wrpr.hero_skill = idx.upper().replace("-", "_")+"_"+str(skill),
        wrpr.skill = skill
        wrpr.hero = idx
        wrpr.time_range = time_range
        wrpr.radiant_win = row['radiant_win'],
        wrpr.radiant_total = row['radiant_total']
        wrpr.radiant_win_pct = row['radiant_win_pct']
        wrpr.dire_win = row['dire_win']
        wrpr.dire_total = row['dire_total']
        wrpr.dire_win_pct = row['dire_win_pct']
        wrpr.win = row['win']
        wrpr.total = row['total']
        wrpr.win_pct = row['win_pct']

        db.session.merge(wrpr)

    db.session.commit()


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description='Calculate win rate vs. pick rate at all skill levels.')
    parser.add_argument('days', type=int)

    args = parser.parse_args()
        
    utc = dt.datetime.utcnow()
    end = dt.datetime(utc.year, utc.month, utc.day, utc.hour, 0)
    begin = end-dt.timedelta(days=args.days)

    # Get database connection
    engine, session = connect_database()

    # Drop all records
    win_rate = session.query(WinRatePickRate)
    win_rate.delete(synchronize_session=False)

    for skill in [3, 2, 1]:
        
        print("Skill level: {}".format(skill))
        
        time_range = "{} to {}".format(
            begin.strftime("%Y-%m-%d %H:%M"),
            end.strftime("%Y-%m-%d %H:%M"))

        with engine.connect() as conn:
            stmt = "select radiant_win, radiant_heroes, dire_heroes from " \
                   "dota_matches where start_time>={0} and start_time<={1} " \
                   "and api_skill={2};".format(begin.timestamp(),
                                               end.timestamp(), skill)

            matches = conn.execute(stmt)
            print("Row count: {}".format(matches.rowcount))

        df_hero = parse_records(matches)
        write_to_database(df_hero, skill, time_range)


if __name__ == "__main__":
    main()
