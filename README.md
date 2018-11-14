# Todo

- Implement MatchID vs. time model to sample matches randomly vs. going in hero 
  order, this way popularity is capturely appropriately.
- Additional testing of code with summoned units which can have items (e.g. 
  Lone Druid)
- Check for duplicates before writing key to DynamoDB, this can cause the 
  local statistics database to be off and be resilient through crashes.
- Make sure filtering on fetch is accurate and what is desired.

# MariaDB Setup

Create an instance of MariaDB with a strong root password. This can 
either be local in an a Pod if using Openshift.

Setup the dota user and create the default database, either through
the MariaDB CLI or using container configurations.

## On local machine
mysql -u root -p
CREATE DATABASE 'dota';
CREATE USER 'dota'@'localhost' IDENTIFIED BY <password>;
GRANT ALL PRIVILEGES ON dota.* TO 'dota'@'localhost';
FLUSH PRIVILEGES;

## Windows
mysql -u %DOTA_SQL_USER% -p%DOTA_SQL_PASS% %DOTA_SQL_DB%
CREATE TABLE IF NOT EXISTS stats (batch_time INT, updated_epoch INT, fetch_num INT, pair INT) ENGINE=INNODB;

## RSH onto OpenShift:
mysql -u $MYSQL_USER -p$MYSQL_PASSWORD -h $HOSTNAME $MYSQL_DATABASE
CREATE TABLE IF NOT EXISTS stats (batch_time INT, updated_epoch INT, fetch_num INT, pair INT) ENGINE=INNODB;

# Run configuration Setup

Setup the following environmental deploy variables for fetch (OpenShift):

- APP_FILE ["/opt/app-root/src/fetch/fetch.py"]

Setup the following environmental deploy variables for flask (OpenShift):

- APP_MODULE ["monitor.server:app"]

Setup the following build variables (OpenShift):

- UPGRADE_PIP_TO_LATEST ["True"]

Setup the following environmental variables for this workflow:

- AWS_ACCESS
- AWS_SECRET (Use Secret if in Openshift)
- DOTA_MATCH_TABLE
- STEAM_KEY
- DOTA_SQL_DB       ["dota"]
- DOTA_SQL_HOST     ["127.0.0.1" for local, service name if in openshift]
- DOTA_SQL_PASS     [<password>]
- DOTA_SQL_ROOT_PW  [<password>]
- DOTA_SQL_TABLE    ["stats"]
- DOTA_SQL_USER     ["dota"]




init_tables.py will re-initialize the tables

# TODO
- Rename env variables to all start with "DOTA_"
- Need to parameterize AWS Region in aws.py
- In init_tables, first dump environmental variables and make user give a command
  line arg to proceed with a warning of data loss
- init_tables: format strings need to get replaced with SQL parameters...

# Setup of OpenShift locally

Use VirtualBox and minishift to create a local developer copy:

minishift start --vm-driver virtualbox

Logon as the same user to get persistance (e.g. "openshift")

In addition to the above, need to set the variable APP_FILE to
"fetch.py".
7wt15g0V2JXNvvLBR7ogLwl7
