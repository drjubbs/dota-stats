"""Utility functions and shared configuration between elements
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

# Binary hero encoding (local DB mode)
def encode_heroes(hero_list):
    low_mask=0
    high_mask=0

    for t in [hero-1 for hero in hero_list]:
        if t<=63:
            low_mask=low_mask | 2**t
        else:
            t=t-63
            high_mask=high_mask | 2**t

    return(low_mask, high_mask)

def decode_heroes(low_mask, high_mask):

    hero_list=[]
    for i in range(64):
        if 2**i & low_mask:
            hero_list.append(i+1)

    for i in range(64):
        if 2**i & high_mask:
            hero_list.append(i+64)

    return(hero_list)

