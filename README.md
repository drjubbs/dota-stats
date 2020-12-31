# Summary

This program uses the Steam Dota 2 REST API to fetch match information by skill level and hero, storing results in a configured MariaDB/MySQL instance. The scripts are designed to be run in the background using e.g. `crontab` and `supervisor` to continuously harvest match data.

The project also includes several analysis scripts and a web server, which use a variety of a summary statistics and machine learning techniques to extract insight from the data. Some of the files are Jupyter Notebooks, stored as markdown. Since Jupyter Notebooks are difficult to `diff`, the `jupytext` extension should be used to run these notebooks and keep the markdown synced.

The web server is a Flask based application, which is typically hosted through a reverse proxy configuration using Nginx and Gunicorn.

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

I have found it helpful to use small utility shell script(s), which also sets environmental variables the setup and program will need.

```
$ cat 'env.sh'
export STEAM_KEY=0D3D2....
export DOTA_DB_URI=mysql://dota:password@localhost/dota
export DOTA_LOGGING=0
export DOTA_THREADS=8

export FLASK_APP=server.py
source env/bin/activate
```

## MariaDB/MySQL

Proceed to follow instructions to setup MariaDB on your platform.   You may need to allow remote access if your analysis machine is different from your database, this usually involves setting the `bind-address` in MariaDB to `0.0.0.0` or commenting out that line.

Note that using MyISAM (vs. InnoDB) as the engine on a Raspberry PI/small virtual machine had a profound impact on performance, this may not be true on all platforms. To reduce memory footprint, the I found the following tweaks to MariaDB defaults to be helpful (`/etc/mysql/mariaBase.conf.d/50-server.cnf`):

```
[mysqld]
#
# * Azure Adjustments
#
performance_schema = off
key_buffer_size = 8M
query_cache_size = 1M
query-cache-limit = 1M
tmp_table_size = 1M
innodb_buffer_pool_size = 0
innodb_log_buffer_size = 64K
max_connections = 16
sort_buffer_size = 256M
read_buffer_size = 256K
read_rnd_buffer_size = 256K
join_buffer_size = 64K
thread_stack = 128K
...
```

Login to MariaDB as root user. Create the production database and optionally a development database (if you intend to run unit testing). Create the database user, according to the previously setup environmental variables (substitute in for `password` as appropriate).

```
DROP DATABASE if exists dota;
CREATE DATABASE dota;
CREATE DATABASE dota_dev;

CREATE USER 'dota'@'localhost' IDENTIFIED BY 'password1';
GRANT ALL PRIVILEGES ON dota.* TO 'dota'@'localhost';
GRANT ALL PRIVILEGES ON dota_dev.* TO 'dota'@'localhost';
```

Upgrade the database to the latest version. The project uses the `alembic` migration package for all changes to database structure. The database can always be re-created with the following steps:

```
$ python db_util.py --create
$ alembic upgrade head
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 921d6d16a9ee, revise fetch_win_rate
INFO  [alembic.runtime.migration] Running upgrade 921d6d16a9ee -> c71c3f058b8c, Add indices
...
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

Remove the `crontab` jobs and shutdown `supervisor`. Use `killall` to remove all running instances of python and Gunicorn under the standard user. Restart MariaDB/mySQL.

```
mysqldump --compact --compress --opt --databases dota -u dota -p | gzip > backup.sql.gz &
```

# TODO

- Front-end
  
  - Format tweaks are needed to get proper display for mobile
  - Change long horizon health metrics to daily averages (vs. hourly)
  
- Back-end
  - Why is DOTA2 API throughput so variable? I've also noticed some cases where the most recent match was days ago. I suspect not every call to fetch matches is going against the most current data?
  - Check logs and /errors for malformed responses I continue be getting from the API -- Grep "ERROR" and "Traceback" in production logs.
  - Recheck filtering on fetch that it is accurate and what is desired. Add appropriate unit testing.
  - Look for anywhere the "timestamp()" datetime call is being used, it is likely the time is being localized incorrectly in these spots.
  
- New Features

  - Implement hero bitmasking and ability to search matches based on hero. Bitmasking might be slow, instead some sort of hero/match ID table might be needed with appropriate indexing on hero.
  - Implement win rate by position database write and modify front-end to display.
  - Protobuf: Include new fields for modeled roles (based on probability model), include GPM, match duration, and other useful information which might be needed for future analytics. Include player IDs for future work to model skill level based on match statistics.
  
- Data Analysis / Modeling

  - `generate_prior.py`: Add command line arguments and modify to work using dates instead of record counts.
  - `winrate_position.py`: Add command line arguments and ability to write to new database table. CLI arguments should include a date range. Add appropriate unit testing.
  - `win_analysis` needs to be extended to include hero vs. enemy good/bad match-ups. This is currently waiting on bit masking for heroes as each hero will need to be done independently due to memory constraints.
    - Is the 2nd order upper triangular style analysis even needed once we go to a per-hero model? If not, modify this document and edit `dotautil.py` to remove unused functions.

  