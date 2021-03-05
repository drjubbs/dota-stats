---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.2'
      jupytext_version: 1.8.0
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# Hero Win Matrix

Use `dota_hero_matchup` table to find advantageous/disadvantageous matchups for a given hero

TODO: 
- Add integrity check... for a match/hero, should have 25 rows. For full match, we should have 250 rows.

```python
HERO = 'juggernaut'
```

```python
import pandas as pd
from dota_stats import db_util, meta
```

```python
pd.options.display.max_rows = None
```

```python
engine, session = db_util.connect_database()
```

```python
hero_num = meta.REVERSE_HERO_DICT[HERO]
```

```python
stmt = "select * from dota_hero_matchup where hero1={}".format(hero_num)
df_matchup = pd.read_sql(stmt, engine)
```

```python
len(df_matchup)
```

```python
wins = df_matchup[["win", "hero2"]].groupby('hero2').sum()
wins.index = [meta.HERO_DICT[t] for t in wins.index]
cnts = df_matchup[["win", "hero2"]].groupby('hero2').count()
cnts.index = [meta.HERO_DICT[t] for t in cnts.index]
```

```python
win_pct = 100*wins/cnts
```

```python
win_pct = win_pct.sort_values(by='win')
```

```python
win_pct = win_pct.rename(columns={'win' : 'win_pct'})
wins = wins.rename(columns={'win' : 'wins'})
cnts = cnts.rename(columns={'win' : 'matches'})
```

```python
df_summary = win_pct.join(wins).join(cnts)
```

```python
df_summary
```

```python

```
