# -*- coding: utf-8 -*-
import requests
import json
import bs4
import time
import random
import uuid
import pdb

MODE_ENUM = {
    1 : 'All Pick (old)',
    2 : 'Captains Mode',
    3 : 'Random Draft',
    4 : 'Single Draft',
    5 : 'All Random',
    12 : 'Least Played',
    16 : 'Captains Draft',
    18 : 'Ability Draft',
    19 : 'Custom Game',
    20 : 'All Random Deathmatch',
    21 : '1v1 Mid',
    22 : 'All Pick',
    23 : 'Turbo',
    24 : 'Mutation'
}

LOBBY_ENUM = {
	'INVALID' : -1,
	'CASUAL_MATCH' : 0,
	'PRACTICE' : 1,
	'TOURNAMENT' : 2,
	'COOP_BOT_MATCH' : 4,
	'LEGACY_TEAM_MATCH' : 5,
	'LEGACY_SOLO_QUEUE_MATCH' : 6,
	'COMPETITIVE_MATCH' : 7,
	'CASUAL_1V1_MATCH' : 8,
	'BATTLE_CUP' : 9,
        'MOROKAI_CUSTOM_GAME' : 12,
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

HERO_DICT={
 1: 'Anti-Mage',
 2: 'Axe',
 3: 'Bane',
 4: 'Bloodseeker',
 5: 'Crystal Maiden',
 6: 'Drow Ranger',
 7: 'Earthshaker',
 8: 'Juggernaut',
 9: 'Mirana',
 10: 'Morphling',
 11: 'Shadow Fiend',
 12: 'Phantom Lancer',
 13: 'Puck',
 14: 'Pudge',
 15: 'Razor',
 16: 'Sand King',
 17: 'Storm Spirit',
 18: 'Sven',
 19: 'Tiny',
 20: 'Vengeful Spirit',
 21: 'Windranger',
 22: 'Zeus',
 23: 'Kunkka',
 25: 'Lina',
 26: 'Lion',
 27: 'Shadow Shaman',
 28: 'Slardar',
 29: 'Tidehunter',
 30: 'Witch Doctor',
 31: 'Lich',
 32: 'Riki',
 33: 'Enigma',
 34: 'Tinker',
 35: 'Sniper',
 36: 'Necrophos',
 37: 'Warlock',
 38: 'Beastmaster',
 39: 'Queen of Pain',
 40: 'Venomancer',
 41: 'Faceless Void',
 42: 'Wraith King',
 43: 'Death Prophet',
 44: 'Phantom Assassin',
 45: 'Pugna',
 46: 'Templar Assassin',
 47: 'Viper',
 48: 'Luna',
 49: 'Dragon Knight',
 50: 'Dazzle',
 51: 'Clockwerk',
 52: 'Leshrac',
 53: "Nature's Prophet",
 54: 'Lifestealer',
 55: 'Dark Seer',
 56: 'Clinkz',
 57: 'Omniknight',
 58: 'Enchantress',
 59: 'Huskar',
 60: 'Night Stalker',
 61: 'Broodmother',
 62: 'Bounty Hunter',
 63: 'Weaver',
 64: 'Jakiro',
 65: 'Batrider',
 66: 'Chen',
 67: 'Spectre',
 68: 'Ancient Apparition',
 69: 'Doom',
 70: 'Ursa',
 71: 'Spirit Breaker',
 72: 'Gyrocopter',
 73: 'Alchemist',
 74: 'Invoker',
 75: 'Silencer',
 76: 'Outworld Devourer',
 77: 'Lycan',
 78: 'Brewmaster',
 79: 'Shadow Demon',
 80: 'Lone Druid',
 81: 'Chaos Knight',
 82: 'Meepo',
 83: 'Treant Protector',
 84: 'Ogre Magi',
 85: 'Undying',
 86: 'Rubick',
 87: 'Disruptor',
 88: 'Nyx Assassin',
 89: 'Naga Siren',
 90: 'Keeper of the Light',
 91: 'Io',
 92: 'Visage',
 93: 'Slark',
 94: 'Medusa',
 95: 'Troll Warlord',
 96: 'Centaur Warrunner',
 97: 'Magnus',
 98: 'Timbersaw',
 99: 'Bristleback',
 100: 'Tusk',
 101: 'Skywrath Mage',
 102: 'Abaddon',
 103: 'Elder Titan',
 104: 'Legion Commander',
 105: 'Techies',
 106: 'Ember Spirit',
 107: 'Earth Spirit',
 108: 'Underlord',
 109: 'Terrorblade',
 110: 'Phoenix',
 111: 'Oracle',
 112: 'Winter Wyvern',
 113: 'Arc Warden',
 114: 'Monkey King',
 119: 'Dark Willow',
 120: 'Pangolier',
 121: 'Grimstroke',
 129: 'Mars' }

# Updated meta data if run directly....
if __name__ == "__main__":
    #---------------------------------------------
    # Refresh item dictionary from dotabuff
    #---------------------------------------------
    updated_items={}
    for k,v in ITEMS.items():    
        time.sleep(random.randint(1000,2000)/1000)
        url="https://www.dotabuff.com/items/{0}".format(v['name'])
        rv=requests.get(url, headers={'User-agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.168 Safari/537.36)'})
        if rv.status_code==200:
            parsed=bs4.BeautifulSoup(rv.text,"lxml")
            div=parsed.find("div", attrs={'class' : 'tooltip-header'})
            fullname=div.find("div", attrs={'class' : 'name'})
            v['pretty']=fullname.text
            
            div=parsed.find("div", attrs={'class' : 'price'})
            price=div.find("span", attrs={'class' : 'value'})
            if price.text.upper()=="NO COST":
                value=0
            else:
                value=int(price.text.replace(",",""))
            print("{0:45s} {1:5d}".format(v['name'],value))
            v['value']=value            
            updated_items[int(k)]=v
        else:
            print(v['name'])
            v['pretty']="Unknown"
            v['value']=-1            
            updated_items[int(k)]=v
        
    with open("items_{0}.json".format(uuid.uuid4().hex),"w") as f:
        f.writelines(json.dumps(updated_items,indent=4))
        
