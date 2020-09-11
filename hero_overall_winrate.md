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

```python
import os
import mariadb
import pandas as pd
import plotly
import plotly.graph_objects as go
```

# Hero Overall Win Rates

Simple calculation of the overall win rate for each hero over a time horizon.


## Pareto plot & radiant/dire symmetry

```python
skill_dict = {
    1: 'Normal Skill',
    2: 'High Skill',
    3: 'Very High Skill',        
}
```

```python
conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host=os.environ["DOTA_HOSTNAME"],
    database=os.environ['DOTA_DATABASE'])
```

```python
df_sql=pd.read_sql("select * from summary_win_rate",conn)
```

```python
df_sql['skill']=[int(t.split("_")[-1]) for t in df_sql['hero_skill']]
```

```python
for skill in list(set(df_sql['skill'])):
        
    df_sub=df_sql[df_sql['skill']==skill]
    
    print("Radiant win rate: {}".format(df_sub.sum()['radiant_win']/(df_sub.sum()['radiant_total'])))
    
    time_range=set(df_sub['time_range']).pop()
    
    title="{0}: {1} UTC".format(skill_dict[skill], time_range)
    
    fig=go.Figure(data=go.Scatter(
                        x=df_sub['total'].values, 
                        y=df_sub['win_pct'].values, 
                        text=df_sub['hero'].values,
                        mode='markers+text',
                        textposition='top center'
                    ))
    fig.update_layout(title=title,
                     height=700,
                     width=700)
    fig.update_xaxes({'title' : 'Number of Games'})
    fig.update_yaxes({'title' : 'Win %'})
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
