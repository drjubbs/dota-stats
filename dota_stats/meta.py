# -*- coding: utf-8 -*-
"""Metadata and enumerations used throughout the project."""

import os
import json

cwd = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(cwd, "game_mode.json"), "r") as gmj:
    MODE_ENUM = json.loads(gmj.read())

LOBBY_ENUM = {
    'INVALID': -1,
    'CASUAL_MATCH': 0,
    'PRACTICE': 1,
    'TOURNAMENT': 2,
    'COOP_BOT_MATCH': 4,
    'LEGACY_TEAM_MATCH': 5,
    'LEGACY_SOLO_QUEUE_MATCH': 6,
    'COMPETITIVE_MATCH': 7,
    'CASUAL_1V1_MATCH': 8,
    'BATTLE_CUP': 9,
    'MOROKAI_CUSTOM_GAME': 12,
    'TI10_GAUNTLET_?': 13
}

LEAVER = [
    {
        "id": "0",
        "name": "NONE",
        "description": "finished match, no abandon"
    },
    {
        "id": "1",
        "name": "DISCONNECTED",
        "description": "player DC, no abandon"
    },
    {
        "id": "2",
        "name": "DISCONNECTED_TOO_LONG",
        "description": "player DC > 5min, abandon"
    },
    {
        "id": "3",
        "name": "ABANDONED",
        "description": "player dc, clicked leave, abandon"
    },
    {
        "id": "4",
        "name": "AFK",
        "description": "player AFK, abandon"
    },
    {
        "id": "5",
        "name": "NEVER_CONNECTED",
        "description": "never connected, no abandon"
    },
    {
        "id": "6",
        "name": "NEVER_CONNECTED_TOO_LONG",
        "description": "too long to connect, no abandon"
    }
]

HERO_DICT = {
        1: 'anti-mage', 2: 'axe', 3: 'bane', 4: 'bloodseeker',
        5: 'crystal-maiden', 6: 'drow-ranger', 7: 'earthshaker',
        8: 'juggernaut', 9: 'mirana', 10: 'morphling',
        11: 'shadow-fiend', 12: 'phantom-lancer', 13: 'puck',
        14: 'pudge', 15: 'razor', 16: 'sand-king', 17: 'storm-spirit',
        18: 'sven', 19: 'tiny', 20: 'vengeful-spirit',
        21: 'windranger', 22: 'zeus', 23: 'kunkka', 25: 'lina',
        26: 'lion', 27: 'shadow-shaman', 28: 'slardar',
        29: 'tidehunter', 30: 'witch-doctor', 31: 'lich', 32: 'riki',
        33: 'enigma', 34: 'tinker', 35: 'sniper', 36: 'necrophos',
        37: 'warlock', 38: 'beastmaster', 39: 'queen-of-pain',
        40: 'venomancer', 41: 'faceless-void', 42: 'wraith-king',
        43: 'death-prophet', 44: 'phantom-assassin', 45: 'pugna',
        46: 'templar-assassin', 47: 'viper', 48: 'luna',
        49: 'dragon-knight', 50: 'dazzle', 51: 'clockwerk',
        52: 'leshrac', 53: "natures-prophet", 54: 'lifestealer',
        55: 'dark-seer', 56: 'clinkz', 57: 'omniknight',
        58: 'enchantress', 59: 'huskar', 60: 'night-stalker',
        61: 'broodmother', 62: 'bounty-hunter', 63: 'weaver',
        64: 'jakiro', 65: 'batrider', 66: 'chen', 67: 'spectre',
        68: 'ancient-apparition', 69: 'doom', 70: 'ursa',
        71: 'spirit-breaker', 72: 'gyrocopter', 73: 'alchemist',
        74: 'invoker', 75: 'silencer', 76: 'outworld-destroyer',
        77: 'lycan', 78: 'brewmaster', 79: 'shadow-demon',
        80: 'lone-druid', 81: 'chaos-knight', 82: 'meepo',
        83: 'treant-protector', 84: 'ogre-magi', 85: 'undying',
        86: 'rubick', 87: 'disruptor', 88: 'nyx-assassin',
        89: 'naga-siren', 90: 'keeper-of-the-light', 91: 'io',
        92: 'visage', 93: 'slark', 94: 'medusa', 95: 'troll-warlord',
        96: 'centaur-warrunner', 97: 'magnus', 98: 'timbersaw',
        99: 'bristleback', 100: 'tusk', 101: 'skywrath-mage',
        102: 'abaddon', 103: 'elder-titan', 104: 'legion-commander',
        105: 'techies', 106: 'ember-spirit', 107: 'earth-spirit',
        108: 'underlord', 109: 'terrorblade', 110: 'phoenix',
        111: 'oracle', 112: 'winter-wyvern', 113: 'arc-warden',
        114: 'monkey-king', 119: 'dark-willow', 120: 'pangolier',
        121: 'grimstroke', 123: 'hookwink', 126: 'void-spirit',
        128: 'snapfire', 129: 'mars', 135: 'dawnbreaker', 136: 'marci'}

REVERSE_HERO_DICT = {}
for k, v in HERO_DICT.items():
    REVERSE_HERO_DICT[v] = k

HEROES = list(HERO_DICT.keys())
NUM_HEROES = len(HEROES)

# Get items dictionary from OpenDota source:
#   https://github.com/odota/dotaconstants
with open(os.path.join(cwd, 'items.json')) as f:
    txt = f.read()
    ITEMS = json.loads(txt)

REVERSE_ITEM = {}
for k, v in ITEMS.items():
    REVERSE_ITEM[v['id']] = k
