"""
Utility functions and shared configuration between elements
"""
from boto3.dynamodb.conditions import Key, Attr
import logging
import sys

# No abandons, full games, normal and competitve lobbies, duration over 20 minutes
filter_leaver=Attr("calc_leaver").lt(2)
filter_mode=Attr("game_mode").ne(18)&Attr("game_mode").ne(20)&Attr("game_mode").ne(23)
filter_lobby=Attr("lobby_type").ne(-1)&Attr("lobby_type").ne(4)&Attr("lobby_type").ne(8)
filter_duration=Attr("duration").gt(1199)
FILTER_NORMAL=filter_leaver&(filter_mode)&(filter_lobby)&(filter_duration)

# All matches
FILTER_ALL=Attr("game_mode").gt(-999)

# Logging
log=logging.getLogger("dota")
log.setLevel(logging.DEBUG)
ch=logging.StreamHandler(sys.stdout)
fmt=logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                datefmt="%Y-%m-%dT%H:%M:%S %Z")
ch.setFormatter(fmt)

log.addHandler(ch)
