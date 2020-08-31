#!/usr/bin/env python
# coding: utf-8

# Compact SQLite3 into MariaDB
# 
# Older verions of this code generated SQLLite3 files instead of using a database, load these in.

import sqlite3
import os
import json
import pandas as pd
import datetime as dt
import re
import mariadb

# Merge database files and remove duplicates
DB_FILES=[]
for filename in os.listdir("."):    
    if re.match("^.*db$",filename) is not None:    
        DB_FILES.append(filename)
                    
rows=[]
for this_file in DB_FILES:
    conn=sqlite3.connect(this_file)
    c=conn.cursor()
    c.execute("SELECT match_id, start_time, radiant_heroes, dire_heroes, "\
              "radiant_win, api_skill, items, gold_spent FROM dota_stats")
    rows.extend(c.fetchall())
    print("{0} {1}".format(this_file,len(rows)))

rows=list(set(rows))
print("Removing duplicates: {0}".format(len(rows)))

# Write to MariaDB as configured in the environment
conn_maria = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host="localhost",
    database=os.environ['DOTA_DATABASE'])

c=conn_maria.cursor()
c.execute("select count(*) from dota_matches")
print("Rows before merge: {0} ".format(c.fetchall()[0][0]))

# Batch samples in
BATCH_SIZE=2000
for i in range(len(rows)//BATCH_SIZE+1):    
    begin=i*BATCH_SIZE
    end=min(len(rows),(i+1)*BATCH_SIZE)
    print("{0} to {1}".format(begin,end))
    stmt="INSERT IGNORE INTO dota_matches (match_id, start_time, "\
                  "radiant_heroes, dire_heroes, radiant_win, api_skill, "\
                  "items, gold_spent) values(?, ?, ?, ?, ?, ?, ?, ?)"
    print(stmt)
    c.executemany(stmt, list(rows)[begin:end])
    
conn_maria.commit()
c.execute("select count(*) from dota_matches")
print("Rows after merge: {0} ".format(c.fetchall()[0][0]))
conn_maria.close()
