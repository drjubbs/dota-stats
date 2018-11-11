WHERE I LEFT OFF:
- Did not get MariaDB running on OpenShift, need to modify to use "host"
  parameter and create table using interactive shell.

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
CREATE TABLE IF NOT EXISTS dota (batch_time INT, updated_epoch INT, fetch_num INT, pair INT) ENGINE=INNODB;

## RSH onto OpenShift:
mysql -u $MYSQL_USER -p$MYSQL_PASSWORD -h $HOSTNAME $MYSQL_DATABASE
CREATE TABLE IF NOT EXISTS dota (batch_time INT, updated_epoch INT, fetch_num INT, pair INT) ENGINE=INNODB;

# Run configuration Setup

Setup the following environmental variables (OpenShift):

- APP_FILE ["fetch.py"]
- UPGRADE_PIP_TO_LATEST ["True"]

Setup the following environmental variables for this workflow:

- AWS_ACCESS
- AWS_SECRET (Use Secret if in Openshift)
- DOTA_MATCH_TABLE
- STEAM_KEY
- DOTA_SQL_USER     ["dota"]
- DOTA_SQL_PASS     [<password>]
- DOTA_SQL_DB       ["dota"]
- DOTA_SQL_TABLE    ["stats"]
- DOTA_SQL_HOST     ["127.0.0.1" for local, service name if in openshift]



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
