# Summary

This program uses the Dota 2 REST API to fetch match information by skill level and hero, storing results in a configured MariaDB instance. The scripts are designed to be run in the background using e.g. `crontab` to continuously harvest match data.

The project also includes several analysis scripts, which use a variety of a summary statistics and machine learning techniques to extract insight from the data. Some of the files are Jupyter Notebooks, stored as markdown. Since Jupyter Notebooks are difficult to `diff`, the `jupytext` extension should be used to run these notebooks and keep the markdown synced.

Overview of the key files:
- `fetch.py` runs in background fetching new data. It takes command line arguments for which hero and skill level to fetch. This is usually setup to run in the background using a crontab with a lock.
- `fetch_summary.py` can be run to update the summary statistics in the `fetch_summary` table. This is used to track job health.
- `meta.py` Meta-data contain enums and other contextual information for interpreting API results.
- `ml_encoding.py` Utility functions which encode hero and hero pairing information for machine learning. Used to flatten and unflatten feature sets as needed.
- `health_dashboard.md` Notebook which displays tables and graphs showing the results of the fetch jobs by hour and day.
- `hero_overall_winrate.md` Notebook showing basic win rate plotting using descriptive statistics.
- `gen_lane_prior.py` no longer actively used but perhaps useful, this script uses lane percentage information from http://dotabuff.com and some manually mask to provide a probability distribution for which farm position each hero should occupy. For a given match, you can then take the full time composition and calculate a "maximum likelihood" estimate to get farm priority. Not perfect, but it does allow some calculation of win percentage based on farm position.
- `icons.py` Download most recent minimap icons. Icons might be useful to clean up visualizations.
- `compact_db.py` earlier versions of the code using SQLite3 files instead of a MariaDB backend, this scripts compacts those files into a unique record set and transfers into MariaDB.
- `run_test.py` Unit testing

# Setup

After cloning the repository, it is suggested that you setup a virtual environment and install the required python packages:

	cd dota_stats
	python3 -m venv env
	source env/bin/activate
	pip install --upgrade pipe
	pip install -i requirements.txt

Proceed to follow instructions to setup MariaDB on your platform.   You may need to allow remote access if your analysis machine is different from your database, this usually involves setting the `bind-address` in MariaDB to `0.0.0.0` or commenting out that line.

Login as root substituting and run the following script, substituting in a strong password for `password1`. Note that using MyISAM (vs. InnoDB) as the engine on a Raspberry PI had a profound impact on performance, this may not be true on all platforms. 

The following script creates the production database, you may find it helpful to repeat for a development environment. I have separate servers for fetching new data and processing the data so the DB users are defined across my subnet.

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

CREATE TABLE fetch_summary (date_hour BIGINT PRIMARY KEY,\
                            skill INT,\
                            rec_count INT) ENGINE='MyISAM';

CREATE TABLE fetch_history (match_id BIGINT PRIMARY KEY,\
                            start_time BIGINT) ENGINE='MyISAM';
                         
CREATE USER 'dota_prod'@'192.168.%.%' IDENTIFIED BY 'password1';
GRANT ALL PRIVILEGES ON dota_prod.* TO 'dota_prod'@'192.168.%.%';
```

For each environment, I generally create a file `env.sh` which sets the appropriate environmental variables and boots up the python environment (`env.sh`):

	export STEAM_KEY=1234567890....
	export DOTA_USERNAME=dota_prod
	export DOTA_PASSWORD=password1
	export DOTA_HOSTNAME=192.168.1.100
	export DOTA_DATABASE=dota_prod
	export FLASK_APP="server.py"
	
	source ./env/bin/activate

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
- Think about how to balance coefficients in logistic regression when 2nd order effects are include (i.e. shift weight on coefficients from hero-hero interactions onto base hero). Perhaps fit the model in two stages, with the hero/hero interactions on the residuals.

- How to publish results in a meaningful way on a site like reddit?

- In logs, look for `num_results (try` . How often is this failing? It appears Valve's API often returns no records, perhaps due to some error with a load balancer?

- In logs get a count of URLError, HTTPError, etc... and adjust number of threads accordingly.

- Clean-up/linting of all code.

- Audit log level in `fetch.py` so that INFO can be turned off and logs are smaller and contain more helpful error information.

- Add win rate by position based on maximum likelihood to the `hero_overall_winrrate` workbook.

- Consider adding a second mode to `fetch` where match IDs are randomly sampled over a time horizon vs. using the (broken) GetMatchHistory endpoint.

- Recheck filtering on fetch that it is accurate and what is desired.

  
