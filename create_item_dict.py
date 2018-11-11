# -*- coding: utf-8 -*-
"""Create the item dictionary, used once to populate meta.py"""
import pandas as pd

items=pd.read_csv("item_strings_kg.csv")
items[['Internal Name','Item ID']].drop_duplicates()
d={}
for idx,row in items.iterrows():
    d[row['Item ID']]=row['Internal Name']