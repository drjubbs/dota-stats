"""Dota Match Scraper

Fetches, parses, and puts matches in DynamoDB, keeping statistics in
local SQL database for web visualization.

TODO:
    Lone Druid items not accounted for properly (bear/hero)

"""
import time
import requests
import simplejson as json
import datetime as dt
import meta
import copy
import pandas as pd
import util
import time
import lzma
import numpy as np
import logging
import os
import sys
import sqlite3
from dota_pb import dota_pb2
from multiprocessing import Pool
from functools import partial
import urllib
from urllib.request import Request


#----------------------------------------------
# Globals
#----------------------------------------------
NUM_THREADS=16    # Set to 1 for single threaded execution
PAGES_PER_HERO=10
MIN_MATCH_LEN=1200
STEAM_KEY=os.environ['STEAM_KEY']
MATCH_IDS = {}
MISSING_HEROES = {}

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

#----------------------------------------------
# Logging
#----------------------------------------------
log=logging.getLogger("dota")
log.setLevel(logging.DEBUG)
ch=logging.StreamHandler(sys.stdout)
fmt=logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        datefmt="%Y-%m-%dT%H:%M:%S %Z")
ch.setFormatter(fmt)
log.addHandler(ch)

class ParseException(Exception):
    pass

class APIException(Exception):
    pass


def fetch_url(url):
    """Simple wait loop around fetching to deal with things like network 
    outages, etc..."""

    SLEEP_SCHEDULE=[0.0,0.1,1.0,10,30,60,300,500,1000,2000]
    fetched=False
    for sleep in SLEEP_SCHEDULE:
        time.sleep(sleep)

        try:
            req=Request(url, headers={
                'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X '\
                               '10_15_6) AppleWebKit/537.36 (KHTML, like '\
                               'Gecko) Chrome/85.0.4183.83 Safari/537.36',
                'Accept' : 'gzip',
                'Content-Encoding' : 'gzip',
                'Content-Type' : 'application/json',
                }) 
            
            r2=urllib.request.urlopen(req)
            if r2.code==200:
                txt=r2.read()
                r=json.loads(txt)
                if 'error' in r:
                    if r['error']=='Match ID not found':
                        raise(APIException("Match ID not found"))
                    else:
                        raise(APIException(r['error']))
                else:
                    return(r['result'])
        except:
                pass

    raise(ValueError("Could not fetch: {}".format(url)))


def parse_match(match):
    """
    Input: match information in JSON format
    """
    match['batch_time']=int(dt.datetime.fromtimestamp(match['start_time']).strftime("%Y%m%d%H"))
    dt1=dt.datetime.utcfromtimestamp(match['start_time'])
            
    radiant_heroes=[]
    radiant_gpm=[]
    dire_heroes=[]
    dire_gpm=[]
    
    # Bad game mode
    if not(meta.MODE_ENUM[match['game_mode']] in
        ["All Pick", "Captains Mode", "Random Draft", "Single Draft", "All Random", "Least Played"]):
        raise(ParseException("Bad Game Mode"))
               
    # Bail if zero length matches
    if (match['duration']<MIN_MATCH_LEN):
        raise(ParseException("Min Length"))
  
    # Lobby types
    if not(match['lobby_type'] in meta.LOBBY_ENUM.values()):
        raise(ValueError("Unknown lobby type: {}".format(match['match_id'])))
    if not(match['lobby_type'] in [0,2,7,9,13]):
        raise(ParseException("Lobby Type"))
            
    match['calc_leaver']=0

    # Is deepcopy necessary? Not think so but leave this here if a bug turns up
    #players=copy.deepcopy(match["players"])
    players=match["players"]
    
    # Bail if Missing players
    if {} in players:
        raise(ParseException("Min Players"))
            
    new_players=[]
    items_dict = {}
    gold_spent = {}

    for p in players:

        if p['leaver_status']>match['calc_leaver']:
            match['calc_leaver']=p['leaver_status']                    
       
        player_slot=p['player_slot']

        # Check to see if we're missing a hero ID
        if p['hero_id'] not in meta.HERO_DICT.keys():
            MISSING_HEROES[p['hero_id']]=match['match_id']

        # Check for intentional feeding
        if p['deaths']>30 and p['kills']<5:
            raise(ParseException("Feeding"))

        if player_slot<=4:                
            radiant_heroes.append(p['hero_id'])
            radiant_gpm.append(p['gold_per_min'])
        else:
            dire_heroes.append(p['hero_id'])
            dire_gpm.append(p['gold_per_min'])

        # Net worth
        gold_spent[p['hero_id']] = p['gold_spent']

        # Get active items on hero
        items = []
        item_fields = [t for t in p.keys() if t[0:4]=='item']
        for field in item_fields:
            items.append(p[field])

        # No/destroyed items
        if set(items) == set([0]):
            raise(ParseException("No items"))

        bp_fields = [t for t in p.keys() if t[0:8]=='backpack']
        for field in bp_fields:
            items.append(p[field])

        items_dict[p['hero_id']]=items

        pb2_player=dota_pb2.player()
        for t in PLAYER_FIELDS:
            setattr(pb2_player,t,p[t])
            p.pop(t)
        ability_pb_list=[]
        if 'ability_upgrades' in p:
            for ability in p.pop('ability_upgrades'):
                a=dota_pb2.ability()
                a.ability=ability['ability']
                a.time=ability['time']
                a.level=ability['level']
                ability_pb_list.append(a)
            pb2_player.ability_upgrades.extend(ability_pb_list)

        # Arc warden, Lone Druid...
        if "additional_units" in p:
            add_units=p.pop('additional_units')
            new_units = []
            for unit in add_units:
                au=dota_pb2.additional_unit()
                au.unitname=unit['unitname']
                for idx in range(6):
                    label="item_{0}".format(idx)
                    setattr(au,label,unit[label])
                for idx in range(3):
                    label="backpack_{0}".format(idx)
                    setattr(au,label,unit[label])
                new_units.append(au)
            pb2_player.additional_units.extend(new_units)                
        
        new_players.append(pb2_player)

    if 0 in [t.hero_id for t in new_players]:
        raise(ParseException("hero_id=0 in players"))

    if match['calc_leaver']>1:
        raise(ParseException("Leaver"))

    pb2_players = dota_pb2.players()
    pb2_players.players.extend(new_players)
    #btxt=lzma.compress(pb2_players.SerializeToString())

    # Sort heroes by farm priority
    radiant_heroes=[x for _,x in sorted(zip(radiant_gpm,radiant_heroes),reverse=True)]
    dire_heroes=[x for _,x in sorted(zip(dire_gpm,dire_heroes),reverse=True)]

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

    return(summary)

def fetch_match(match_id,skill):
    """Skill is optional, this simply sets an object in the json
    for reference"""

    match=fetch_url("https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/?key={0}&match_id={1}".format(STEAM_KEY,match_id))
    match['api_skill']=skill


    return(match)

def process_match(hero, skill, match_id):
    """Process a single match, used by the multi-threading engine."""

    txt="match ID {0} hero {1:3} skill {2}".format(match_id, hero, skill)

    try:
        match=fetch_match(match_id, skill)
    except APIException as e:
        log.error("{0:20.20} {1}". format("API Error", str(e)))

    try:
        summary=parse_match(match)
        log.info("{0:20.20} {1}". format("Success", txt))
        return(summary)
    except ParseException as e:
        log.info("{0:20.20} {1}". format(str(e), txt))
        return(None)
    except:
        log.error(json.dumps(match,indent=5))
        log.error("{0}". format(str(e)))
        raise(ValueError("Failed on match_id: {}".format(match_id)))

def process_matches(match_ids, hero, skill, conn):
    """Loop over all match_ids, parsing JSON output and writing 
    to database.
    """
    cursor=conn.cursor()
    log.info("{0} matches for processing".format(len(match_ids)))
    match_ids=[m for m in match_ids if m not in MATCH_IDS.keys()]
    log.info("{0} matches after removing duplicates.".format(
                                                    len(match_ids)))

    if NUM_THREADS==1:
        matches=[process_match(hero,skill,match_id) for \
                    match_id in match_ids]
    else:
        f=partial(process_match,hero,skill)
        with Pool(NUM_THREADS) as p:
            matches=p.map(f, match_ids)

    matches=[m for m in matches if m is not None]
    log.info("{0} valid matches to write to database".format(len(matches)))

    for summary in matches:

        # Set dictionary for start time so we don't fetch multiple times
        MATCH_IDS[summary['match_id']]=summary['start_time']

        cursor.execute('INSERT INTO '+SQL_STATS_TABLE+\
                ' (match_id, start_time, radiant_heroes, dire_heroes, radiant_win, api_skill, items, gold_spent) VALUES (?,?,?,?,?,?,?,?)',(
                        summary['match_id'],
                        summary['start_time'],
                        str(summary['radiant_heroes']),
                        str(summary['dire_heroes']),
                        summary['radiant_win'],
                        summary['api_skill'],
                        summary['items'], summary['gold_spent']))
    conn.commit()
    
    # Return the lowest match id for the next page
    try:
        return(min(match_ids))
    except:
        return(0)


def fetch_matches(hero, skill, conn):
    """Gets list of matches by page. This is just the index, not the 
    individual match results.
    """
    counter=1
    start=time.time()
    start_at_match_id=9999999999
    while(counter<=PAGES_PER_HERO):
        log.info("Fetching more matches: {} of {}".format(
                                            counter,PAGES_PER_HERO))
        url="https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/V001/?key={0}&skill={1}&start_at_match_id={2}&hero_id={3}".format(STEAM_KEY,skill,start_at_match_id,hero)
        rv=requests.get(url)
        log.info("Done fetching more matches....")
        if rv.status_code==200:
            j=json.loads(rv.text)['result']        
            if j['num_results']>0:
                match_ids=[t['match_id'] for t in j['matches']]
                start_at_match_id=process_matches(match_ids, hero, skill, conn)
            counter=counter+1
        else:
            print("Bad return code")

    print("Matches per minute: {0}".format(60*counter/(time.time()-start)))

def usage():
    txt="""
python fetch.py <[hero name]|all> <skill level>
    """
    print(txt)
    sys.exit(1)

if __name__=="__main__":

    # Check command line arguments and setup hero list and
    # skill level
    if len(sys.argv)<3:
        usage()

    hero_name=sys.argv[1].lower()
    if hero_name=="all":
        heroes=list(meta.HERO_DICT.keys())
    else:
        valid_heroes=[v for k,v in meta.HERO_DICT.items()]
        if not t in valid_heroes:
            usage()
        else:
            heroes=[k for k,v in meta.HERO_DICT.items() if v==hero_name]

    t=sys.argv[2].lower()
    if t in ["1", "2", "3"]:
        skill = int(t)
    else:
        usage()

    # Setup filename
    SQL_STATS_FILE="matches_{0}_{1}_{2}.db".format(
            skill,
            hero_name,
            dt.datetime.now().strftime("%Y%m%d%H"))

    # Setup database
    SQL_STATS_TABLE="dota_stats"

    conn=sqlite3.connect(SQL_STATS_FILE)
    c = conn.cursor() 

    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables=c.fetchall()
    tables=[t[0] for t in tables]

    if not(SQL_STATS_TABLE in tables):
        # Parameter substituion not allowed on CREATE TABLE, this is dumb...
        log.info("Create new SQLITE summary stats table")
        c.execute("CREATE TABLE "+SQL_STATS_TABLE+
            "(match_id INTEGER PRIMARY KEY, start_time INTEGER, "\
            "radiant_heroes STRING, dire_heroes STRING, radiant_win"\
            " INTEGER, api_skill INTEGER, items STRING, gold_spent STRING);")
        conn.commit()
    conn.close()
   
    conn=sqlite3.connect(SQL_STATS_FILE)
    counter=1
    for h in heroes:
        log.info("Hero: {0} {1}/{2} Skill: {3}".format(
                    meta.HERO_DICT[h],
                    counter,
                    len(heroes),
                    skill))
        fetch_matches(h,skill,conn)
        counter=counter+1

    conn.commit()
    conn.close()

    print("-------------------------------------------------------------")
    print("Missing Heroes: ")
    print(MISSING_HEROES)
    print("-------------------------------------------------------------")
