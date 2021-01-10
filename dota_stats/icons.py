# -*- coding: utf-8 -*-
"""Download minimap icons used in plotting"""
import re
import time
import requests
from bs4 import BeautifulSoup
from dota_stats import meta


def main():
    """Main entry point"""
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/74.0.3729.169 Safari/537.36 '
            }

    resp = requests.get("https://dota2.gamepedia.com/Minimap", headers=headers)
    bsoup = BeautifulSoup(resp.text, 'html.parser')

    # Look for for a table with hyperlinks that match the number of heroes
    tables = bsoup.find_all("tbody")
    this_table = None
    for table in tables:
        if len(table.find_all("a")) == meta.NUM_HEROES:
            this_table = table

    # Extract the urls and save
    for link in this_table.find_all("a"):
        url = str((link.find("img"))['src'])
        print(url)

        resp = requests.get(url)

        if resp.status_code != 200:
            raise ValueError("Error fetching: {}".format(link))

        match = re.match(".*/(.*)_minimap.*", url)
        file_name = match.group(1).lower().replace("-", "_")

        with open("./server/icons/{}.png".format(file_name), "wb") as fname:
            fname.write(resp.content)

        time.sleep(0.5)


if __name__ == "__main__":
    main()
