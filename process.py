"""
Algorthm for win probability by farm position.

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
from itertools import permutations

SQL_STATS_TABLE=os.environ['DOTA_SQL_STATS_TABLE']
#DEBUG_MATCH=5022182446
DEBUG_MATCH=0

def process_rows(rows, heroes_lower):
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
        for hero_pos in zip([heroes_lower[t1] for t1 in radiant], 
                            ["P{}".format(t2+1) for t2 in range(5)],
                            5*[1]):
            hero_played.append(hero_pos)
            if radiant_win:
                hero_wins.append(hero_pos)

        for hero_pos in zip([heroes_lower[t1] for t1 in dire], 
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

    # Setup indices for hero matrix, note this won't match hero number necessarily
    heroes_lower={}
    for k,v in meta.HERO_DICT.items():
        heroes_lower[k]=v.lower().replace(" ","_").replace("-","_")


    # Process
    total_matches, total_wins = process_rows(rows, heroes_lower)

    # Write out first pass to file
    wrp1=pd.concat([total_matches,total_wins, (total_wins/total_matches)], axis=1, sort=True)
    wrp1.to_csv("wr_pass1_{0}.csv".format(dt.datetime.now().strftime("%Y%m%d%H")))


if __name__=="__main__":

    if not(len(sys.argv))==2:
        usage()
    if not(os.path.exists(sys.argv[1])):
        usage()

    process_database(sys.argv[1])


"""

prob_position=total_matches.div(total_matches.sum(axis=1),axis=0)

# Second pass, look at maximum likelihoods
for match_id, radiant, dire, radiant_win in rows:

    radiant=ast.literal_eval(radiant)
    dire=ast.literal_eval(dire)

    max_L=0
    for ii in permutations(range(5)):

        radiant_test=[radiant[t] for t in ii]

        z=1
        for h,p,w in zip(radiant_test,["P{}".format(t+1) for t in range(5)],WEIGHTS):
            z=w*z*(prob_position.loc[heroes_lower[h],p]+1.0e-5)
            if match_id==DEBUG_MATCH:

                print("{0} {1} {2:8.5f} {3}".format(
                    p,
                    heroes_lower[h],
                    prob_position.loc[heroes_lower[h],p],
                    z))
        
        if z>max_L:
            max_L=z
            max_ii=ii

        # Debug this match
        if match_id==DEBUG_MATCH:
            print("{0:7.5f} {1}\n\n".format(
                    z, [heroes_lower[t] for t in [radiant[j] for j in ii]]))
       
    # Debug this match
    if match_id==DEBUG_MATCH:
        print(match_id, max_ii, [heroes_lower[radiant[t]] for t in max_ii])
        print()
        import pdb
        pdb.set_trace()

    # If the initial probability table did not yield
    # max liklehood, we have a re-assignment...
    if not(max_ii==(0,1,2,3,4)):
        print(match_id, max_ii, [heroes_lower[radiant[t]] for t in max_ii])

"""
