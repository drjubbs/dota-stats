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
import sys
import bz2
import mariadb
import pickle
import meta
from match import match_pb
import ujson as json
```

```python
# Setup database
conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host=os.environ['DOTA_HOSTNAME'],
    database=os.environ['DOTA_DATABASE'])
cursor=conn.cursor()
```

```python
cursor.execute("SELECT radiant_heroes, dire_heroes, items, gold_spent FROM dota_matches LIMIT 100")
rows=cursor.fetchall()
conn.close()
```

```python
BIGINT=2**64-1
```

```python
def encode_heroes_bitmask(heroes):
    """Returns a 3 BIGINT bitmask which encodes the heroes"""
    low_mask = 0
    mid_mask = 0
    high_mask = 0
    
    for hero_num in heroes:
        if hero_num>0 and hero_num<=63:
            low_mask=low_mask | 2**hero_num
        elif hero_num>63 and hero_num<=127:
            mid_mask=mid_mask | 2**(hero_num-64)
        elif hero_num>127 and hero_num<=191:
            high_mask=mid_mask | 2**(hero_num-128)
        else:
            raise ValueError("Hero out of range %d" % hero_num)

    return low_mask, mid_mask, high_mask

def where_bitmask(hero_num):
    """Returns SQL WHERE clause for a given hero"""
    
    if hero_num>0 and hero_num<=63:
        bitmask = 2**hero_num
        stmt = "WHERE hero_mask_low & {} = {}".format(bitmask, bitmask)
        
    elif hero_num>63 and hero_num<=127:
        bitmask = 2**(hero_num-64)
        stmt = "WHERE hero_mask_mid & {} = {}".format(bitmask, bitmask)
                
    elif hero_num>126 and hero_num<=191:
        bitmask = 2**(hero_num-128)
        stmt = "WHERE hero_mask_high & {} = {}".format(bitmask, bitmask)        
    else:
        raise ValueError("Hero out of range %d" % hero_num)

    return stmt

def decode_heroes_bitmask(bit_masks):
    """Returns list of heroes in match given a bitmask tuple/list"""
    
    low_mask, mid_mask, high_mask = bit_masks
    heroes = []
    for ibit in [t for t in range(64)]:
        if 2**ibit & low_mask == 2**ibit:
            heroes.append(ibit)
        if 2**ibit & mid_mask == 2**ibit:
            heroes.append(ibit+64)
        if 2**ibit & high_mask == 2**ibit:
            heroes.append(ibit+128)
            

    return heroes
```

```python
# Check some hand-selected patterns
test_patterns=[
    [1,2,3],              # Basic
    [1,63,64,123,124],    # Test edges
    [28, 17, 93, 66, 26], # From real games
    [23, 104, 9, 31, 8],  # From real games    
]

for test_pattern in test_patterns:
    enc=encode_heroes_bitmask(test_pattern)
    dec=decode_heroes_bitmask(enc)    
    print(set(test_pattern)==set(dec))    
```

```python
# Check all the numbers [1,189]
results=[]
for idx in [t+1 for t in range(188)]:
    enc=encode_heroes_bitmask([idx])
    print(all([t<BIGINT for t in enc]))
    dec=decode_heroes_bitmask(enc)
    results.append(idx==dec[0])    
print(all(results))
```

```python

```

```python
where_bitmask(1)
```

```python
where_bitmask(63)
```

```python
where_bitmask(64)
```

```python
where_bitmask(127)
```

```python
where_bitmask(128)
```

```python
BIGINT-9223372036854775808
```

```python
# Exceptions
encode_heroes_bitmask([190])
encode_heroes_bitmask([0])
```
