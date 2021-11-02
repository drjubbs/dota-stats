# -*- coding: utf-8 -*-
"""fetch.py

Fetches, parses, and puts matches into MariaDB using steam API. This script
is usually run using `crontab` and `flock` on a regular basis.

To avoid duplicate data pulls, on loading, creates a dictionary of already
fetched matches within a time horizon. The main routine creates a
ThreadPoolExecutor which is used to parallelize data pulls and process.
The main routine calls `fetch_matches`, which uses the `GetMatchHistory`
endpoint to fetch recent matches for a specified `hero` and `skill` level.
This continues in a loop until no more matches are found.

The matches IDs are passed in the `process_matches` along with some metadata
and the executor. The internal dictionary is updated to prevent "re-pulls" of
matches. `process_matches` calls `process_match` in either a single thread or
multiple threads depending on the multithreading setup. This is point at which
the process is parallelized. `process_match` calls `fetch_match` to grab a
single match from the API, parses the output in `parse_match`, and returns.
`parse_match` is where filtering conditions are applied. A call is made to
`parse_players` which handles that subset of the match info.

Control is returned to `process_matches` and data is written into database
in `write_matches` if valid matches still exist.
"""
import os
import sys
import ssl
import json
import argparse
import time
from functools import partial
from concurrent import futures
import datetime as dt
import requests
import numpy as np
from dota_stats import meta, db_util
from log_conf import get_logger

log = get_logger("fetch")

# Globals
NUM_THREADS = int(os.environ['DOTA_THREADS'])  # 1 = single threaded
MIN_MATCH_LEN = 1200
INITIAL_HORIZON = 3  # Days to load from database on start-up
CTX = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

# Globals used in multi-threading
MATCH_IDS = {}

PLAYER_FIELDS = [
    "account_id",
    "player_slot",
    "hero_id",
    "item_0",
    "item_1",
    "item_2",
    "item_3",
    "item_4",
    "item_5",
    "backpack_0",
    "backpack_1",
    "backpack_2",
    "kills",
    "deaths",
    "assists",
    "leaver_status",
    "last_hits",
    "denies",
    "gold_per_min",
    "xp_per_min",
    "level",
    "hero_damage",
    "tower_damage",
    "hero_healing",
    "gold",
    "gold_spent",
    "scaled_hero_damage",
    "scaled_tower_damage",
    "scaled_hero_healing"
]


class ParseException(Exception):
    """Used to indicate a parse error in the JSON from Valve API"""


class APIException(Exception):
    """Used to indicate an error fetching from the Valve API"""


def fetch_url(url):
    """Simple wait loop around fetching to deal with things like network
    outages, etc..."""

    sleep_schedule = np.logspace(-0.5, 3, 20)
    sleep_schedule += sleep_schedule * np.random.rand(20)
    for sleep in sleep_schedule:
        time.sleep(np.random.uniform(0.3 * sleep, 0.7 * sleep))
        headers = {
            'Accept': 'gzip',
            'Content-Encoding': 'gzip',
            'Content-Type': 'application/json',
        }
        try:
            resp = requests.get(url, headers=headers, timeout=60)
        except requests.exceptions.ConnectionError as conn_error:
            log.error("Connection error: %r", conn_error)
        except requests.exceptions.ReadTimeout as timeout_error:
            log.error("Timeout error: %r", timeout_error)
        else:
            # Normal response
            if resp.status_code == 200:
                resp_json = json.loads(resp.content)
                if 'error' in resp_json['result']:
                    raise APIException(resp_json['result']['error'])
                return resp_json['result']

            # Error handling
            if resp.status_code == 429:
                log.error("Too many requests")
            elif resp.status_code == 503:
                log.error("Service unavailable")
            elif resp.status_code == 403:
                raise APIException("Forbidden - Check Steam API key")
            else:
                log.error("Unknown repsonse %d %s", resp.status_code,
                          resp.reason)

    raise ValueError("Could not fetch (timeout?): {}".format(url))


def parse_players(match_id, players):
    """Parse the players section of the JSON response."""

    radiant_heroes = []
    radiant_gpm = []
    dire_heroes = []
    dire_gpm = []
    items_dict = {}
    gold_spent = {}
    leaver = False

    for player in players:
        # DOTA_LEAVER_NONE = 0;
        # DOTA_LEAVER_DISCONNECTED = 1;
        # DOTA_LEAVER_DISCONNECTED_TOO_LONG = 2;
        # DOTA_LEAVER_ABANDONED = 3;
        # DOTA_LEAVER_AFK = 4;
        # DOTA_LEAVER_NEVER_CONNECTED = 5;
        # DOTA_LEAVER_NEVER_CONNECTED_TOO_LONG = 6;

        if player['leaver_status'] > 1:
            leaver = True

        player_slot = player['player_slot']

        # Check to see if we're missing a hero ID
        if player['hero_id'] not in meta.HERO_DICT.keys():

            if player['hero_id'] == 0:
                raise ParseException("Null Hero ID")
            raise ValueError("Missing hero: {} {}".format(
                match_id, player['hero_id']))

        # Check for intentional feeding
        if player['deaths'] > 30 and player['kills'] < 5:
            raise ParseException("Feeding")

        if player_slot <= 4:
            radiant_heroes.append(player['hero_id'])
            radiant_gpm.append(player['gold_per_min'])
        else:
            dire_heroes.append(player['hero_id'])
            dire_gpm.append(player['gold_per_min'])

        # Net worth
        gold_spent[str(player['hero_id'])] = player['gold_spent']

        # Get active items on hero
        items = []
        item_fields = [t for t in player.keys() if t[0:4] == 'item']
        for field in item_fields:
            items.append(player[field])

        # No/destroyed items
        if set(items) == {0}:
            raise ParseException("No items")

        bp_fields = [t for t in player.keys() if t[0:8] == 'backpack']
        for field in bp_fields:
            items.append(player[field])

        items_dict[str(player['hero_id'])] = items

        # Sort heroes by farm -- probably not correct but good first pass
        radiant_heroes = [x for _, x in sorted(zip(radiant_gpm,
                                                   radiant_heroes),
                                               reverse=True)]
        dire_heroes = [x for _, x in sorted(zip(dire_gpm, dire_heroes),
                                            reverse=True)]

    return leaver, radiant_heroes, dire_heroes, items_dict, gold_spent


def parse_match(match):
    """Parse match info from main API endpoint. Player section is broken
    out into a separate subroutine for clarity.
    """
    match['batch_time'] = int(
        dt.datetime.fromtimestamp(match['start_time']).strftime("%Y%m%d_%H%M"))

    valid_game_modes = ["game_mode_all_pick",
                        "game_mode_captains_mode",
                        "game_mode_random_draft",
                        "game_mode_single_draft",
                        "game_mode_all_random",
                        "game_mode_least_played",
                        "game_mode_captains_draft",
                        "game_mode_all_draft"]

    game_mode = meta.MODE_ENUM[str(match['game_mode'])]['name']

    # Bad game mode
    if game_mode not in valid_game_modes:
        raise ParseException("Bad Mode: {}".format(game_mode))

    # Bail if zero length matches
    if match['duration'] < MIN_MATCH_LEN:
        raise ParseException("Min Length")

    # Lobby types
    if not match['lobby_type'] in meta.LOBBY_ENUM.values():
        raise ValueError("Unknown lobby type: {}".format(match['match_id']))
    if not (match['lobby_type'] in [0, 2, 7, 9, 13]):
        raise ParseException("Lobby Type")

    players = match["players"]

    # Bail if Missing players
    if {} in players:
        raise ParseException("Min Players")

    leaver, radiant_heroes, dire_heroes, items_dict, gold_spent = \
        parse_players(match['match_id'], players)

    if leaver:
        raise ParseException("Leaver")

    summary = {
        'match_id': match['match_id'],
        'start_time': match['start_time'],
        'radiant_heroes': radiant_heroes,
        'dire_heroes': dire_heroes,
        'radiant_win': match['radiant_win'],
        'api_skill': match['api_skill'],
        'items': items_dict,
        'gold_spent': gold_spent,
    }

    return summary


def fetch_match(match_id, skill):
    """Skill is optional, this simply sets an object in the json
    for reference"""

    url = "https://api.steampowered.com/IDOTA2Match_570/"
    url += "GetMatchDetails/V001/?key={0}&match_id={1}"

    match = {}
    for _ in range(10):
        match = fetch_url(url.format(os.environ['STEAM_KEY'], match_id))
        if 'start_time' in match.keys():
            break

        log.error("Match ID not found: %s", str(match_id))
        time.sleep(1)

    match['api_skill'] = skill

    # If something went wrong, log to file and return no match
    if 'start_time' not in match.keys():
        if not os.path.exists('error'):
            os.makedirs('error')
        with open("./error/{}.json".format(match_id), "w") as file_handle:
            file_handle.write(json.dumps(match))
        raise APIException("Bad match JSON {}".format(match_id))

    return match


def process_match(hero, skill, match_id):
    """Process a single match, used by the multi-threading engine."""

    txt = "match ID {0} hero {1:3} skill {2}".format(match_id, hero, skill)

    try:
        match = fetch_match(match_id, skill)
    except APIException as e_msg:
        log.error("{0:30.30} {1}". format("API Error", str(e_msg)))
        return None

    try:
        summary = parse_match(match)
        log.debug("{0:30.30} {1}". format("Success", txt))
        return summary
    except ParseException as e_msg:
        log.debug("{0:30.30} {1}". format(str(e_msg), txt))
        return None


def write_matches(mongo_db, matches):
    """Write matches to database"""

    for summary in matches:

        # Index by time + match to speed up searching
        key = db_util.get_key(
            summary['api_skill'],
            summary['start_time'],
            summary['match_id'],
        )
        summary['_id'] = key

        # Expand out the heroes into columns for hero pair searching
        radiant = [meta.HERO_DICT[int(t)] for t in summary['radiant_heroes']]
        for hero in radiant:
            summary["rh-" + hero] = 1

        dire = [meta.HERO_DICT[int(t)] for t in summary['dire_heroes']]
        for hero in dire:
            summary["dh-" + hero] = 1

        mongo_db.matches.insert_one(summary)


def process_matches(mongo_db, match_ids, hero, skill, executor):
    """Loop over all match_ids, parsing JSON output and writing
    to database.
    """
    log.debug("%d matches for processing", len(match_ids))
    match_ids = [m for m in match_ids if m not in MATCH_IDS.keys()]
    log.info("%d matches after removing duplicates.", len(match_ids))

    if NUM_THREADS == 1:
        matches = [process_match(hero, skill, match_id) for match_id in
                   match_ids]
    else:
        f_p = partial(process_match, hero, skill)
        matches = executor.map(f_p, match_ids, timeout=3600)

    matches = [m for m in matches if m is not None]

    if matches is not None:
        log.info("%d valid matches to write to database", len(matches))
        write_matches(mongo_db, matches)


def fetch_matches_loop(url, skill, start_at_match_id, hero):
    """Loop until we find matches. There is a bug in valve API with load
    balancing, sometimes the API returns no matches, so we'll re-try a few
    times if we expect more matches.
    """
    resp = {}
    for retry in range(20):
        resp = fetch_url(url.format(
            os.environ["STEAM_KEY"],
            skill,
            start_at_match_id,
            hero,
        ))

        log.error("num_results (try %d) %d", retry, resp['num_results'])

        # If we found results, break out of loop
        if resp['num_results'] > 0:
            break

        time.sleep(1)

    return resp


def fetch_matches(mongo_db, hero, skill, executor):
    """Gets list of matches by page. This is just the index, not the
    individual match results.
    """
    counter = 1
    start = time.time()
    start_at_match_id = 9999999999

    url = "https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/"
    url += "V001/?key={0}&skill={1}&start_at_match_id={2}&hero_id={3}"

    no_results_remain = False
    while not no_results_remain:
        log.info("Fetching more matches: %d", counter)

        resp = fetch_matches_loop(url, skill, start_at_match_id, hero)

        if resp['num_results'] > 0:
            match_ids = [t['match_id'] for t in resp['matches']]
            process_matches(mongo_db, match_ids, hero, skill, executor)
            start_at_match_id = min(match_ids) - 1

        # Set dictionary for start time so we don't fetch multiple times,
        # both in current cache as well as the database.
        matches = []
        start_times = []
        for match in resp['matches']:

            # Skip if already in database
            if not match['match_id'] in MATCH_IDS.keys():
                MATCH_IDS[match['match_id']] = match['start_time']
                matches.append(match['match_id'])
                start_times.append(match['start_time'])

        # Exit if no results remain
        if resp['results_remaining'] == 0:
            no_results_remain = True
        else:
            log.info("Remaining %d (Match ID %d)", resp['results_remaining'],
                     start_at_match_id)

        counter = counter + 1

    mpm = str(60 * counter / (time.time() - start))
    log.debug("Matches per minute: %s", mpm)


def parse_command_line():
    """Parse command line options."""

    parser = argparse.ArgumentParser(
        description='Fetch matches from DOTA 2 API web services.')
    parser.add_argument('hero', type=str, help='"all" or hero names')
    parser.add_argument('skill', type=int, help="skill = {1, 2, 3}")
    opts = parser.parse_args()

    # Parse heroes
    hero_name = opts.hero.lower()
    if hero_name == "all":
        heroes = list(meta.HERO_DICT.keys())
    else:
        valid_heroes = [v for k, v in meta.HERO_DICT.items()]
        if hero_name not in valid_heroes:
            parser.print_help()
            sys.exit(-1)
        else:
            heroes = [k for k, v in meta.HERO_DICT.items() if v == hero_name]

    if opts.skill not in [1, 2, 3]:
        parser.print_help()
        sys.exit(-1)

    return heroes, opts.skill


def main():
    """Main entry point. """

    # Parse command line
    heroes, skill = parse_command_line()

    # Mongo connection
    mongo_db = db_util.connect_mongo()

    # Populate dictionary with matches we already have within
    # INITIAL_HORIZON (don't refetch there)

    # Get UTC timestamps spanning HORIZON_DAYS ago to today
    start_time = int((dt.datetime.utcnow() - dt.timedelta(
        days=INITIAL_HORIZON)).timestamp())
    end_time = int(dt.datetime.utcnow().timestamp())

    key_begin = db_util.get_key(skill, start_time, 0)
    key_end = db_util.get_key(skill, end_time, 0)
    query = {'_id': {'$gte': key_begin, '$lte': key_end}}
    rows1 = mongo_db.matches.find(query)

    count = 0
    for row in rows1:
        MATCH_IDS[row['match_id']] = row['start_time']
        count += 1
    log.info("Records to seed MATCH_IDS: %d", count)

    # Main loop over heroes. Create the thread pool now to prevent constant
    # creation and destruction of threads. Also, destroy database connection
    # in between heroes just in case something hangs.
    executor = futures.ThreadPoolExecutor(max_workers=int(NUM_THREADS))
    counter = 1

    for hero in heroes:
        log.info("---------------------------------------------------------")
        log.info(">>>>>>>> Hero: %s %d/%d Skill: %d <<<<<<<<",
                 meta.HERO_DICT[hero], counter, len(heroes), skill)
        log.info("---------------------------------------------------------")
        fetch_matches(mongo_db, hero, skill, executor)
        counter += 1


if __name__ == "__main__":
    main()
