# Initial setup

First setup the following environmental variables:
- AWS_ACCESS
- AWS_SECRET (Use Secret if in Openshift)
- DOTA_MATCH_TABLE
- STEAM_KEY

init_tables.py will re-initialize the tables

# Setup of OpenShift locally

Use VirtualBox and minishift to create a local developer copy:

minishift start --vm-driver virtualbox

Logon as the same user to get persistance (e.g. "openshift")

In addition to the above, need to set the variable APP_FILE to
"fetch.py".