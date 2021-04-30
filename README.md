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

```bash
cd dota-stats
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -i requirements.txt
```

I have found it helpful to use small utility shell script(s), which also sets environmental variables the setup and program will need. `PYTHONPATH` should be set properly so the package operates correctly.

```
$ cat 'env.sh'
export STEAM_KEY=0D3D2....
export DOTA_DB_URI=mysql://dota:password@localhost/dota
export DOTA_LOGGING=0
export DOTA_THREADS=8
export FLASK_APP=server.py
export PYTHONPATH=$PYTHONPATH:$HOME/dota-stats

source dota-stats/env/bin/activate
```

You can check this setup:

```
(env)$ python
Python 3.7.3 (default, Jul 25 2020, 13:03:44)
>>> from dota_stats import meta
>>> meta.NUM_HEROES
120
```



## 

Create the admin user:

```
mongo --port 27017

use admin
db.createUser(
  {
    user: "admin",
    pwd: "password1",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" }, "readWriteAnyDatabase" ]
  }
)
quit()
```

Edit the configuration to use authentication and restart the service (uncomment the line `auth = True`. If desired, change the location of the storage for easy of backup **TODO: Check to see this actually contains enough for a proper backup**.

```
$ sudo vim /etc/mongodb.conf
$ sudo systemctl restart mongodb
```

Log back on as admin and create a new database and user:

```
$ mongo --port 27017  --authenticationDatabase "admin" -u "admin" -p
use dota
db.createUser(
  {
    user: "dota",
    pwd:  "password2",
    roles: [ { role: "readWrite", db: "dota" } ]

  }
)
use dotadev
db.createUser(
  {
    user: "dotadev",
    pwd:  "password3",
    roles: [ { role: "readWrite", db: "dotadev" } ]

  }
)
```

## Automation/Crontab

Next create a basic shell script (`fetch.sh`) which activates the virtual environment and runs the scripts with the required options. 

```
#!/bin/bash
source env_prod.sh
cd dota-stats/dota_stats
mkdir -p log

export DATESTR=`date +"%Y%m%d_%H%M"`
for SKILL in 1 2 3;
do
        python fetch.py all $SKILL &>> log/fetch_$DATESTR.log
        python fetch_summary.py 3 &>> log/fetch_$DATESTR.log
        python win_rate_pick_rate.py 3 $SKILL &>> log/fetch_$DATESTR.log
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

## Regenerating Priors

The script `analytics/generate_priors.py` rebuilds the files `prior_final.csv` and `prior_final.json` using recent match history and lane presence from Dotabuff (see description above). Prior to running this script, `prior_mask.csv` must be updated to include new or renamed heroes. The code will issues warnings if there is a mismatch.

## Database Backup

Remove the `crontab` jobs and shutdown `supervisor`. Use `killall` to remove all running instances of python and Gunicorn under the standard user. Restart MariaDB/mySQL.

```
mysqldump --compact --compress --opt --databases dota -u dota -p | gzip > backup.sql.gz
```

# TODO

- `win_rate_position.py`
  - Finish implementation, add to "fetch loop"
- `matchups.py` 
  - Unit testing and write results to database
- MongoDB Migration
  
  - When run in a crontab, getting timeout errors, why?
  - Do a time comparison of a complete run, mariadb vs. mongodb
  - Update environment / `env.sh` scripts in this document
  - Check to see if bot matches are still flooding the fetch (look for heroes with few records written)
- Front-end
  - Completely broken, split into 3 different pages and make charts work on mobile if possible.
- Back-end

  - Why is DOTA2 API throughput so variable? I've also noticed some cases where the most recent match was days ago. I suspect not every call to fetch matches is going against the most current data, do some experimentation.
  - Check logs and /errors for malformed responses I continue be getting from the API -- Grep "ERROR" and "Traceback" in production logs.
  - Recheck filtering on fetch that it is accurate and what is desired. Add appropriate unit testing.
  - Look for anywhere the "timestamp()" datetime call is being used, it is likely the time is being localized incorrectly in these spots.
  - Add new table for hero match-ups to easily index and find specific match-ups (e.g. Lycan vs. TA)
- Analysis / Modeling
  - `generate_prior.py`: Add command line arguments and modify to work using dates instead of record counts
