"""Utility functions to serialize and de-serialize match details
using protobuf.
"""

import ujson as json
from match import match_pb

def protobuf_match_details(rad_heroes, dire_heroes, items, gold):
    
    item_dict=json.loads(items)
    gold_dict=json.loads(gold)
    
    rad_list=[]
    for rh in json.loads(rad_heroes):
        rad_list.append(match_pb.Hero(
            hero=rh,
            items=item_dict[str(rh)],
            gold_spent=gold_dict[str(rh)]
        ))

    dire_list=[]
    for dh in json.loads(dire_heroes):
        dire_list.append(match_pb.Hero(
            hero=dh,
            items=item_dict[str(dh)],
            gold_spent=gold_dict[str(dh)]
        ))

    match_info=match_pb.MatchInfo(
        radiant_heroes=rad_list,
        dire_heroes=dire_list,
    )
    
    return match_info
    
def unprotobuf_match_details(match_pb):
    
    radiant_heroes=[]
    dire_heroes=[]
    gold_spent={}
    items={}
    for rh in match_pb.radiant_heroes:
        radiant_heroes.append(rh.hero)
        gold_spent[str(rh.hero)]=rh.gold_spent
        items[str(rh.hero)]=[t for t in rh.items]

    for dh in match_pb.dire_heroes:
        dire_heroes.append(dh.hero)
        gold_spent[str(dh.hero)]=dh.gold_spent
        items[str(dh.hero)]=[t for t in dh.items]
        
    return (json.dumps(radiant_heroes),
            json.dumps(dire_heroes),
            json.dumps(items),
            json.dumps(gold_spent))