import sqlite3
import os
import meta
import pandas as pd
import numpy as np
import ast

SQL_STATS_TABLE=os.environ['DOTA_SQL_STATS_TABLE']

conn = sqlite3.connect('matches.db')
c = conn.cursor()
c.execute("SELECT match_id,radiant_heroes, dire_heroes, radiant_win FROM {}".format(SQL_STATS_TABLE))


# Setup indices for hero matrix, note this won't match hero number necessarily
heroes_lower={}
for k,v in meta.HERO_DICT.items():
    heroes_lower[k]=v.lower().replace(" ","_").replace("-","_")

total_matches=pd.DataFrame(np.zeros([len(heroes_lower),5]))
total_matches.index=list(heroes_lower.values())
total_matches.columns=["P1", "P2", "P3", "P4", "P5"]

total_wins=pd.DataFrame(np.zeros([len(heroes_lower),5]))
total_wins.index=list(heroes_lower.values())
total_wins.columns=["P1", "P2", "P3", "P4", "P5"]

rows=c.fetchall()
print("{0} matches found in database".format(len(rows)))

# Create blank dataframe for hero vectors
hero_matrix=pd.DataFrame(np.zeros([len(rows),len(heroes_lower.values())]))
hero_matrix.columns=sorted(heroes_lower.values())

counter=0
win_vector=[]
for match_id, radiant, dire, radiant_win  in rows:

    radiant=ast.literal_eval(radiant)
    dire=ast.literal_eval(dire)

    # Guard against wierd 4v5 situations
    if 0 not in radiant+dire:
        # Radiant loop
        for hero,position in zip(radiant,range(5)):
            pos="P{0}".format(position+1)
            hero_matrix.loc[hero_matrix.index==counter,heroes_lower[hero]]=1
            total_matches.loc[heroes_lower[hero],pos]=total_matches.loc[heroes_lower[hero],pos]+1
            if radiant_win==1:
                total_wins.loc[heroes_lower[hero],pos]=total_wins.loc[heroes_lower[hero],pos]+1
            

        for hero,position in zip(dire,range(5)):
            pos="P{0}".format(position+1)
            hero_matrix.loc[hero_matrix.index==counter,heroes_lower[hero]]=-1
            total_matches.loc[heroes_lower[hero],pos]=total_matches.loc[heroes_lower[hero],pos]+1
            if radiant_win==0:
                total_wins.loc[heroes_lower[hero],pos]=total_wins.loc[heroes_lower[hero],pos]+1

        if radiant_win:
            win_vector.append(100)
        else:
            win_vector.append(0)

        counter=counter+1
        print(".", end="")
        if counter>1000:
            break

    else:
        print("\nBad match ID {}\n".format(match_id))



# Unit tests:
# - total wins = matches / 10
# - set vectorization of hero matrix
# - sum(abs(hero_matrix.iloc[2,:])), sum(hero_matrix.iloc[2,:]) should be zero


import pdb
pdb.set_trace()
#summary=pd.concat([total_matches,total_wins, (total_wins/total_matches)], axis=1)
#summary.to_csv("summary_{0}.csv".format(dt.datetime.now().strftime("%Y%m%d%H")))

