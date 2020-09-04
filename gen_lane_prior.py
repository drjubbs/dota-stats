"""Extract lane presence for all heroes from Dotabuff website, used to 
develop part of `prior` probabilty distribution for doing lane estimation.
"""

from bs4 import BeautifulSoup
import requests
import time
import random
import pandas as pd

BASE_URL="https://www.dotabuff.com"

headers = {
        'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko)'
                       ' Chrome/74.0.3729.169 Safari/537.36'
        }

rv = requests.get("{}/heroes".format(BASE_URL), headers=headers)

if rv.status_code != 200:
    raise(ValueError("Non-200 return code from main page"))

bs=BeautifulSoup(rv.text, 'html.parser')
hg=bs.find("div", {'class' : 'hero-grid'})

tuples=[]
for link in [t.get("href") for t in hg.find_all("a")]:

    hero=link.split("/")[2].replace("-", "_").replace("'","")
    print(hero)

    rv2 = requests.get("{}/{}".format(BASE_URL, link),
                        headers=headers)

    if rv2.status_code != 200:
        raise(ValueError("Non-200 return code from hero page"))


    bs2=BeautifulSoup(rv2.text, 'html.parser')
    lp=[t for t in bs2.find_all("section") if \
                t.header.text=='Lane Presence'][0]

    for tr in lp.tbody.find_all("tr"):
        td=tr.find_all("td")
    
        # Append hero, lane, presence
        tuples.append((
            hero,
            td[0].text, 
            float(td[1].text.replace("%",""))/100.0))

    time.sleep(random.uniform(0,0.5))

# Create data frame, eliminate non safe/off/mid 
# lane presence, and renormalize
df=pd.DataFrame(tuples)
df.columns=['hero','lane','presence']
df=df.pivot(index='hero', columns='lane', values='presence')
df=df.fillna(0)
df=df[['Mid Lane','Safe Lane', 'Off Lane']]
df=df.div(df.sum(axis=1),axis=0)

# Rename the columns, duplicate P2/P5 probability from P1/P3
# probability
df=df.rename(columns={'Safe Lane' : 'P1', 'Mid Lane' : 'P2', 'Off Lane' : 'P3'})
df['P5']=df['P1']
df['P4']=df['P3']
df=df[["P{}".format(t+1) for t in range(5)]]

# Apply mask and renormalize one last time, allow
# some small probability in all positions
mask=pd.read_csv("position_mask.dat", index_col=0)

missing=set(df.index.values)-set(mask.index.values)
if len(missing)!=0:
    raise(ValueError("{0} missing in position_mask.dat".format(missing)))

prior=df*mask
prior=prior.replace(0, 0.01)
prior=prior.div(prior.sum(axis=1), axis=0)
prior.to_csv("position_prior.dat", encoding='utf-8')
