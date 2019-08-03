# Todo
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
* In  `.bashrc`, `export STEAM_KEY=1234567890....`
