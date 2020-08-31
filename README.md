# Summary

This program uses the Dota 2 REST API (see https://steamwebapi.azurewebsites.net/) to fetch match information by skill level and hero, storing results in a configured MariaDB instance. The scripts are designed to be run in the background using e.g. `crontab` to continuously harvest match data.

The project also includes several analysis scripts, which use a variety of a summary statistics and machine learning techniques to extract insight from the data.

Overview of the key files:
- `fetch.py` runs in background fetching new data. It takes command line arguments for which hero and skill level to fetch. This is usually setup to run in the background using a crontab with a lock.
- `fetch_summary.py` can be run to update the summary statistics in the `fetch_summary` table. This is used to track job health.
- `compact_db.py` earlier versions of the code using SQLite3 files instead of a MariaDB backend, this scripts compacts those files into a unique record set and transfers into MariaDB.
- 


# Setup

After cloning the repository, it is suggested that you setup a virtual environment and install the required python packages:

	cd dota_stats
	python3 -m venv env
	source env/bin/activate
	pip install --upgrade pipe
	pip install -i requirements.txt

Proceed to follow instructions to setup MariaDB on your platform.  Login as root substituting and run the following script, substituting in a strong password for `password1`. Note that using MyISAM (vs. InnoDB) as the engine on a Raspberry PI had a profound impact on performance, this may not be true on all platforms. The following script creates the production database, you may find it helpful to repeat for a development environment.

```
DROP DATABASE if exists dota_prod;
CREATE DATABASE dota_prod;
USE dota_prod;
CREATE TABLE dota_matches (match_id BIGINT PRIMARY KEY, \
                         start_time BIGINT, \
                         radiant_heroes CHAR(32), \
                         dire_heroes CHAR(32), \
                         radiant_win BOOLEAN, \
                         api_skill INTEGER, \
                         items VARCHAR(1024), \
                         gold_spent VARCHAR(1024))
                         ENGINE = 'MyISAM';
                         
CREATE TABLE fetch_summary (date_hour BIGINT PRIMARY KEY, rec_count INT) ENGINE='MyISAM';
                         
CREATE USER 'dota_prod'@localhost IDENTIFIED BY 'password1';
GRANT ALL PRIVILEGES ON dota.* TO 'dota_prod'@localhost;
```

For each environment, I generally create a file `env.sh` which sets the appropriate environmental variables and boots up the python environment (`env.sh`):

	export STEAM_KEY=1234567890....
	export DOTA_USERNAME=dota
	export DOTA_PASSWORD=password1
	
	source ./env/bin/activate

**export DOTA_DATABASE=dota_prod**

Prior to doing any work, `source` the file above (note that running the script will not work as the environmental variables will not be persistant).

Next create a basic shell script (`fetch_prod.sh`) which activates the virtual environment and runs with required options. This script will be run from a user based crontab. 

```
#!/bin/bash
cd dota-prod
source env.sh
mkdir -p log

export DATESTR=`date +"%Y%m%d%H"`
python fetch.py all 1 &> log/matches_1_$DATESTR.log
```

All of this can then be setup to run on a regular basis using a user crontab (`crontab -e`). The use of `flock` is suggested to ensure that multiple jobs are not running at the same time. `flock` accounts for a lot of the odd bookkeeping.

```
05 */2 * * * /usr/bin/flock -n /tmp/fetch_prod.lockfile bash -l -c '/home/pi/fetch_prod.sh'
```



# TODO

- Covert `fetch.py` to use MariaDB directly, eliminating the older SQLite3 staging files. Also modify to fetch all skill levels (not just normal skill) so that comparisons can be done at various skill levels. See what the impact on # of records fetched is.
- Add the summary statistics update to the end of the `fetch.sh` script so that the match count is automatically populated.
- Increase number of threads from 8 to 16 to see if we can fetch more data?
  - Moved to urllib3, see if this resolves protocol errors I was seeing before.
- Use new MariaDB database to compare pre- and post-patch winrrates.
- Migrate `fetch.py` over to using MariaDB
  - Needs to load initial dictionary of known matches on started (at least within a reasonable data range)
  - Table/user/database/etc... needs to be setup in environment to allow for development testing
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

