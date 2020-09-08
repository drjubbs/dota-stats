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

## Win Classification

Use match data and several machine learning models to try and classify the winner based on hero selection 
as well as hero/enemy hero pair interactions (i.e. basic counters).

**Note**: `ml_encode.py` must be prior to this script to generate cached sparse encodings. See that file for 
a description of the encoding methodology

```python
%load_ext autoreload
%autoreload 2
import copy
import plotly.express as px
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import *
from sklearn.svm import LinearSVC, SVC
from sklearn import linear_model
from sklearn.model_selection import GridSearchCV
from sklearn.dummy import DummyClassifier
from scipy import sparse
import meta
import ml_encoding
```

```python
y=sparse.load_npz("y.npz").toarray().transpose()
X1=sparse.load_npz("X1.npz")
X2=sparse.load_npz("X2.npz")
X3=sparse.load_npz("X3.npz")

print("Large matrix size: {}".format(X3.shape))
```

```python
models={
    "Dummy" : 
        (DummyClassifier(strategy="constant"),
         { 'constant' : [0,1] }  ),
    #"RandomForest" :
    #    (           
    #      RandomForestClassifier(n_estimators=100,                                  
    #                             class_weight='balanced_subsample',
    #                             bootstrap=False), # Turn off external CV
    #     { 'max_depth' : [5,10,15,25,35] }
    #    ),
    "Logistic_Regression" :
        (
            LogisticRegression(fit_intercept=False,class_weight='balanced_subsample'),
            { 'C' : [1000, 100, 10, 1, 0.1, 0.01, 0.001] }
        ),
    "GradientBoostingClassifier" :
        (
            GradientBoostingClassifier(verbose=2),
            {
                "n_estimators" : [1,10,100],
                "max_depth" : [3,4,5],
            }
        ),    
}
```

```python
models_search={}
for model_name, model in models.items():
    print("............................................................")
    print(model_name)
    gscv=GridSearchCV(estimator=model[0], 
                      param_grid=model[1],
                      verbose=2,
                      cv=3,
                      n_jobs=4,
                      scoring=make_scorer(accuracy_score))
    models_search[model_name]=copy.copy(gscv.fit(X1,y))
        
print("Done")
```

```python
for model_name, model_search in models_search.items():
    print("\n=========================================================")
    print(model_name)
    for params,mean_test_score in zip(model_search.cv_results_['params'], model_search.cv_results_['mean_test_score']):    
        print("\t"+str(params))
        print("\t"+str(mean_test_score))
        
    y_bar=model_search.best_estimator_.predict(X1)

    print(".............................")
    print("accuracy score")
    print(str(accuracy_score(y,y_bar)))

    print("balanced accuracy score")
    print(str(balanced_accuracy_score(y,y_bar)))

    print("confusion matrix")
    print(str(confusion_matrix(y,y_bar)))
```
## Logistic Regression With 2nd Order Effects

Note that L1 penality is used as in general this will force more coefficients to zero (i.e. sparse coefficient matrix).

```python
lr=LogisticRegression(fit_intercept=False,class_weight='balanced_subsample',penalty='l1', solver='saga')
params={ 'C' : [10, 1, 0.1, 0.01, 0.001] }    
gscv=GridSearchCV(estimator=lr, 
                  param_grid=params,
                  verbose=2,
                  cv=3,
                  n_jobs=4,
                  scoring=make_scorer(accuracy_score))
gscv.fit(X3,y)
```

```python
for params,mean_test_score in zip(gscv.cv_results_['params'], gscv.cv_results_['mean_test_score']):    
    print("\t"+str(params))
    print("\t"+str(mean_test_score))

y_bar=gscv.best_estimator_.predict(X3)
print(str(accuracy_score(y,y_bar)))
print(str(balanced_accuracy_score(y,y_bar)))
print(str(confusion_matrix(y,y_bar)))
```

```python
# First get the radiant and dire coefficients... in general these should be similar
coef=gscv.best_estimator_.coef_
a=(coef[0,0:meta.NUM_HEROES]).reshape(meta.NUM_HEROES,1)
b=(coef[0,meta.NUM_HEROES:2*meta.NUM_HEROES]).reshape(meta.NUM_HEROES,1)
```

```python
# Next unpack the 2nd order matrix...
c_flat=coef[0,2*meta.NUM_HEROES:]
c=ml_encoding.unflatten_second_order_upper(c_flat)
```

```python
results=pd.DataFrame(np.hstack([a,b,c]))
```

```python
results.index=meta.HERO_DICT.values()
results.columns=['dire','radiant']+list(meta.HERO_DICT.values())
```

```python
results.to_csv("results.csv")
```

```python
results
```

```python

```
