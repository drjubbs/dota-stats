# -*- coding: utf-8 -*-
"""Algorthm for win probability by farm position. Position is inferred from
a combination of actual gold farmed and a Bayesian like prior based on
actual laning percentages (from dotabuff.com) and a 0/1 mask which is 
manually constructed for each hero (e.g. witch doctor should never be
position 1).

First calculate probability of a role, assuming input heroes position equals
post game GPM. Then iterate and re-assign match by match, based on maximium 
likelihood, using first pass overall probabilty as prior.

The concept here is that several hero might either have a good or bad game
and therefore post-GPM is only a proxy for position. Also several heroes
work well in pretty much any position, so use the likely role of other
heroes to back all this out.

For each hero on a team, define:

    d_hl = 1 if hero `h` is in position `l`
    p_hl = probabilty of hero `h` in position `l` from first
           pass
    
    argmax = \Pi_h d_hl*p_hl
    d_hl 
"""
import sqlite3
import os
import meta
import pandas as pd
import numpy as np
import datetime as dt
import ast
import sys
import re
from itertools import permutations

DEBUG_MATCH=0
PRIOR_WEIGHT=5
SQL_STATS_TABLE=os.environ['DOTA_SQL_STATS_TABLE']

# Setup indices for hero matrix, note this won't match hero number necessarily
HEROES_LOWER={}
for k,v in meta.HERO_DICT.items():
    HEROES_LOWER[k]=v.lower().replace(" ","_").replace("-","_").replace("'","")


def process_rows(rows):
    """Process the SQLite 3 results, returns:

        total_matches - DataFrame, hero played by position
        total_wins - DataFrame, hero win by position
    """
    counter=0

    hero_played=[]  # (hero, position,1 ) tuple
    hero_wins=[]    # (hero, position, 1) tuple

    for match_id, radiant, dire, radiant_win in rows:

        radiant=ast.literal_eval(radiant)
        dire=ast.literal_eval(dire)

        # Total games
        for hero_pos in zip([HEROES_LOWER[t1] for t1 in radiant], 
                            ["P{}".format(t2+1) for t2 in range(5)],
                            5*[1]):
            hero_played.append(hero_pos)
            if radiant_win:
                hero_wins.append(hero_pos)

        for hero_pos in zip([HEROES_LOWER[t1] for t1 in dire], 
                            ["P{}".format(t2+1) for t2 in range(5)],
                            5*[1]):
            hero_played.append(hero_pos)
            if not(radiant_win):
                hero_wins.append(hero_pos)

        counter=counter+1
        if counter % 1000 == 0:
            print("Processing {} of {}".format(counter,len(rows)))

    df1=pd.DataFrame(data=hero_played, columns=["hero", "position", "i"]).groupby(["hero", "position"]).count()
    df1.reset_index(level=[0, 1], inplace=True)
    total_matches=df1.pivot(index="hero", columns="position", values="i").fillna(0)

    df2=pd.DataFrame(data=hero_wins, columns=["hero", "position", "i"]).groupby(["hero", "position"]).count()
    df2.reset_index(level=[0, 1], inplace=True)
    total_wins=df2.pivot(index="hero", columns="position", values="i").fillna(0)


    return(total_matches, total_wins)


def likelihood(heroes, prob_position):
    L=0
    for h,p in zip(heroes, ["P{}".format(t+1) for t in range(5)]):
        L=L+np.log(np.max([prob_position.loc[HEROES_LOWER[h],p], 1.0e-3]))
    return(L)

def assign_max_likelihood(match_id, heroes, prob_position):
    """For 5 heroes, re-arrange into maximum likelihood."""

    # Set current to max
    max_L=likelihood(heroes, prob_position)
    orig_L=max_L
    orig_ii=heroes
    max_ii=[0, 1, 2, 3, 4]

    for ii in permutations(range(5)):

        hero_test=[heroes[t] for t in ii]
        z=likelihood(hero_test, prob_position)
        if z>max_L:
            max_L=z
            max_ii=ii

    # Major change in probability, output for dianogstics
    if max_L-orig_L>4.0:
        print(match_id, (0,1,2,3,4), [HEROES_LOWER[heroes[t]] for t in (0,1,2,3,4)])
        print(match_id, max_ii, [HEROES_LOWER[heroes[t]] for t in max_ii])
        print("----------------------------------")

    try:
        return([heroes[t] for t in max_ii])
    except:
        import pdb
        pdb.set_trace()


def fix_positions(rows, prob_position):
    """Second pass, re-assigns hero position based on maximum
    likelihood.
    """

    max_L_rows=[]
    # Second pass, look at maximum likelihoods
    for match_id, radiant, dire, radiant_win in rows:

        radiant=ast.literal_eval(radiant)
        dire=ast.literal_eval(dire)

        radiant=assign_max_likelihood(match_id, radiant, prob_position)
        dire=assign_max_likelihood(match_id,  dire, prob_position)

        max_L_rows.append((
                match_id,
                str(radiant),
                str(dire),
                radiant_win))

    return(max_L_rows)


def usage():
    print("python process.py <filename>")
    sys.exit(1)


def process_database(filename):
    """Called for main entry point, read in database, process, rerank
    position, and write output.
    """

    conn = sqlite3.connect(sys.argv[1])
    c = conn.cursor()
    c.execute("SELECT match_id,radiant_heroes, dire_heroes, radiant_win FROM {}".format(SQL_STATS_TABLE))
    rows=c.fetchall()
    print("{0} matches found in database".format(len(rows)))

    m=re.match(u"matches_(\d+)_(\d+)\.db", sys.argv[1])
    if m is None:
        raise(ValueError("Bad filename for database"))

    f1name="wr_pass1_{}_{}.csv".format(m.group(1), m.group(2))
    f2name="wr_pass2_{}_{}.csv".format(m.group(1), m.group(2))

    # Process
    total_matches, total_wins = process_rows(rows)

    # Write out first pass to file
    wrp1=pd.concat([total_matches,total_wins, (total_wins/total_matches)], axis=1, sort=True)
    wrp1.to_csv(f1name)

    gold_position=total_matches.div(total_matches.sum(axis=1),axis=0).fillna(0)

    # Apply some constraints (manual input) and renormalize
    position_prior=pd.read_csv("position_prior.dat", index_col=0)
    prob_position=gold_position+PRIOR_WEIGHT*position_prior
    prob_position=prob_position.div(prob_position.sum(axis=1),axis=0)

    # Re-assignn
    new_rows = fix_positions(rows, prob_position)
 
    # Process #2
    total_matches, total_wins = process_rows(new_rows)

    # Write out first pass to file
    wrp2=pd.concat([total_matches,total_wins, (total_wins/total_matches)], axis=1, sort=True)
    wrp2.to_csv(f2name)

   

if __name__=="__main__":

    if not(len(sys.argv))==2:
        usage()
    if not(os.path.exists(sys.argv[1])):
        usage()

    process_database(sys.argv[1])

