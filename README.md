# Summary

Uses Dota 2 REST API to fetch matches by skill level and hero, creates an SQLite3 database, which is in turn used to generate summary statistics.

Key files:
- `fetch.py` runs in background fetching new data.
- `process.py` processes database into win by position summary statistics (?)
- `hero_overall_winrate.ipynb`: Simple calculation of a hero's winrate.


# Setup

Acquire an API key from Valve and set the following environmental variables:

	export STEAM_KEY=1234567890....
	export DOTA_SQL_STATS_TABLE=dota_stats

Also install required packages:

	pip install -i requirements.txt

Create a basic shell script which activates the virtual environment and runs with required options. This script can be run from a user based crontab.

```
#!/bin/bash
export STEAM_KEY=0D3D25631076EE1DD6723DFC7E4123D8
export DOTA_SQL_STATS_FILE=matches.db
export DOTA_SQL_STATS_TABLE=dota_stats

cd dota-stats
source ./env/bin/activate
mkdir -p log

export DATESTR=`date +"%Y%m%d%H"`
python fetch.py all 1 60 1> log/matches_1_$DATESTR.log 2> log/matches_1_$DATESTR.err
export DATESTR=`date +"%Y%m%d%H"`
python fetch.py all 3 60 1> log/matches_3_$DATESTR.log 2> log/matches_3_$DATESTR.err
```


# TODO
- Check that the new logic excluding previously fetched matches is working...
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

