# Initial setup

First setup the following environmental variables:
- AWS_ACCESS
- AWS_SECRET (Use Secret if in Openshift)
- DOTA_MATCH_TABLE
- STEAM_KEY
- WORKFLOW_DB (Set to location for persistent sqlite3 DB)
- APP_FILE (set to fetch.py or main entry point)

init_tables.py will re-initialize the tables

# TODO

Need to parameterize AWS Region in aws.py

# Setup of OpenShift locally

Use VirtualBox and minishift to create a local developer copy:

minishift start --vm-driver virtualbox

Logon as the same user to get persistance (e.g. "openshift")

In addition to the above, need to set the variable APP_FILE to
"fetch.py".