# -*- coding: utf-8 -*-
"""Database processing and hero matchups."""

import ujson as json
import meta

def unpack_match(match_id, hero, radiant_heroes, dire_heroes, radiant_win):
    """Return a list of tuples for a match givig both the
    enemy and ally match ups.

    Returns the following tuples for enemy match-ups:
    
        match ID | target_hero | radiant_flag | enemy_hero | win_flag
    
    And the following format for synergies with teammates:

        match ID | target_hero | radiant_flag | ally_hero | win_flag
        
    Only create this list for the "selected" ``hero`` otherwise we run 
    into memory issues.
    """

    counter_list = []
    ally_list = []
    hero=hero.lower().replace(" ","-")
    
    radiant_heroes=[meta.HERO_DICT[t] for t in json.loads(radiant_heroes)]
    dire_heroes=[meta.HERO_DICT[t] for t in json.loads(dire_heroes)]
    
    # Counters
    for rh in radiant_heroes:
        for dh in dire_heroes:

            # Add both the forward and reverse match-ups, just
            # flip the target and win status
            if (rh==hero): 
                counter_list.append((
                    match_id, rh, 
                    1, dh, int(radiant_win),
                    ))
                
            if (dh==hero):
                counter_list.append((
                    match_id, dh,
                    0, rh, int(not(radiant_win)),
                    ))
    
    # Allies
    if hero in radiant_heroes:
        for rh in radiant_heroes:
            if not(rh==hero):
                    ally_list.append((
                        match_id, hero, 
                        1, rh, int(radiant_win),
                        ))

    if hero in dire_heroes:
        for dh in dire_heroes:
            if not(dh==hero):
                    ally_list.append((
                        match_id, hero, 
                        0, dh, int(not(radiant_win)),
                        ))

    return(counter_list, ally_list)

