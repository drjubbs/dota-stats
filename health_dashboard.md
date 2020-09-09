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

# Health Dashboard

Use the `fetch_summary` table to calculate and display metrics related to the performance of the `fetch.py` job.

```python
import mariadb
import os
import pandas as pd
import datetime as dt
import pytz
import json
import plotly
import plotly.graph_objs as go
import pandas as pd
```

```python
conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host=os.environ["DOTA_HOSTNAME"],
    database=os.environ['DOTA_DATABASE'])
c=conn.cursor()
```

```python
begin=int((dt.datetime.utcnow()-dt.timedelta(days=3)).timestamp())
begin=str(begin)+"_0"
```

```python
c.execute("select date_hour_skill, rec_count from fetch_summary where date_hour_skill>='{}'".format(begin))
rows=c.fetchall()

# Split out times and localize to my server timezone (East Coast US)
mytz=pytz.timezone("US/Eastern")
times=[dt.datetime.fromtimestamp(int(t[0].split("_")[0])) for t in rows]
times=[mytz.localize(t).strftime("%Y-%m-%dT%H:00:00") for t in times]
# Get remaining fields
skills=[int(t[0].split("_")[1]) for t in rows]
rec_count=[t[1] for t in rows]
```

```python
# Pivot for tablular view
df_summary=pd.DataFrame({
    'date_hour' : times,
    'skill' : skills,
    'count' : rec_count
    })
df_summary=df_summary.pivot(index='date_hour', columns='skill', values='count').fillna(0).astype('int32').sort_index(ascending=False)
df_summary=df_summary[[1,2,3]]
df_summary.columns=['normal', 'high', 'very_high']

# Print out a summary table
for idx, row in df_summary.iterrows():
    print("{0:20} {1:8} {2:8} {3:8}".format(idx, int(row['normal']), int(row['high']), int(row['very_high'])))
```

```python
fig = go.Figure(data=[
    go.Bar(name='Normal', x=df_summary.index.values, y=df_summary['normal']),
    go.Bar(name='High', x=df_summary.index.values, y=df_summary['high']),
    go.Bar(name='Very High', x=df_summary.index.values, y=df_summary['very_high']),
])
record_count_plot=json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
```

```python
fig.update_layout(barmode='stack')
fig.show()
```

```python

```
