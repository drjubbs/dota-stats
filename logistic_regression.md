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

## Logistic Regression Model

```python
import mariadb
import os
import meta
import json
import pandas as pd
import datetime as dt
import re
import plotly.express as px
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import *
from sklearn.svm import LinearSVC, SVC
import numpy as np
from sklearn import linear_model
from scipy import sparse
```

```python
# Data selection
BEGIN=dt.datetime(2020,8,31)
END=dt.datetime(2020,9,1,12,0,0)
SKILL=1
print("{0} to {1}".format(BEGIN, END))
```

```python
# Database fetch
conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host="localhost",
    database=os.environ['DOTA_DATABASE'])
c=conn.cursor()

# Fetch all rows
stmt="SELECT start_time, match_id, radiant_heroes, dire_heroes, radiant_win FROM dota_matches WHERE start_time>={0} and start_time<={1} and api_skill={2}".format(
    int(BEGIN.timestamp()),
    int(END.timestamp()),
    SKILL)

c.execute(stmt)
rows=c.fetchall()
print("Records: {}".format(len(rows)))
```

## Logistic Regression

Use simple logistic regression to determine probability of a win. It's tempting to trying something like this:
`log(p/(1-p)) = c0 + x1*c1 + x2*c2 + x3*c3 + ... `

where `c0` is the intercept and represents the contribution from being on radiant, `x1` .. `xn` are indicator variables, where `1` indicates the hero was selected on radiant, and `-1` indicates the hero was selected on dire. The issue here is that the interpretation of the coefficients becomes difficult. If `c1` is high, does that mean a high win rate for radiant or a high loss rate for dire? It also assumes that each hero has symmetric effects, radiant vs. dire.

Instead we will break each game into two vectors, a winner and loser, and use only `{0,1}` indicator variables:

`log(p/(1-p)) = a0 + x1*b1 + x2*b2 + x3*b3 + ... + y1*c1 + y2*c2 + y3*c3 + ...`

where `x_n=1` denotes hero was present on radiant, and `y_n=-1` denotes the hero was present on dire. The negation is used so that a negative coefficient on a dire term means the hero was more likely a win for dire.

```python
# Setup the X matrix, we'll use sparse matrices to be kind to memory usage
heroes=list(meta.HERO_DICT.keys())
num_heroes=len(heroes)
X=sparse.lil_matrix((len(rows),2*num_heroes), dtype='b')

counter=0
for row in rows:
    for rh in json.loads(row[2]):
        X[counter,heroes.index(rh)]=1
    for dh in json.loads(row[3]):
        X[counter,num_heroes+heroes.index(dh)]=-1
    counter=counter+1
    
# Setup the target vector
y=np.array([t[-1] for t in rows])
```

```python
# Some basic integrity checks: all rows should sum to 0 net heroes, radiant and
# dire should be balanced 5 & -5

a=np.array(X.sum(axis=1))
b=np.zeros(len(rows)).reshape(len(rows),1)
if not(np.all(a==b)):
    raise(ValueError("Error building sparse matrix"))

a=X[:,0:num_heroes].sum(axis=1)
b=np.ones(len(rows)).reshape(len(rows),1)*5
if not(np.all(a==b)):
    raise(ValueError("Error building sparse matrix"))


a=X[:,num_heroes:].sum(axis=1)
b=np.ones(len(rows)).reshape(len(rows),1)*(-5)
if not(np.all(a==b)):
    raise(ValueError("Error building sparse matrix"))

```

```python
#lr=LogisticRegression(C=0.01, fit_intercept=False)
#lr=RandomForestClassifier(n_estimators=100,verbose=2)
#lr=GradientBoostingClassifier(verbose=2)
lr=LinearSVC(verbose=2)
lr=SVC(kernel='rbf', verbose=2)
lr.fit(X,y)
```

```python
print(sum(y)/len(y))
print(confusion_matrix(y,lr.predict(X)))
print(accuracy_score(y,lr.predict(X)))
print(balanced_accuracy_score(y,lr.predict(X)))
```

```python

```

```python
summary=pd.DataFrame(lr.coef_.reshape(num_heroes,2,order='F'))
summary.columns=['radiant','dire']
summary.index=meta.HERO_DICT.values()
```

```python
for idx,row in summary.sort_values(by='radiant', ascending=False).iterrows():
    print("{0:20} {1:7.2f} {2:7.2f}".format(idx,row[0]*100,row[1]*100))
```

```python
lr
```

```python
dir(lr)
```

```python

```
