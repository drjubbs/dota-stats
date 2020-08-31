#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import mariadb
import datetime as dt
import pandas as pd
"""
fetch_summary - Update table containing record counts cache in database,
used to monitor the health of the fetch job.

HORIZON_DAYS controls how far back in history is reprocessed each time
the script runs.
"""

HORIZON_DAYS=5

# Get UTC timestamps spanning HORIZON_DAYS ago to today
start_time=int((dt.datetime.utcnow()-dt.timedelta(days=HORIZON_DAYS)).timestamp())
end_time=int(dt.datetime.utcnow().timestamp())

# Connect to database and fetch records
conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host="localhost",
    database=os.environ['DOTA_DATABASE'])
c=conn.cursor()
stmt="SELECT start_time, match_id FROM dota_matches WHERE start_time>={0} and start_time<={1};".format(
    start_time,
    end_time)
print(stmt)
        
c.execute(stmt)
rows=c.fetchall()
print("Records: {}".format(len(rows)))

# Round off timestamps to the nearest hour, create data frame and aggregate on counts
times=[dt.datetime.utcfromtimestamp(t[0]).strftime("%Y-%m-%dT%H:00") for t in rows]
date_hour=[dt.datetime.strptime(t,"%Y-%m-%dT%H:%M").timestamp() for t in times]
match_ids=[t[1] for t in rows]
summary=pd.DataFrame({'date_hour' : date_hour, 'match_ids' : match_ids}).groupby("date_hour").count()

# Write to database, overwriting old records
counts=[]
for idx,row in summary.iterrows():
    stmt="INSERT INTO fetch_summary VALUES (?,?) ON DUPLICATE KEY UPDATE rec_count=(?)"
    c.execute(stmt, (int(idx), int(row['match_ids']), int(row['match_ids'])))
conn.close()    


# In[ ]:




