---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.2'
      jupytext_version: 1.6.0
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# Hero Overall Win Rates

Simple calculation of the overall win rate for each hero over a time horizon.

```python
import mariadb
import os
import meta
import json
import pandas as pd
import datetime as dt
import pytz
import re
import plotly.express as px
import pandas as pd
```

## Parameters for Analysis

```python
BEGIN=dt.datetime(2020,9,5)
END=dt.datetime(2020,9,7)
SKILL=3
title="{0} to {1}, skill={2}".format(BEGIN, END, SKILL)
print(title)
```

## Database connection

```python
conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host=os.environ["DOTA_HOSTNAME"],
    database=os.environ['DOTA_DATABASE'])
c=conn.cursor()
```

## Read in rows within a timerange

```python
stmt="SELECT start_time, match_id, radiant_heroes, dire_heroes, radiant_win FROM dota_matches WHERE start_time>={0} and start_time<={1} and api_skill={2}".format(
    int(BEGIN.timestamp()),
    int(END.timestamp()),
    SKILL)
print(stmt)
        
c.execute(stmt)
rows=c.fetchall()
print("Records: {}".format(len(rows)))
```

## Histogram of Times 

See if this covers most times of day evenly, 0 represents the earliest match, x-axis is in hours.

```python
times=[t[0] for t in rows]
min_t=min(times)
times=[(t-min_t)/3600 for t in times]
df_times=pd.DataFrame({'times' : times})
fig=px.histogram(df_times, x='times')
fig.show()
```

## Summary statistics

Tally win rate and pick rates, keeping radiant and dire seperate (allow for asymmetry).

```python
radiant_win=[]
radiant_total=[]
dire_win=[]
dire_total=[]

counter=0

for row in rows:
    if counter % 10000 == 0:
        print("{} of {}".format(counter,len(rows)))
        
    # Radiant win
    if row[4]==1:
        for hero in json.loads(row[2]):
            radiant_win.append(meta.HERO_DICT[hero])
            radiant_total.append(meta.HERO_DICT[hero])
        for hero in json.loads(row[3]):
            dire_total.append(meta.HERO_DICT[hero])
    
    # Dire win
    else:
        for hero in json.loads(row[2]):
            radiant_total.append(meta.HERO_DICT[hero])            
        for hero in json.loads(row[3]):
            dire_win.append(meta.HERO_DICT[hero])            
            dire_total.append(meta.HERO_DICT[hero])
    counter=counter+1
```

```python
# Convert the lists into DataFrames which are easier to manipulate

# Radiant Summary
df_radiant_win=pd.DataFrame(radiant_win, columns=['hero'])
df_radiant_win['radiant_win']=1
df_radiant_win=df_radiant_win.groupby("hero").count()

df_radiant_total=pd.DataFrame(radiant_total, columns=['hero'])
df_radiant_total['radiant_total']=1
df_radiant_total=df_radiant_total.groupby("hero").count()

df1=df_radiant_win.join(df_radiant_total)
df1['radiant_win_pct']=100.0*df1['radiant_win']/df1['radiant_total']

# Dire Summary
df_dire_win=pd.DataFrame(dire_win, columns=['hero'])
df_dire_win['dire_win']=1
df_dire_win=df_dire_win.groupby("hero").count()

df_dire_total=pd.DataFrame(dire_total, columns=['hero'])
df_dire_total['dire_total']=1
df_dire_total=df_dire_total.groupby("hero").count()

df2=df_dire_win.join(df_dire_total)
df2['dire_win_pct']=100.0*df2['dire_win']/df2['dire_total']

df_hero=df1.join(df2)
df_hero['win']=df_hero['radiant_win']+df_hero['dire_win']
df_hero['total']=df_hero['radiant_total']+df_hero['dire_total']
df_hero['win_pct']=100.0*df_hero['win']/df_hero['total']
```

```python
# Integrity checks... totals and winners should agree with match counts

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
```

## Pareto plot & radiant/dire symmetry

```python
df_hero['hero']=df_hero.index
fig=px.scatter(df_hero,
           x='total',
           y='win_pct',
           text='hero',
           title="All Pick {0} to {1}, Skill level {2}".format(
                BEGIN,
                END,
                SKILL,
               ),
           labels={                 
                   'total' : 'Total Matches',
                   'win_rate' : "Win Rate (%)",
                  
                  })
fig.update_traces(textposition='top center')
fig.update_layout(
    autosize=False,
    width=900,
    height=900,)
fig.show()
```

```python
# Calculate radiant vs. dire offset
offset=200*(df_hero.sum()['dire_win']-df_hero.sum()['radiant_win'])/df_hero.sum()['total']
print("Radiant vs. Dire delta%: {}".format(offset))
```

```python
fig=px.scatter(df_hero,
           x='radiant_win_pct',
           y='dire_win_pct',
           text='hero',
           title="All Pick {0} to {1}, Skill level {2}".format(
                BEGIN,
                END,
                SKILL,
               ),
           labels={                 
                   'total' : 'Total Matches',
                   'win_rate' : "Win Rate (%)",
                  
                  })

fig.update_layout(shapes=[
    dict(
      type= 'line',
      yref= 'y', y0= 0, y1= 100,
      xref= 'x', x0= 0, x1= 100,
    ),
      dict(
      type= 'line',
      yref= 'y', y0= offset, y1= 100+offset,
      xref= 'x', x0= 0, x1= 100,
    )
])
    
fig.update_layout(xaxis=dict(range=[35,65]),yaxis=dict(range=[35,65]))
    

fig.update_traces(textposition='top center')
fig.update_layout(
    autosize=False,
    width=900,
    height=900,)
fig.show()
```

```python

```
