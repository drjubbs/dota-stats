# -*- coding: utf-8 -*-
"""Utility functions to manage the Mongo database and keys"""
import os
from pymongo import MongoClient


def connect_mongo():
    """Connect to MongoDB"""
    mongo = MongoClient(os.environ['DOTA_MONGO_URI'])
    return mongo[os.environ['DOTA_MONGO_DB']]


def get_key(skill, time, match):
    """Generate MongdoDB _id for skill/time/match trio"""
    return "{0:1d}_{1:010d}_{2:012d}".format(skill, time, match)


def get_max_start_time():
    """Return the most recent start time"""

    mongo_db = connect_mongo()
    try:
        matches = mongo_db.matches.find().sort("start_time", -1)
        last = matches[0]
    except IndexError:
        return 0

    return last['start_time']
