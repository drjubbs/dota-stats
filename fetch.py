"""Dota Match Scraper

Fetches, parses, and puts matches in DynamoDB, keeping statistics in
local SQL database for web visualization.
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

#----------------------------------------------
# Globals
#----------------------------------------------
PAGES_PER_HERO=10
MIN_MATCH_LEN=1200
STEAM_KEY=os.environ['STEAM_KEY']
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

def fetch_url(url):
    """Simple wait loop around fetching to deal with things like network 
    outages, etc..."""

    SLEEP_SCHEDULE=[0.05,0.1,1.0,10,30,60,300,500,1000,2000,6000]
    fetched=False
    for sleep in SLEEP_SCHEDULE:
        time.sleep(sleep)

        rv=requests.get(url)
        if rv.status_code==200:
            r=json.loads(rv.text)['result']
            # Check to see if we have an error
            if 'error' in r:
                raise(ValueError("API returned error: {}".format(url)))
            else:
                return(json.loads(rv.text)['result'])
    
    raise(ValueError("Could not fetch: {}".format(url)))


def parse_match(match):
    """
    Input: match information in JSON format
    """
    match['batch_time']=int(dt.datetime.fromtimestamp(match['start_time']).strftime("%Y%m%d%H"))
    dt1=dt.datetime.utcfromtimestamp(match['start_time'])
            
    radiant_heroes=[]
    dire_heroes=[]
    
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
    if not(match['lobby_type'] in [0,2,7]):
        raise(ParseException("Lobby Type"))
            
    match['calc_leaver']=0
    players=copy.deepcopy(match["players"])
    
    # Bail if Missing players
    if {} in players:
        raise(ParseException("Min Players"))
            
    new_players=[]
    for p in players:

        if p['leaver_status']>match['calc_leaver']:
            match['calc_leaver']=p['leaver_status']                    
       
        player_slot=p['player_slot']

        if player_slot<=4:                
            radiant_heroes.append(p['hero_id'])                
        else:
            dire_heroes.append(p['hero_id'])

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

    if match['calc_leaver']>1:
        raise(ParseException("Leaver"))

    pb2_players = dota_pb2.players()
    pb2_players.players.extend(new_players)
    btxt=lzma.compress(pb2_players.SerializeToString())

    summary={
                'match_id' : match['match_id'],
                'start_time' : match['start_time'],
                'radiant_heroes' : radiant_heroes,
                'dire_heroes' : dire_heroes,
                'radiant_win' : match['radiant_win'], 
                'api_skill' : match['api_skill']
            }

    return(summary)


def process_matches(match_ids, hero, skill, conn):
    """Loop over all match_ids, parsing JSON output and writing 
    to database.
    """
    cursor=conn.cursor()

    for match_id in match_ids:
        txt="match ID {0} hero {1:3} skill {2}".format(match_id, hero, skill)

        if match_id in MATCH_IDS.keys():
            log.info("{0:20.20} {1}". format("Exists", txt))
        else:
            match=fetch_url("https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/?key={0}&match_id={1}".format(STEAM_KEY,match_id))
       
            # Skill level as defined by API
            match['api_skill']=skill
            
            # Set dictionary for start time so we don't fetch multiple times
            MATCH_IDS[match['match_id']]=match['start_time']

            try:
                summary=parse_match(match)
                cursor.execute('INSERT INTO '+SQL_STATS_TABLE+\
                        ' (match_id, start_time, radiant_heroes, dire_heroes, radiant_win, api_skill) VALUES (?,?,?,?,?,?)',(
                                summary['match_id'],
                                summary['start_time'],
                                str(summary['radiant_heroes']),
                                str(summary['dire_heroes']),
                                summary['radiant_win'],
                                summary['api_skill']))
                log.info("{0:20.20} {1}". format("Success", txt))
               
            except ParseException as e:
                log.info("{0:20.20} {1}". format(str(e), txt))
            except:
                log.error(json.dumps(match,indent=5))
                raise(ValueError("Failed on match_id: {}".format(match_id)))
    conn.commit()
    return(match_id)


def fetch_matches(hero, skill, conn):

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

if __name__=="__main__":

    SQL_STATS_FILE=os.environ['DOTA_SQL_STATS_FILE']
    SQL_STATS_TABLE=os.environ['DOTA_SQL_STATS_TABLE']

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
            " INTEGER, api_skill INTEGER);")
        conn.commit()
    
    heroes_random=list(meta.HERO_DICT.keys())
    idx=np.random.choice(range(len(heroes_random)),len(heroes_random),replace=False)
    heroes_random=[heroes_random[t] for t in idx]

    while True:
        for h in heroes_random:
            for s in [1,2,3]:
                log.info("Hero: {0}\t\tSkill: {1}".format(meta.HERO_DICT[h],s))
                fetch_matches(h,s,conn)
