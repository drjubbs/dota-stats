import time
import argparse
from dateutil import parser
import bs4
import requests
import pandas as pd
import odutil

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36  (" \
             "KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"


def fix_hero_name(hname):
    """Small utility function to normalize hero names between databases"""
    return hname.lower().replace(" ", "_").replace("'", "")


# -----------------------------------------------------------------------------
# DotaBuff Parsing
# -----------------------------------------------------------------------------


def parse_match_summary(txt):
    """Parse a single page of match summary data from Dotabuff.
    Returns a dataframe summarizing matches
    """
    
    soup = bs4.BeautifulSoup(txt, "html.parser")

    # Find the match table
    div_filter = soup.find("div", {"class": "filter"})
    th = None
    for th in div_filter.parent.find_all("th"):
        if th.contents[0] == "Hero":
            break
    match_body = th.parent.parent.parent.find("tbody")

    hero = []
    match = []
    win = []
    timestamp = []
    ranked = []

    for tr in match_body.find_all("tr"):        
        tds = tr.find_all("td")    

        # Hero and match
        a_hero = tds[1].find("a")
        hero.append(a_hero.contents[0])
        match.append(a_hero['href'].split("/")[-1])

        # Win/loss
        win_txt = tds[3].find("a").contents[0].split(" ")[0].upper()
        if win_txt == "WON":
            win.append(1)
        else:
            win.append(0)

        # Timestamp
        this_ts = parser.parse(tds[3].find("time").get('datetime'))
        timestamp.append(this_ts)

        # Custom games have an extra tag element, these should be
        # flagged as unranked
        if tds[4].contents[0].__class__ == bs4.element.Tag:
            ranked.append(0)
        elif tds[4].contents[0].upper() == "RANKED":
            ranked.append(1)
        else:
            ranked.append(0)
            
    hero = [fix_hero_name(t) for t in hero]
            
    # Create dataframe
    df_summary = pd.DataFrame({
        'time': timestamp,
        'hero': hero,
        'match': match,
        'win': win,
        'ranked': ranked,
    })
    
    return df_summary, sum(df_summary["ranked"])
        

def process_player(pid, num_matches):
    """Use DotaBuff to return ranked match information for a player (pid).
    Returns approximately MATCHES results.
    """

    matches = 0
    page = 1
    summary = []
    df_summary = None

    while matches <= num_matches:
        headers = {"User-Agent": USER_AGENT}
        db_url = r"https://www.dotabuff.com/players/{0}/matches?enhance" \
                 r"=overview&page={1}".format(pid, page)
        r = requests.get(db_url, headers=headers)
        df_page, page_matches = parse_match_summary(r.content)

        summary.append(df_page)

        # Concatenate and take only ranked matches
        df_summary = pd.concat(summary)
        df_summary = df_summary[df_summary['ranked'] == 1]

        matches = len(df_summary)
        print("DotaBuff Page {0} Ranked Matches {1} of {2}".
              format(page, matches, num_matches))
        page += 1
        time.sleep(1)

    # Trim to the number of matches requested and sort
    df_summary = df_summary[0:num_matches]

    return df_summary


# -----------------------------------------------------------------------------
# OpenDota Functions
# -----------------------------------------------------------------------------

def parse_teamtable(teamtable):
    """Parse OpenDota `teamtable` and return dictionary of heroes
    and party status.
    """
    hero_party = {}    
    tt_tbody = teamtable.find("tbody")
    for row in tt_tbody.find_all("tr"):
        img = row.find("td").find("img")
        if img is not None:
            hero = fix_hero_name(img['data-for'])
            party_flag = img.parent.parent.find("div", {"class": "party"})
            if party_flag is not None:
                hero_party[hero] = 1
            else:
                hero_party[hero] = 0

    return hero_party


def get_party_info_for_match(this_od, match_id):
    """For a given match_id, use OpenData to return dictionary
    encoding party status for each hero in the match.
    """
    soup3 = this_od.get_match(match_id)

    radiant = soup3.find("div", {"class": "teamtable-radiant"})
    dire = soup3.find("div", {"class": "teamtable-dire"})

    combined_dict = {**parse_teamtable(radiant), **parse_teamtable(dire)}
    
    return combined_dict

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------


def main(player_id, num_matches, current_mmr):
    """Main program execution"""

    # Command line


    # DotaBuff
    df_matches = process_player(player_id, num_matches)
    print(len(df_matches))
    this_od = odutil.OpenDota()

    party_status = []
    for idx, row in df_matches.iterrows():
        hero_dict = get_party_info_for_match(this_od, row.match)
        party_status.append(hero_dict[row.hero])

    df_matches['party'] = party_status

    mmr = [current_mmr]
    for idx, row in df_matches.iloc[:-1, :].iterrows():
        if row.party == 1:
            delta = 20
        else:
            delta = 30
        if row.win == 1:
            mmr.append(mmr[-1]-delta)
        else:
            mmr.append(mmr[-1]+delta)
    df_matches['mmr'] = mmr

    # Sort and output to disk
    df_matches = df_matches.sort_values(by='time')
    print("Writing to: {}.csv".format(player_id))
    df_matches.to_csv("{}.csv".format(player_id))


if __name__ == "__main__":
    aparser = argparse.ArgumentParser(
        description="Dota 2MMR back calculation for charting")
    aparser.add_argument("player_id", type=int,
                        help="Steam ID to fetch data for")
    aparser.add_argument("num_matches", type=int,
                        help="Number of historical matches to fetch")
    aparser.add_argument("current_mmr", type=int,
                        help="Current MMR")
    opts = aparser.parse_args()
    print("Fetching {0} matches for ID {1}, mmr = {2}".format(
        opts.num_matches,
        opts.player_id,
        opts.current_mmr,
    ))

    main(opts.player_id, opts.num_matches, opts.current_mmr)
