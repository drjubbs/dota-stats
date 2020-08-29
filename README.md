# Summary

Uses Dota 2 REST API to fetch matches by skill level and hero, creates an SQLite3 database, which is in turn used to generate summary statistics.

Key files:
- `fetch.py` runs in background fetching new data.
- `process.py` processes database into win by position summary statistics (?)
- `hero_overall_winrate.ipynb`: Simple calculation of a hero's winrate.


# Setup

Install required python packages:

	pip install -i requirements.txt

Setup MariaDB configuration, substituting in a strong password for `password1`. Note that using `MyISAM` as the engine on a Raspberry PI had a profound impact on performance.

```
DROP DATABASE if exists dota;
CREATE DATABASE dota;
USE dota;
CREATE TABLE dota_matches (match_id BIGINT PRIMARY KEY, \
                         start_time BIGINT, \
                         radiant_heroes CHAR(32), \
                         dire_heroes CHAR(32), \
                         radiant_win BOOLEAN, \
                         api_skill INTEGER, \
                         items VARCHAR(1024), \
                         gold_spent VARCHAR(1024))
                         ENGINE = 'MyISAM';
                         


CREATE USER 'dota'@localhost IDENTIFIED BY 'password1';
GRANT ALL PRIVILEGES ON dota.* TO 'dota'@localhost;
```

Add the following environmental variables to your shell:

	export STEAM_KEY=1234567890....
	export DOTA_USERNAME=dota
	export DOTA_PASSWORD=password1

Create a basic shell script which activates the virtual environment and runs with required options. This script can be run from a user based crontab. It should export the same environmental variables as the shell to ensure the scripts work properly.

```
#!/bin/bash
export STEAM_KEY=1234567890....
export DOTA_USERNAME=dota
export DOTA_PASSWORD=password1


cd dota-stats
source ./env/bin/activate
mkdir -p log

export DATESTR=`date +"%Y%m%d%H"`
python fetch.py all 1 60 1> log/matches_1_$DATESTR.log 2> log/matches_1_$DATESTR.err
export DATESTR=`date +"%Y%m%d%H"`
python fetch.py all 3 60 1> log/matches_3_$DATESTR.log 2> log/matches_3_$DATESTR.err
```


# TODO
- Increase number of threads from 8 to 16 to see if we can fetch more data?
  - Moved to urllib3, see if this resolves protocol errors I was seeing before.
- Use new MariaDB database to compare pre- and post-patch winrrates.
- Migrate `fetch.py` over to using MariaDB
  - Needs to load initial dictionary of known matches on started (at least within a reasonable data range)
- Check that the new logic excluding previously fetched matches is working... search for "matches for processing" in logs toward the end...
- In `fetch/process_match` see if exceptions are causing a hard stop (they should??)
- Profile/optimize `fetch.py` so that all high skill level games can be captured. Histogram of match times should not have any missing data.
- Update virtual environment and `requirementstxt`.
- Optimize number of matches being processed so that an entire day's worth at a single skill level can be captured. This is likely a combination of code optimization, reduced sleep timers, and only selecting matches within a range based on an initial scan.
- `fetch.py` crashes when a non-unique primary key is given (e.g. the match already  exists in the database.)
- Split out the database merge option into a seperate workflow.
- Move databases and logfiles to a separate directory which will
  be created if it doesn't exist.
- Check log level in `fetch.py` so that INFO can be turned off and
  logs contain more helpful error information.
- Finish re-ranking of position logic in `process.py` to assign hero
  positions based on based likelihood. Used to calculate win probably 
  by farm position summary.
- Unit testing for `process.py`
- New mode: implement MatchID vs. time model to sample matches randomly vs. 
  going in hero order, this way popularity is capturely appropriately.
- Additional testing of code with summoned units which can have items (e.g. 
  Lone Druid)
- Make sure filtering on fetch is accurate and what is desired.

