# TODO
- Re-enable protobuf writes (currently disabled), try storing in SQLite database
  instead of cloud solution
- Unless there is an HTML fetch error, track all match IDs... no reason to
  revisit a match ID which was already rejected. 
- Implement MatchID vs. time model to sample matches randomly vs. going in hero 
  order, this way popularity is capturely appropriately.
- Additional testing of code with summoned units which can have items (e.g. 
  Lone Druid)
- Check for duplicates before writing key to NoSQL, this can cause the 
  local statistics database to be off and be resilient through crashes.
- Make sure filtering on fetch is accurate and what is desired.

# General Raspberry Pi Setup
* `pip install -i requiremnents.txt`
* Setup `.ssh/authorized_keys`, note that Putty public key must be one line and 
  begin with ssh-rsa
* vim: `/usr/share/vim/vim81/defaults.vim` -- remove `set mouse=a`
* Non-obvious packages to get things working:
  - `sudo apt-get install libatlas-base-dev`
* In  `.bashrc`, set the following:

```bash
export STEAM_KEY=1234567890....
export DOTA_SQL_STATS_FILE=/matches.db
export DOTA_SQL_STATS_TABLE=dota_stats
```
