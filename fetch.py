#!/usr/bin/env python3
# coding: utf-8
"""fetch.py

Fetches, parses, and puts matches into MariaDB using steam API. This script
is usually run using `crontab` and `flock` on a regular basis.
"""
import time
import logging
import os
import sys
import ssl
from urllib import request, error
from functools import partial
from concurrent import futures
from concurrent.futures import TimeoutError
import http.client
import datetime as dt
import numpy as np
import mariadb
import simplejson as json
import meta

#----------------------------------------------
# Globals
#----------------------------------------------
NUM_THREADS=8    # Set to 1 for single threaded execution
PAGES_PER_HERO=10
MIN_MATCH_LEN=1200
INITIAL_HORIZON=1    # Days to load from database on start-up
CTX=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

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

# Logging
log=logging.getLogger("dota")
if int(os.environ['DOTA_LOGGING'])==0:
    log.setLevel(logging.INFO)
else:
    log.setLevel(logging.DEBUG)
ch=logging.StreamHandler(sys.stdout)
fmt=logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%S %Z")
ch.setFormatter(fmt)
log.addHandler(ch)

class ParseException(Exception):
    """Used to indicate a parse error in the JSON from Valve API"""


class APIException(Exception):
    """Used to indicate an error fetching from the Valve API"""


def fetch_url(url):
    """Simple wait loop around fetching to deal with things like network
    outages, etc..."""

    sleep_schedule=[0.25,1.0,2,10,30,60,300,500,1000,1000]
    for sleep in sleep_schedule:
        time.sleep(np.random.uniform(0.3*sleep,0.7*sleep))
        req=request.Request(url, headers={
            'Accept' : 'gzip',
            'Content-Encoding' : 'gzip',
            'Content-Type' : 'application/json',
            })

        try:
            resp=request.urlopen(req,context=CTX)
            if resp.code==200:
                txt=resp.read()
                resp_json=json.loads(txt)
                if 'error' in resp_json:
                    print("*** ",url)
                    raise APIException("Match ID not found")
                return resp_json['result']

        # Catch exceptions, sleep a little, and re-try until
        # our sleep schedule is exhausted.
        except error.HTTPError as http_e:
            log.error("error.HTTPError  %s", http_e.msg)
            time.sleep(np.random.uniform(0.5,1.5))

        except error.URLError as url_e:
            log.error("error.URLError  %s", url_e.reason)
            time.sleep(np.random.uniform(0.5,1.5))

        except http.client.RemoteDisconnected as http_e:
            log.error("http.client.RemoteDisconnected  %s", str(http_e))

    raise ValueError("Could not fetch (timeout?): {}".format(url))

def parse_players(match_id, players):
    """Parse the players section of the JSON response."""

    radiant_heroes=[]
    radiant_gpm=[]
    dire_heroes=[]
    dire_gpm=[]
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

        if player['leaver_status']>1:
            leaver=True

        player_slot=player['player_slot']

        # Check to see if we're missing a hero ID
        if player['hero_id'] not in meta.HERO_DICT.keys():

            if player['hero_id']==0:
                raise ParseException("Null Hero ID")
            raise ValueError("Missing hero: {}".format(match_id))

        # Check for intentional feeding
        if player['deaths']>30 and player['kills']<5:
            raise ParseException("Feeding")

        if player_slot<=4:
            radiant_heroes.append(player['hero_id'])
            radiant_gpm.append(player['gold_per_min'])
        else:
            dire_heroes.append(player['hero_id'])
            dire_gpm.append(player['gold_per_min'])

        # Net worth
        gold_spent[player['hero_id']] = player['gold_spent']

        # Get active items on hero
        items = []
        item_fields = [t for t in player.keys() if t[0:4]=='item']
        for field in item_fields:
            items.append(player[field])

        # No/destroyed items
        if set(items) == set([0]):
            raise ParseException("No items")

        bp_fields = [t for t in player.keys() if t[0:8]=='backpack']
        for field in bp_fields:
            items.append(player[field])

        items_dict[player['hero_id']]=items

        # Sort heroes by farm -- probably not correct but good first pass
        radiant_heroes=[x for _,x in \
                sorted(zip(radiant_gpm,radiant_heroes),reverse=True)]
        dire_heroes=[x for _,x in \
                sorted(zip(dire_gpm,dire_heroes),reverse=True)]

    return leaver, radiant_heroes, dire_heroes, items_dict, gold_spent


def parse_match(match):
    """Parse match info from main API endpoint. Player section is broken
    out into a separate subroutine for clarity.
    """
    match['batch_time']=int(dt.datetime.fromtimestamp(\
                                match['start_time']).strftime("%Y%m%d_%H%M"))

    # Bad game mode
    if not(meta.MODE_ENUM[match['game_mode']] in
        ["All Pick", "Captains Mode", "Random Draft",
            "Single Draft", "All Random", "Least Played"]):
        raise ParseException("Bad Game Mode")

    # Bail if zero length matches
    if match['duration']<MIN_MATCH_LEN:
        raise ParseException("Min Length")

    # Lobby types
    if not match['lobby_type'] in meta.LOBBY_ENUM.values():
        raise ValueError("Unknown lobby type: {}".format(match['match_id']))
    if not(match['lobby_type'] in [0,2,7,9,13]):
        raise ParseException("Lobby Type")

    players=match["players"]

    # Bail if Missing players
    if {} in players:
        raise ParseException("Min Players")

    leaver, radiant_heroes, dire_heroes, items_dict, gold_spent =\
        parse_players(match['match_id'],players)

    if leaver:
        raise ParseException("Leaver")

    summary={
                'match_id' : match['match_id'],
                'start_time' : match['start_time'],
                'radiant_heroes' : radiant_heroes,
                'dire_heroes' : dire_heroes,
                'radiant_win' : match['radiant_win'],
                'api_skill' : match['api_skill'],
                'items' : json.dumps(items_dict),
                'gold_spent' : json.dumps(gold_spent),
            }

    return summary


def fetch_match(match_id,skill):
    """Skill is optional, this simply sets an object in the json
    for reference"""

    url = "https://api.steampowered.com/IDOTA2Match_570/"
    url += "GetMatchDetails/V001/?key={0}&match_id={1}"
    
    for i in range(10):
        match=fetch_url(url.format(os.environ['STEAM_KEY'],match_id))
        if 'start_time' in match.keys():
            break
        log.error("Match ID not found: %s", str(match_id))
        time.sleep(1)

    match['api_skill']=skill

    # If something went wrong, log to file and return no match
    if not 'start_time' in match.keys():
        if not os.path.exists('error'):
            os.makedirs('error')
        with open("./error/{}.json".format(match_id), "w") as f:
            f.write(json.dumps(match))
        raise APIException("Bad match JSON {}".format(match_id))

    return match

def process_match(hero, skill, match_id):
    """Process a single match, used by the multi-threading engine."""

    txt="match ID {0} hero {1:3} skill {2}".format(match_id, hero, skill)

    try:
        match=fetch_match(match_id, skill)
    except APIException as e_msg:
        log.error("{0:20.20} {1}". format("API Error", str(e_msg)))
        return None
    except TimeoutError as e_msg:
        log.error("{0:20.20} {1}". format("TimeoutError", str(e_msg)))
        return None
    try:
        summary=parse_match(match)
        log.debug("{0:20.20} {1}". format("Success", txt))
        return summary
    except ParseException as e_msg:
        log.debug("{0:20.20} {1}". format(str(e_msg), txt))
        return None
    return None


def process_matches(match_ids, hero, skill, conn, executor):
    """Loop over all match_ids, parsing JSON output and writing
    to database.
    """
    cursor=conn.cursor()
    log.debug("%d matches for processing", len(match_ids))
    match_ids=[m for m in match_ids if m not in MATCH_IDS.keys()]
    log.info("%d matches after removing duplicates.", len(match_ids))

    if NUM_THREADS==1:
        matches=[process_match(hero,skill,match_id) for \
                    match_id in match_ids]
    else:
        f_p=partial(process_match,hero,skill)
        matches=executor.map(f_p, match_ids, timeout=3600)

    matches=[m for m in matches if m is not None]
    log.info("%d valid matches to write to database",len(matches))

    for summary in matches:
        stmt = 'INSERT IGNORE INTO dota_matches '
        stmt += '(match_id, start_time, radiant_heroes, dire_heroes, '
        stmt += 'radiant_win, api_skill, items, gold_spent) '
        stmt += 'VALUES (?,?,?,?,?,?,?,?)'

        cursor.execute(stmt,
                       (summary['match_id'],
                        summary['start_time'],
                        str(summary['radiant_heroes']),
                        str(summary['dire_heroes']),
                        summary['radiant_win'],
                        summary['api_skill'],
                        summary['items'],
                        summary['gold_spent'])
                       )
    conn.commit()


def fetch_matches(hero, skill, conn, executor):
    """Gets list of matches by page. This is just the index, not the
    individual match results.
    """
    counter=1
    start=time.time()
    start_at_match_id=9999999999

    url="https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/"
    url+="V001/?key={0}&skill={1}&start_at_match_id={2}&hero_id={3}"

    no_results_remain = False
    while not no_results_remain:
        log.info("Fetching more matches: %d of %d", counter, PAGES_PER_HERO)

        # There is a bug in valve API with load balancing, sometimes
        # the API returns no matches, so we'll re-try a few times
        # if we expect more matches.
        retry=0
        while retry<20:
            resp=fetch_url(url.format(
                os.environ["STEAM_KEY"],
                skill,
                start_at_match_id,
                hero,
                ))

            log.error("num_results (try %d) %d", retry, resp['num_results'])

            # If we found results, break out of loop
            if resp['num_results']>0:
                break

            time.sleep(1)
            retry=retry+1

        if resp['num_results']>0:
            match_ids=[t['match_id'] for t in resp['matches']]
            process_matches(match_ids, hero, skill, conn, executor)
            start_at_match_id=min(match_ids)-1

        # Set dictionary for start time so we don't fetch multiple times,
        # both in current cache as well as the database.
        matches=[]
        start_times=[]
        for match in resp['matches']:
            MATCH_IDS[match['match_id']]=match['start_time']
            matches.append(match['match_id'])
            start_times.append(match['start_time'])

        if len(matches)>1:
            stmt="INSERT IGNORE INTO fetch_history VALUES(?,?)"
            cursor=conn.cursor()
            cursor.executemany(stmt, [t for t in zip(matches,start_times)])
            conn.commit()

        # Exit if no results remain
        if resp['results_remaining']==0:
            no_results_remain=True
        else:
            log.info("Remaining %d (Match ID %d)",
                        resp['results_remaining'],
                        start_at_match_id)

        counter=counter+1

    log.debug("Matches per minute: {0}".format(60*counter/(time.time()-start)))

def usage():
    """Display usage information."""

    txt="python fetch.py [hero name]|all skill={1,2,3}"
    print(txt)
    sys.exit(1)

def get_database_connection():
    conn = mariadb.connect(
        user=os.environ['DOTA_USERNAME'],
        password=os.environ['DOTA_PASSWORD'],
        host=os.environ['DOTA_HOSTNAME'],
        database=os.environ['DOTA_DATABASE'])

    return conn


def main():
    """Main entry point. """
    if len(sys.argv)<3:
        usage()

    hero_name=sys.argv[1].lower()
    if hero_name=="all":
        heroes=list(meta.HERO_DICT.keys())
    else:
        valid_heroes=[v for k,v in meta.HERO_DICT.items()]
        if not hero_name in valid_heroes:
            usage()
        else:
            heroes=[k for k,v in meta.HERO_DICT.items() if v==hero_name]

    skill=sys.argv[2].lower()
    if skill in ["1", "2", "3"]:
        skill = int(skill)
    else:
        usage()

    conn=get_database_connection()
    cursor=conn.cursor()

    # Populate dictionary with matches we already have within
    # INITIAL_HORIZON (don't refetch there)

    # Get UTC timestamps spanning HORIZON_DAYS ago to today
    start_time=int((dt.datetime.utcnow()-dt.timedelta(days=INITIAL_HORIZON)).timestamp())
    end_time=int(dt.datetime.utcnow().timestamp())

    stmt="SELECT match_id, start_time "
    stmt+="FROM fetch_history WHERE start_time>={0} and start_time<={1};"
    stmt=stmt.format(start_time, end_time)
    log.info(stmt)

    cursor.execute(stmt)
    rows=cursor.fetchall()
    print("Records to seed MATCH_IDS: {}".format(len(rows)))

    for row in rows:
        MATCH_IDS[row[0]]=row[1]
    conn.close()

    # Main loop over heroes.
    # Create the thread pool now to prevent constant creation
    # and destruction of threads. Also, destroy database connection
    # in between heroes just in case something hangs.
    executor=futures.ThreadPoolExecutor(max_workers=NUM_THREADS)
    counter=1

    for hero in heroes:
        conn=get_database_connection()
        log.info("Hero: %s %d/%d Skill: %d",
                    meta.HERO_DICT[hero],
                    counter,
                    len(heroes),
                    skill)
        fetch_matches(hero,skill,conn,executor)
        counter=counter+1

        conn.commit()
        conn.close()

if __name__=="__main__":
    main()
