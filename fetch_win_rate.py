# -*- coding: utf-8 -*-
"""Calculate summary win rate statistcs for each hero, radiant vs. dire. This 
should be automated in a cron job.
"""
import mariadb
import os
import meta
import sys
import pandas as pd
import datetime as dt
import json


def parse_records(rows):
    """Create summary table as a pandas DataFrame"""
    
    summary={
        'radiant_win' : [],
        'radiant_total' : [],
        'dire_win' : [],
        'dire_total' : [],
    }
    counter=0
    
    for row in rows:
        if counter % 10000 == 0:
            print("{} of {}".format(counter,len(rows)))

        rhs=json.loads(row[2])
        dhs=json.loads(row[3])

        for hero in rhs:
            summary['radiant_total'].append(meta.HERO_DICT[hero])
            if row[4]==1:
                summary['radiant_win'].append(meta.HERO_DICT[hero])
        for hero in dhs:
            summary['dire_total'].append(meta.HERO_DICT[hero])
            if row[4]==0:
                summary['dire_win'].append(meta.HERO_DICT[hero])

        counter=counter+1
    
    # Radiant Summary
    df_radiant_win=pd.DataFrame(summary['radiant_win'], columns=['hero'])
    df_radiant_win['radiant_win']=1
    df_radiant_win=df_radiant_win.groupby("hero").count()
    df_radiant_total=pd.DataFrame(summary['radiant_total'], columns=['hero'])
    df_radiant_total['radiant_total']=1
    df_radiant_total=df_radiant_total.groupby("hero").count()
    df1=df_radiant_win.join(df_radiant_total, how='outer').fillna(0)
    df1['radiant_win_pct']=100.0*df1['radiant_win']/df1['radiant_total']

    # Dire Summary
    df_dire_win=pd.DataFrame(summary['dire_win'], columns=['hero'])
    df_dire_win['dire_win']=1
    df_dire_win=df_dire_win.groupby("hero").count()
    df_dire_total=pd.DataFrame(summary['dire_total'], columns=['hero'])
    df_dire_total['dire_total']=1
    df_dire_total=df_dire_total.groupby("hero").count()
    df2=df_dire_win.join(df_dire_total, how='outer').fillna(0)
    df2['dire_win_pct']=100.0*df2['dire_win']/df2['dire_total']

    df_hero=df1.join(df2, how='outer').fillna(0)
    df_hero['win']=df_hero['radiant_win']+df_hero['dire_win']
    df_hero['total']=df_hero['radiant_total']+df_hero['dire_total']
    df_hero['win_pct']=100.0*df_hero['win']/df_hero['total']

    # Integrity checks
    if not(int(df_hero.sum()['radiant_total'])==len(rows*5)):
        raise(ValueError("Data integrity check fail"))
    if not(int(df_hero.sum()['dire_total'])==len(rows*5)):
        raise(ValueError("Data integrity check fail"))    
    if not(int(df_hero.sum()['radiant_win'])+int(df_hero.sum()['dire_win'])==len(rows*5)):
        raise(ValueError("Data integrity check fail"))
    if not(int(df_hero.sum()['total'])==10*len(rows)):
        raise(ValueError("Data integrity check fail"))
    if not(int(df_hero.sum()['win'])==5*len(rows)):
        raise(ValueError("Data integrity check fail"))
        
    return(df_hero)


def write_to_database(conn, df_hero, skill, time_range):
    sql_data=[]
    for idx, row in df_hero.iterrows():
        sql_data.append((idx.upper().replace("-","_")+"_"+str(skill),                         
                         skill,
                         idx,
                         time_range,
                         row['radiant_win'],
                         row['radiant_total'],
                         row['radiant_win_pct'],
                         row['dire_win'],
                         row['dire_total'],
                         row['dire_win_pct'],
                         row['win'],
                         row['total'], 
                         row['win_pct'],
                         #idx.upper().replace("-","_")+"_"+str(skill)
                        ))
    #stmt="INSERT INTO summary_win_rate (hero_skill, hero, time_range, radiant_win, "
    #stmt+="radiant_total, radiant_win_pct, dire_win, dire_total, dire_win_pct, win, "
    #stmt+="total, win_pct) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON DUPLICATE "
    #stmt+="KEY UPDATE hero_skill=?"
    
    stmt="REPLACE INTO fetch_win_rate (hero_skill, skill, hero, time_range, radiant_win, "
    stmt+="radiant_total, radiant_win_pct, dire_win, dire_total, dire_win_pct, win, "
    stmt+="total, win_pct) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?);"
    
    print(stmt)
        
    c=conn.cursor()
    c.executemany(stmt, sql_data)


def fetch_records(conn, begin, end, skill):

    stmt="SELECT start_time, match_id, radiant_heroes, dire_heroes, "
    stmt+="radiant_win FROM dota_matches WHERE start_time>={0} and "
    stmt+="start_time<={1} and api_skill={2}"

    stmt=stmt.format(
        int(begin.timestamp()),
        int(end.timestamp()),
        skill)
    
    print(stmt)
        
    c=conn.cursor()
    c.execute(stmt)
    rows=c.fetchall()
    print("Records: {}".format(len(rows)))
    return rows
    
    
    
def usage():
    print("python calc_winrate.py <days>")
    print("")
    print("days:    trailing window from utcnow()")    
    print("")
    sys.exit(-1)
          

def main():
    
    # Parsse command line
    if len(sys.argv)!=2:
        usage()
        
    try:
        days=int(sys.argv[1])
    except:        
        usage()
        
    utc=dt.datetime.utcnow()
    end=dt.datetime(utc.year, utc.month, utc.day, utc.hour, 0)
    begin=end-dt.timedelta(days=days)
    

    conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host=os.environ["DOTA_HOSTNAME"],
    database=os.environ['DOTA_DATABASE'])    

    for skill in [3,2,1]:
        
        print("Skill level: {}".format(skill))
        
        time_range = "{} to {}".format(            
            begin.isoformat(),
            end.isoformat())

        
        rows=fetch_records(conn,begin,end,skill)
        df_hero=parse_records(rows)
        write_to_database(conn, df_hero,skill,time_range)
        conn.commit()        
        
    conn.close()
    
if __name__ == "__main__":
    main()
