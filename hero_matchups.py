#!/usr/bin/env python
# coding: utf-8

"""
Hero Match-Ups

Use logistic regression to determine which heroes counter other heroes and 
which have synergy with other heroes.
"""

import sqlite3
import meta
import os
import ujson as json
import pandas as pd
import numpy as np
import hero_analysis
from sklearn.linear_model import LogisticRegression

HERO='juggernaut'
DB_FILES = ['matches_1_all_2020010710.db']

rows=[]
for db_file in DB_FILES:
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT match_id, radiant_heroes, dire_heroes, items, "\
            "gold_spent, radiant_win FROM {}".format(
        os.environ['DOTA_SQL_STATS_TABLE']))
    rows.extend(c.fetchall())
    conn.close()
    
print("{0} matches found in database".format(len(rows)))


enemy_list = []
ally_list = []
for match_id, radiant_heroes, dire_heroes, items, \
                        gold_spent, radiant_win in rows:
    a, b = hero_analysis.unpack_match(match_id, HERO, radiant_heroes, 
                                                dire_heroes, radiant_win)
    if not(a==[]):
        enemy_list.extend(a)
    if not(b==[]):
        ally_list.extend(b)


def regress_matchups(hero_list, enemy_flag):
    """Given a hero list of:
    
    match_ID, hero, radiant, other hero, win
    
    Perform a logistic regression. Enemy flag used to determine if
    logistic regression should be calculating enemy counters or
    hero synergies.
    
    """
    df=pd.DataFrame(hero_list)
    if enemy_flag==True:
        pivot_column="enemy_hero"
    else:
        pivot_column="ally_hero"
    df.columns=["match_id", "target_hero", "radiant_flag", pivot_column, "win"]
    df.to_csv("temp_{}_flat.csv".format(pivot_column))
    
    df['p1']=1
        
    df=df.pivot_table(index=['match_id', 'target_hero', 'radiant_flag', 'win'], 
                      columns=pivot_column, values='p1').fillna(0)
    df.reset_index(inplace=True)
    
    hero_columns=[t for t in df.columns if t not in ['match_id', 
        'target_hero', 'radiant_flag', 'win']]
    
    X1=np.array([int(t) for t in df['radiant_flag']]).reshape(-1,1)
    X2=df[hero_columns].values
    y=[int(t) for t in df['win']]        
    
    X=np.concatenate([X1, X2], axis=1)
    X_labels=["radiant"]+hero_columns
    
    lr=LogisticRegression()
    _ = lr.fit(X,y)
    
    results=pd.DataFrame({
    'variable' : X_labels,
    'coeff' : lr.coef_[0]})    
    return(results)


df_enemy = regress_matchups(enemy_list, True)
df_ally = regress_matchups(ally_list, True)


df_enemy=df_enemy.rename(columns={'variable' : 'enemy' , 
                                  'coeff' : 'enemy_coeff'}).\
                                  sort_values(by="enemy_coeff") 
df_ally=df_ally.rename(columns={'variable' : 'ally' , 
                                'coeff' : 'ally_coeff'}).\
                                sort_values(by="ally_coeff", ascending=False)
df_enemy.reset_index(inplace=True)
df_ally.reset_index(inplace=True)


counter=0
for idx, row in df_ally.join(df_enemy, lsuffix="l_", rsuffix="r_").iterrows():
    print("{0:20} {1:6.3f}   {2:20} {3:6.3f}".format(
            row.ally,
            row.ally_coeff,
            row.enemy,
            row.enemy_coeff))
    counter=counter+1
    if counter==30:
        break
