"""Download minimap icons used in plotting"""
import requests
import meta
import time
import meta
from bs4 import BeautifulSoup
import re

# +
headers = {
        'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko)'
                       ' Chrome/74.0.3729.169 Safari/537.36'
        }

rv = requests.get("https://dota2.gamepedia.com/Minimap", headers=headers)
bs=BeautifulSoup(rv.text, 'html.parser')
# -

# Look for for a table with hyperlinks that match the number of heroes
tables=bs.find_all("tbody")
this_table=None
for table in tables:
    if len(table.find_all("a"))==meta.NUM_HEROES:
        this_table=table

# Extract the urls and save
for link in this_table.find_all("a"):
    url=str((link.find("img"))['src'])
    print(url)
    
    rv=requests.get(url)
    if rv.status_code != 200:
        raise ValueError("Error fetching: {}".format(hero))
    
    m=re.match(".*\/(.*)_minimap.*",url)    
    file_name=m.group(1).lower().replace("-","_")
    
    with open("./icons/{}.png".format(file_name),"wb") as f:
        f.write(rv.content)
    
    time.sleep(0.5)

