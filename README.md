# Summary

This program uses the Steam Dota 2 REST API to fetch match information by skill level and hero, storing results in a configured MariaDB/MySQL instance. The scripts are designed to be run in the background using e.g. `crontab` to continuously harvest match data.

The project also includes several analysis scripts and a web server, which use a variety of a summary statistics and machine learning techniques to extract insight from the data. Some of the files are Jupyter Notebooks, stored as markdown. Since Jupyter Notebooks are difficult to `diff`, the `jupytext` extension should be used to run these notebooks and keep the markdown synced.

The web server is a Flask based application, which I typically host through a reverse proxy configuration using Nginx and Gunicorn.

## Contents

[TOC]

# Analytical Methods

## Hero/Role Probability Model

Given the scope of this project, it is impractical to analyze each match in detail to determine which role was played by each hero. However, many heroes (e.g. Tiny, Mirana, Void Sprit, etc...) are frequently played in multiple roles, and therefore overall win rate metrics might not capture key statistics. Therefore, this project employs an approximate methods, inspired by Bayesian statistics to do role assignment for subsequent analytics. These pieces of information are used to construct this model:

- `A`  - An estimated position based on gold spent, taken from each match
- `B`  - Lane presence estimates from Dota 2 statistical websites such as Dotabuff
- `C`  - A manual configured "mask" restricting some heroes to roles (e.g. Anti-Mage should always be position 1)

Each of these factors are normalized so role (farm position) totals 1. Prior to normalization, a minimal probability of 1% is given to each hero/role combination to allow for unlikely but "creative" heroes choices. These probabilities are multiplied together, and re-normalized to generate the probability model used for maximum likelihood role assignment. The file `analytics/prior_final.json` contains this models, along with a timestamp. An example of this probability model visualized as a heat map:

![hero prior example](./doc/hero_prior_example.png)



# Configuration and Usage

## Python Virtual Environment

After cloning the repository, it is suggested that you setup a virtual environment and install the required python packages.

	cd dota_stats
	python3 -m venv env
	source env/bin/activate
	pip install --upgrade pip
	pip install -i requirements.txt

I have found it helpful to use a small utility shell script, which also sets environmental variables the setup will need.

```
$ cat 'env.sh'
export STEAM_KEY=0D3D2....
export DOTA_USERNAME=dota
export DOTA_DATABASE=dota
export DOTA_HOSTNAME='localhost'
export DOTA_PASSWORD=8e348...
export DOTA_LOGGING=0
export FLASK_APP=server.py
source env/bin/activate
```

## MariaDB/MySQL

Proceed to follow instructions to setup MariaDB on your platform.   You may need to allow remote access if your analysis machine is different from your database, this usually involves setting the `bind-address` in MariaDB to `0.0.0.0` or commenting out that line.

Note that using MyISAM (vs. InnoDB) as the engine on a Raspberry PI/small virtual machine had a profound impact on performance, this may not be true on all platforms. To reduce memory footprint, the I found the following tweaks to MariaDB defaults to be helpful (`/etc/mysql/mariaBase.conf.d/50-server.cnf`):

```
[mysqld]

...

#
# * Azure Adjustments
#
performance_schema = off
key_buffer_size = 16M
query_cache_size = 2M
query-cache-limit = 1M
tmp_table_size = 1M
innodb_buffer_pool_size = 0
innodb_log_buffer_size = 256K
max_connections = 20
sort_buffer_size = 512M
read_buffer_size = 256K
read_rnd_buffer_size = 512K
join_buffer_size = 128K
thread_stack = 196K

...
```

Login to MariaDB as root user. The following script creates the production database, you may find it helpful to repeat for a development environment. Change the user password to something secure. I have separate servers for fetching new data and processing the data so the DB users are defined both locally and across my subnet.

```
DROP DATABASE if exists dota;
CREATE DATABASE dota;
USE dota;
CREATE TABLE dota_matches (match_id BIGINT PRIMARY KEY, start_time BIGINT, radiant_heroes CHAR(32), dire_heroes CHAR(32), radiant_win BOOLEAN, api_skill INTEGER, items VARCHAR(1024), gold_spent VARCHAR(1024)) ENGINE = 'MyISAM';

CREATE TABLE fetch_summary (date_hour_skill CHAR(32) PRIMARY KEY, skill INT, rec_count INT) ENGINE='MyISAM';

CREATE TABLE fetch_history (match_id BIGINT PRIMARY KEY, start_time BIGINT) ENGINE='MyISAM';

CREATE TABLE fetch_win_rate (hero_skill CHAR(128) PRIMARY KEY, skill TINYINT, hero CHAR(128), time_range CHAR(128), radiant_win INT, radiant_total INT, radiant_win_pct FLOAT, dire_win INT, dire_total INT, dire_win_pct FLOAT, win INT, total INT, win_pct FLOAT) ENGINE='MyISAM';

CREATE DATABASE dota_dev;

CREATE USER 'dota'@'localhost' IDENTIFIED BY 'password1';
GRANT ALL PRIVILEGES ON dota.* TO 'dota'@'localhost';
GRANT ALL PRIVILEGES ON dota_dev.* TO 'dota'@'localhost';

```

## Automation/Crontab

Next create a basic shell script (`fetch.sh`) which activates the virtual environment and runs the scripts with the required options. 

```
#!/bin/bash
cd dota-stats
source env.sh
mkdir -p log

export DATESTR=`date +"%Y%m%d_%H%M"`
for SKILL in 1 2 3;
do
        python fetch.py all $SKILL &>> log/fetch_$DATESTR.log
        python fetch_summary.py 3 &>> log/fetch_$DATESTR.log
        python fetch_win_rate.py 1 &>> log/fetch_$DATESTR.log
done
```

This can then be setup to run on a regular basis using a user crontab (`crontab -e`). The use of `flock` is suggested to ensure that multiple jobs are not running at the same time.

```
*/10 * * * * /usr/bin/flock -n /tmp/fetch.lockfile bash -l -c '/home/dota/fetch.sh'
```

## Reverse Proxy Setup

I use a combination of Nginx, Let's Encrypt, and Gunicorn to host the Flask application. Other stacks are possible but I've this one to be fairy straightforward to setup. Getting TLS certificates from Let's Encrypt is beyond the scope of this document. I hade the following edits to `/etc/nginx/sites-enabled/default`

```
server {
        listen 443 ssl;
        server_name server.com;
        ssl_certificate     /etc/letsencrypt/live/server.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/server.com/privkey.pem;
        ssl_protocols       TLSv1 TLSv1.1 TLSv1.2;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        location / {
                # First attempt to serve request as file, then
                # as directory, then fall back to displaying a 404.
                proxy_pass http://127.0.0.1:8000;
        }
}

server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name server.com;
		
		# Intercept Let's Encrypt handshake, this must occur on port 80
        location /.well-known {
            alias /var/www/letsencrypt/.well-known;
        }

        location / {                
                # Redirct to HTTPS
                return 301 https://$host$request_uri;
        }
}

```

This will redirect first to port 443 for TLS, and then locally to port 8000 which is where Gunicorn/Flask will be setup. Create a script to startup the server:

```
#!/bin/bash
cd dota-stats
source env.sh
cd server
gunicorn -w 1 --reload server:app
```

I use `supervisord`  to ensure Gunicorn stays running `/etc/supervisor/supervisord.conf`:

```
...
[program:gunicorn]
command=/home/dota/start_server.sh
directory=/home/dota
user=dota
autostart=true
autorestart=true
redirect_stderr=true
```

Restart the supervisor service: `sudo systemctl restart supervisor`. Now requests to port 80 (at least the root page) should be re-directed to `gunicorn` which is running on port 8000. This should all survive a reboot and is worth testing.

## Database Backup

Dumping the entire database can be slow and costly. 

```
TODO: INSTRUCTIONS FOR SHUTDOWN OF SERVICES
--single-transaction --quick --lock-tables=false ...Does this help...???
db_snapshot.py [DAYS]
```

To limit records, a  timestamp filter can be applied to `mysqldump`:

```mysqldump --databases dota --tables dota_matches --where="start_time>1604592194" -u dota -p > dota_matches.sql
mysqldump --databases dota --tables dota_matches --where="start_time>1604808513" -u dota -p | gzip > dota_matches.sql.gz
```

where `start_time` can be obtained from a Python shell to represent a few hours/days worth of data:

```
>>> from datetime import datetime, timedelta
>>> int((datetime.now()-timedelta(hours=12)).timestamp())
1604592194.271184
```

# TODO

- High Priority
  
  - Server HTML
    - Cleanup display
    - Add navbar anchors
    - Check for valid HTML/CSS
    - Format properly for mobile 
    - Each skill level should have a different time range.
  - Move rest of project over to ORM model (remove mariadb dependency): fetch.py is done, work on other files.
  - For all "summary" statistics jobs, DAYS should be relative to most recent match in database to make this universal. Move this to a utility function somewhere.
  - Implement win rate by position database write and modify front-end to display.
  - Remove `fetch_history` table this can be taken directly from the main match table.
  
- General
  
  - `db_util.py`: Add CLI features and ability to upgrade DB to create new table for win rate by position; add appropriate unit testing.
  - Protobuf: Include new fields for modeled roles (based on probability model), include GPM, match duration, and other useful information which might be needed for analytics. Include player IDs for future work to model skill level based on match statistics.
  - Bitmask implementation - need ability to search database for matches involving a specific hero.
  - Replace other instances of "INSERT INTO .... DUPLICATE KEY" with "REPLACE INTO".
  - Reversion requirements.txt to the newest distro (Ubuntu 20.04 LTS).
  - Clean-up/linting of all code.
  
- Backend
  - Look at ThreadPooling code in fetch.py - it's probably possible to start the executor at a higher level to prevent the continuous creation and destruction of thread pools.
  - Check logs and /errors for malformed responses I continue be getting from the API -- Grep "ERROR" and "Traceback" in production logs.
  - Recheck filtering on fetch that it is accurate and what is desired. Add appropriate unit testing.
  - Document fetch logic as well as filtering algorithms being used.
  - In logs, look for `num_results (try` . How often is this failing? It appears Valve's API often returns no records at times, perhaps due to some error with a load balancer and a misconfigured node?
  - In logs get a count of `URLError`, `HTTPError`, etc... and adjust number of threads accordingly.
  
- Web Server
  
  - Pick rate/win rate chart -- time range will be different for each skill level, modify accordingly...
  
- Data Analysis / Modeling
  
  - `generate_prior.py`: Add command line arguments and modify to work using dates instead of record counts.
  - `winrate_position.py`: Add command line arguments and ability to write to new database table. CLI arguments should include a date range. Add appropriate unit testing.
  - `win_analysis` needs to be extended to include hero vs. enemy good/bad match-ups. This is currently waiting on bit masking for heroes as each hero will need to be done independently due to memory constraints.
    - Is the 2nd order upper triangular style analysis even needed once we go to a per-hero model? If not, modify this document and edit `dotautil.py` to remove unused functions.
  
  