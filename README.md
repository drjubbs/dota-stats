# Summary

Uses Dota 2 REST API to fetch matches by skill level and hero, creates an SQLite3 database, which is in turn used to generate summary statistics.

`fetch.py` runs in background fetching new data, `process.py` processes database into win by position summary statistics.

# Setup

Aquire an API key from Valve and set the following environmental variables:

	export STEAM_KEY=1234567890....
	export DOTA_SQL_STATS_TABLE=dota_stats

Also install required packages:

	pip install -i requirements.txt


# TODO

- Finish re-ranking of position logic in `process.py` to assign hero
  positions based on based likelihood. Used to calculate win probably 
  by farm position summary.
- Unit testing for `process.py`
- New mode: implement MatchID vs. time model to sample matches randomly vs. 
  going in hero order, this way popularity is capturely appropriately.
- Additional testing of code with summoned units which can have items (e.g. 
  Lone Druid)
- Make sure filtering on fetch is accurate and what is desired.

