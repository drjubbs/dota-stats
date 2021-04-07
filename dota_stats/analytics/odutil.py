"""OpenDota utility functions"""

import time
import bs4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class OpenDota:
    """Fetch a match from OpenDota using Selenium driver. This is needed to
    wait for JavaScript to finish loading.
    """
    def __init__(self):
        """Initial Firefox brower using Selenium"""

        # Fetch Firefox Browers in headless mode for javascript
        options = Options()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

    def get_match(self, match_id):
        """Use Selenium to fetch OpenDota match information. Javascript takes a
        while to load, so loop until we get the `hero-icons` class."""

        print("Fetching OpenData match id {} ".format(match_id))
        url = "https://www.opendota.com/matches/{0}".format(match_id)

        soup3 = None
        hero_icons = None
        counter = 0
        sleep_schedule = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]

        while hero_icons is None:
            self.driver.get(url)
            time.sleep(sleep_schedule[counter])
            soup3 = bs4.BeautifulSoup(self.driver.page_source, "html.parser")
            hero_icons = soup3.find("div", {"class": "hero-icons"})

            if sleep_schedule[counter] == sleep_schedule[-1]:

                import pdb
                pdb.set_trace()

                raise ValueError("OpenDota page not loading in time {}. Match "
                                 "might be missing try requesting a parse and "
                                 "running again ("
                                 "https://www.opendota.com/request)".
                                 format(url))
            counter += 1
        return soup3
