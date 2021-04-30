# -*- coding: utf-8 -*-
"""Unit testing for dota-stats"""
import unittest
import logging
import os
import json
import datetime as dt
import numpy as np
import fetch
import fetch_summary
from dota_stats import meta, db_util, db_tools, win_rate_pick_rate, dotautil, \
    win_rate_position

# Globals
BIGINT = 9223372036854775808  # Max bitmask
DUMP_BUG = None  # Set to none for no dump


class TestDumpBug(unittest.TestCase):
    """Use this class to dump a problematic match JSON for additional testing
    JSON is stored into the testing directory.

        python run_test.py TestDumpBug
    """

    def test_fetch_debug(self):
        """Dump problematic API result to JSON"""
        if DUMP_BUG is None:
            return

        match_id = str(DUMP_BUG)
        match = fetch.fetch_match(match_id, 0)
        with open("./testing/{}.json".format(match_id), "w") as filename:
            filename.write(json.dumps(match, indent=4))
            self.assertTrue(match is not None)


class TestDB(unittest.TestCase):
    """Parent class for testing functionality which requries database
    connectivity."""

    @classmethod
    def setUpClass(cls):
        """Setup database for testing"""
        # Bail if we're not in development...
        if os.environ['DOTA_MONGO_DB'] != "dotadev":
            raise NotImplementedError("Must be on development environment!")

        # Create and upgrade database
        db_tools.create_database()

        cls.mongo_db = db_util.connect_mongo()

        # Populate tables
        filename = os.path.join("testing", "mongo_test_db.json")
        with open(filename, "r") as filehandle:
            db_txt = json.loads(filehandle.read())

        cls.mongo_db.matches.insert_many(db_txt)

    def tearDown(self):
        pass


class TestDBUtil(TestDB):
    """Check basic database functions in `db_util.py`"""

    def test_load(self):
        """Check that the database loaded the number of records in the
        JSON test database."""
        self.assertEqual(self.mongo_db.matches.count_documents({}), 4)

    def test_get_max_start_time(self):
        """Find the most recent match in the database"""
        max_time = db_util.get_max_start_time()
        self.assertTrue(max_time, 1615990847)

    def test_purge_database(self):
        """Clear out the database"""

        # Create the win rate / pick rate records to check if they
        # are purged properly
        win_rate_pick_rate.main(1, 1)
        win_rate_pick_rate.main(1, 2)
        win_rate_pick_rate.main(1, 3)

        # No matches on a 10 day window relative to max time
        rec_matches, rec_winrate = db_tools.purge_database(
            10, use_current_time=False)
        self.assertEqual(rec_matches, 0)

        # Four matches on a zero day window
        rec_matches, rec_winrate = db_tools.purge_database(
            -1, use_current_time=False)
        self.assertEqual(rec_matches, 4)
        # Should have one record for each hero, 24 hours, 3 skill levels
        self.assertEqual(rec_winrate, meta.NUM_HEROES * 24 * 3)


class TestWinRatePickRate(TestDB):
    """Test code to calculate win rate vs. pick rate tables"""

    def test_win_rate_pick_rate(self):
        """Test code to calculate win rate vs. pick rate tables"""
        mongo_db = db_util.connect_mongo()
        win_rate_pick_rate.main(days=2, skill=3)
        df_out = win_rate_pick_rate.get_current_win_rate_table(mongo_db, 1)

        # Integrity checks
        summary = df_out.sum()
        self.assertEqual(
            summary['radiant_win'] + summary['dire_win'],
            4 * 5)
        self.assertEqual(summary['radiant_total'], summary['dire_total'])
        self.assertEqual(
            4 * 5 + 4 * 5,
            sum(df_out[['radiant_total', 'dire_total']].sum(axis=1)))

        # Individual heroes
        mask = df_out['hero_skill'] == 'ANTI-MAGE_3'
        self.assertEqual(df_out[mask]['radiant_win'].values[0], 3)
        self.assertEqual(df_out[mask]['dire_win'].values[0], 0)

        mask = df_out['hero_skill'] == 'SHADOW-FIEND_3'
        self.assertEqual(df_out[mask]['radiant_win'].values[0], 2)

        # We should only have skill level 3 in test database
        mask = df_out['hero_skill'] == 'ANTI-MAGE_1'
        self.assertEqual(df_out[mask]['total'].values[0], 0)
        mask = df_out['hero_skill'] == 'ANTI-MAGE_2'
        self.assertEqual(df_out[mask]['total'].values[0], 0)


class TestDotaUtil(unittest.TestCase):
    """Test utility functions in DotaUtil"""

    def test_get_hour_blocks(self):
        """Given `timestamp`, return list of begin and end times on the near
        hour going back `hours` from the timestamp."""
        text, begin, end = dotautil.TimeMethods.get_hour_blocks(1609251250, 11)

        self.assertEqual(begin[0], 1609250400)
        self.assertEqual(end[0], 1609254000)

        self.assertEqual(text[0], "20201229_1400")
        self.assertEqual(text[-1], "20201229_0400")

    def test_get_time_nearest(self):
        """Check rounding of timestamps"""

        hour = dotautil.TimeMethods.get_time_nearest(1609251250)
        day = dotautil.TimeMethods.get_time_nearest(1609251250, False)

        self.assertEqual(hour[0], 1609250400)
        self.assertEqual(day[0], 1609200000)


class TestFetch(TestDB):
    """Test routines in the main fetch.py logic"""

    def test_bad_api_key(self):
        """Bad API Key"""

        old_key = os.environ["STEAM_KEY"]
        os.environ["STEAM_KEY"] = "AAAAA"
        with self.assertRaises(fetch.APIException) as context:
            _ = fetch.fetch_match(111, 1)

        self.assertEqual(str(context.exception),
                         'Forbidden - Check Steam API key')
        os.environ["STEAM_KEY"] = old_key

    def test_bad_match_id(self):
        """Bad Match ID"""

        with self.assertRaises(fetch.APIException) as context:
            _ = fetch.fetch_match(111, 1)
        self.assertEqual(str(context.exception), 'Match ID not found')

    def test_feeding_bit_detection(self):
        """Check feeding/bot detection"""

        with open("./testing/bots.json") as filename:
            match = json.loads(filename.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__() == 'Feeding')

    def test_backpack(self):
        """Check that items in backpack are registered as valid. In this
        match Jugg had phase boots in backpack"""

        with open("./testing/backpack.json") as filename:
            match = json.loads(filename.read())
        parsed_match = fetch.parse_match(match)
        item_dict = parsed_match['items']
        jugg = item_dict[str(meta.REVERSE_HERO_DICT['juggernaut'])]
        self.assertTrue(meta.ITEMS['phase_boots']['id'] in jugg)

        # Test no items detection
        file_handle = open("./testing/no_items.json")
        txt = file_handle.read()
        match = json.loads(txt)
        file_handle.close()

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__() == 'No items')

    def test_null_hero(self):
        """Test null hero"""
        with open("./testing/null_hero.json") as filename:
            match = json.loads(filename.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__() == 'Null Hero ID')

    def test_write_matches(self):
        """ Write some matches and test using ORM """

        with open("./testing/write_match.json") as filename:
            match = json.loads(filename.read())

        match = fetch.parse_match(match)
        match_id = match['match_id']

        fetch.write_matches(self.mongo_db, [match])

        match_read = self.mongo_db.matches.find(
            {"match_id": {"$eq": match_id}})[0]

        self.assertEqual(match_read['match_id'], match['match_id'])
        self.assertEqual(match_read['radiant_heroes'], match['radiant_heroes'])
        self.assertEqual(match_read['dire_heroes'], match['dire_heroes'])


class TestFetchSummary(TestDB):
    """Testing of methods related to fetch statistics"""

    def test_main(self):
        """Create the database table and check record count"""
        fetch_summary.main(10, use_current_time=False)
        mongo_db = db_util.connect_mongo()

        # 2 matches at this hour
        query = {"_id": "1615730400_3"}
        results = mongo_db.fetch_summary.find(query)

        self.assertTrue(
            results[0]['rec_count'], 2
        )

        # Two matches at this hour
        query = {"_id": "1615726800_3"}
        results = mongo_db.fetch_summary.find(query)

        self.assertTrue(
            results[0]['rec_count'], 2
        )

    def test_get_health_summary(self):
        """Checks on report for service health (records per hour/day)"""

        # Check creation of blank dataframe, hourly
        start = dt.datetime(2020, 7, 23, 1, 20, 30)
        blank, begin, _ = fetch_summary.get_blank_time_summary(
            days=5, hour=True, start=start)
        self.assertEqual(len(blank), 120)
        self.assertEqual(blank.index[0], '2020-07-23T01:00:00')
        # Begin: GMT: Saturday, July 18, 2020 2:00:00 AM
        self.assertEqual(begin, 1595037600)

        # Check creation of blank dataframe, daily
        blank, begin, _ = fetch_summary.get_blank_time_summary(
            days=5, hour=False, start=start)

        self.assertEqual(len(blank), 5)
        self.assertEqual(blank.index[0], '2020-07-23T00:00:00')

        # Begin: GMT: Saturday, July 18, 2020 12:00:00 AM
        self.assertTrue(begin, 1595034000)

        mongo_db = db_util.connect_mongo()

        # From the database, 4 matches...
        # 1615731621 Sunday, March 14, 2021 2:20:21 PM
        # 1615731630 Sunday, March 14, 2021 2:20:30 PM
        # 1615728046 Sunday, March 14, 2021 1:20:46 PM
        # 1615630847 Saturday, March 13, 2021 10:20:47 AM
        fetch_summary.main(days = 5, use_current_time=False)

        # Check hourly fetch...
        df1 = fetch_summary.get_health_summary(
            mongo_db, days=3, hour=True, use_current_time=False)

        self.assertEqual(df1.loc['2021-03-14T14:00:00']['very_high'], 2)
        self.assertEqual(df1.loc['2021-03-14T13:00:00']['very_high'], 1)
        self.assertEqual(df1.loc['2021-03-13T10:00:00']['very_high'], 1)
        self.assertEqual(len(df1), 3 * 24)

        # Check daily fetch
        df2 = fetch_summary.get_health_summary(
            mongo_db, days=3, hour=False, use_current_time=False)
        self.assertEqual(df2.loc['2021-03-14T00:00:00']['very_high'], 3)
        self.assertEqual(df2.loc['2021-03-13T00:00:00']['very_high'], 1)



class TestWinRatePosition(TestDB):
    """Test cases for winrate by position probability model"""

    def test_winrate_position(self):
        """Test assignment of heroes to positions and winrates"""

        mongo_db = db_util.connect_mongo()
        matches = mongo_db.matches.find({})

        rows = []
        for match in matches:
            rows.append((
                match['match_id'],
                match['radiant_heroes'],
                match['dire_heroes'],
                match['radiant_win'],
            ))

        hml = win_rate_position.HeroMaxLikelihood(
            os.path.join("analytics", "prior_final.json"))
        total_win_mat, total_count_mat = hml.matches_to_summary(rows)

        # 4 matches * 5 heroes, 1 winning each game = 20 wins, 40 total
        self.assertEqual(np.sum(total_win_mat), 20.0)
        self.assertEqual(np.sum(total_count_mat), 40.0)

        ww_id = meta.REVERSE_HERO_DICT['winter-wyvern']
        ww_idx = meta.HEROES.index(ww_id)

        self.assertEqual(total_win_mat[ww_idx, :].sum(), 2)
        self.assertEqual(total_count_mat[ww_idx, :].sum(), 2)

        # Anti-mage in all, 2 wins
        am_id = meta.REVERSE_HERO_DICT['anti-mage']
        am_idx = meta.HEROES.index(am_id)

        self.assertEqual(total_win_mat[am_idx, :].sum(), 3)
        self.assertEqual(total_count_mat[am_idx, :].sum(), 4)

        # dazzle, mirana, mars, zeus, phantom-assassin
        max_h, _ = hml.find_max_likelihood([50, 9, 129, 22, 44])
        self.assertEqual(max_h, [44, 22, 129, 9, 50])


if __name__ == '__main__':
    # Supress output
    fetch.log.setLevel(logging.CRITICAL)
    win_rate_pick_rate.log.setLevel(logging.CRITICAL)
    db_tools.log.setLevel(logging.CRITICAL)
    fetch_summary.log.setLevel(logging.CRITICAL)

    unittest.main()
