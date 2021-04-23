# -*- coding: utf-8 -*-
"""Generates statistics for hero/hero pairings"""

import pandas as pd
from dota_stats.db_util import connect_mongo, get_max_start_time
from dota_stats import meta


def query_hero_matches(mongo, hero, radiant_flag, skill, begin_time):
    """Query database for hero match-up raw data. If radiant flag is
    True, return data for hero on radiant team, otherwise return for
    dire. Skill is 1, 2, 3 denoting nromal, high, and very high in the
    API.

    Returns a tuple of `(hero, wins, matches)`, where `hero` is the
    opposing hero number.
    """
    # TODO: Check that hero is valid!!!

    matchups = []
    # Radiant
    query = {
        'start_time': {"$gte": begin_time},
        'api_skill': {'$eq': skill},
    }

    if radiant_flag:
        key = "rh-{}".format(hero)
        query[key] = {"$exists": True}
    else:
        key = "dh-{}".format(hero)
        query[key] = {"$exists": True}

    results = mongo.matches.find(query)

    for result in results:
        if result['radiant_win']:
            if radiant_flag:
                win = 1
            else:
                win = 0
        else:
            if radiant_flag:
                win = 0
            else:
                win = 1

        if radiant_flag:
            for dhero in result['dire_heroes']:
                matchups.append((dhero, win, 1))
        else:
            for rhero in result['radiant_heroes']:
                matchups.append((rhero, win, 1))

    return matchups


def main():
    hero = 'axe'
    days = 1
    skill = 1

    mongo = connect_mongo()
    end = get_max_start_time()
    begin = end - days * 24 * 60 * 60

    matchups = []
    matchups.extend(query_hero_matches(mongo, hero, True, skill, begin))
    matchups.extend(query_hero_matches(mongo, hero, False, skill, begin))

    df_matchups = pd.DataFrame(matchups)
    df_matchups.columns = ['hero', 'wins', 'matches']

    df_summary = df_matchups.groupby('hero').sum().reset_index()
    df_summary['hero'] = [meta.HERO_DICT[t] for t in df_summary['hero']]

    df_summary['win_rate'] = df_summary['wins'] / df_summary['matches']

    return df_summary


if __name__ == "__main__":
    dfs = main()
    import pdb
    pdb.set_trace()
