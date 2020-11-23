"""Utility functions used by multiple scripts in the project. Includes methods
to seriaslize and de-serialize match details using protobuf as well as
functions to encode the heroes in a match into a bitmask for searching.
"""

import ujson as json
from match import match_pb

def protobuf_match_details(rad_heroes, dire_heroes, items, gold):
    """Serialize some match info to protobuf"""
    
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
    """Deserialize match information from protobuf"""
    
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


def encode_heroes_bitmask(heroes):
    """Returns a 3 BIGINT bitmask which encodes the heroes"""
    low_mask = 0
    mid_mask = 0
    high_mask = 0
    
    for hero_num in heroes:
        if hero_num>0 and hero_num<=63:
            low_mask=low_mask | 2**hero_num
        elif hero_num>63 and hero_num<=127:
            mid_mask=mid_mask | 2**(hero_num-64)
        elif hero_num>127 and hero_num<=191:
            high_mask=mid_mask | 2**(hero_num-128)
        else:
            raise ValueError("Hero out of range %d" % hero_num)

    return low_mask, mid_mask, high_mask


def where_bitmask(hero_num):
    """Returns SQL WHERE clause for a given hero"""
    
    if hero_num>0 and hero_num<=63:
        bitmask = 2**hero_num
        stmt = "WHERE hero_mask_low & {} = {}".format(bitmask, bitmask)
        
    elif hero_num>63 and hero_num<=127:
        bitmask = 2**(hero_num-64)
        stmt = "WHERE hero_mask_mid & {} = {}".format(bitmask, bitmask)
                
    elif hero_num>126 and hero_num<=191:
        bitmask = 2**(hero_num-128)
        stmt = "WHERE hero_mask_high & {} = {}".format(bitmask, bitmask)        
    else:
        raise ValueError("Hero out of range %d" % hero_num)

    return stmt


def decode_heroes_bitmask(bit_masks):
    """Returns list of heroes in match given a bitmask tuple/list"""
    
    low_mask, mid_mask, high_mask = bit_masks
    heroes = []
    for ibit in [t for t in range(64)]:
        if 2**ibit & low_mask == 2**ibit:
            heroes.append(ibit)
        if 2**ibit & mid_mask == 2**ibit:
            heroes.append(ibit+64)
        if 2**ibit & high_mask == 2**ibit:
            heroes.append(ibit+128)
            
    return heroes

