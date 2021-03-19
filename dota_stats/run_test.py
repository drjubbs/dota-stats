# -*- coding: utf-8 -*-
"""Unit testing for dota-stats"""
import unittest
import logging
import os
import json
import numpy as np
import pandas as pd
import fetch
from dota_stats import meta, db_util, win_rate_pick_rate, dotautil, \
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


class TestDBUtil(unittest.TestCase):
    """Parent class for testing functionality which requries database
    connectivity."""

    @classmethod
    def setUpClass(cls):
        """Setup database for testing"""

        # Bail if we're not in development...
        if os.environ['DOTA_MONGO_DB'] != "dotadev":
            raise NotImplementedError("Must be on development environment!")

        # Create and upgrade database
        db_util.create_database()

        cls.mongo_db = db_util.connect_mongo()

        # Populate tables
        filename = os.path.join("testing", "mongo_test_db.json")
        with open(filename, "r") as filehandle:
            db_txt = json.loads(filehandle.read())

        cls.mongo_db.matches.insert_many(db_txt)
        win_rate_pick_rate.main(1, 3)

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

        # No matches on a 10 day window relative to max time
        rec_matches, rec_winrate = db_util.purge_database(10, utc=False)
        self.assertEqual(rec_matches, 0)

        # Four matches on a zero day window
        rec_matches, rec_winrate = db_util.purge_database(-1, utc=False)
        self.assertEqual(rec_matches, 4)
        self.assertTrue(rec_winrate, meta.NUM_HEROES * 24)

    def tearDown(self):
        pass


class TestWinRatePickRate(TestDBUtil):
    """Test code to calculate win rate vs. pick rate tables"""

    def test_win_rate_pick_rate(self):
        """Test code to calculate win rate vs. pick rate tables"""

        win_rate_pick_rate.main(days=1, skill=3)
        df_out = win_rate_pick_rate.get_current_win_rate_table(1)

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
        self.assertEqual(
            df_out[df_out['hero'] == 'anti-mage']['radiant_win'].values[0],
            3
        )

        self.assertEqual(
            df_out[df_out['hero'] == 'anti-mage']['dire_win'].values[0],
            0
        )

        self.assertEqual(
            df_out[df_out['hero'] == 'shadow-fiend']['radiant_win'].values[0],
            2
        )

        self.assertEqual(
            df_out[df_out['hero'] == 'silencer']['radiant_win'].values[0],
            1
        )


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


class TestFetch(TestDBUtil):
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
        item_dict = json.loads(parsed_match['items'])
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

    def test_dummy_matches(self):
        """Test dummy matches"""

        rows = self.session.query(db_util.Match).all()
        radiant = [json.loads(t.radiant_heroes) for t in rows]
        dire = [json.loads(t.dire_heroes) for t in rows]

        # There should be an anti-mage in each game
        antimage = sum([1 in t for t in radiant]) + sum([1 in t for t in dire])
        self.assertEqual(antimage, 6)

    def test_orm_writes(self):
        """ Write some matches and test using ORM """

        with open("./testing/write_match.json") as filename:
            match = json.loads(filename.read())

        match = fetch.parse_match(match)
        match_id = match['match_id']
        fetch.write_matches(self.session, [match])

        match_read = self.session.query(db_util.Match). \
            filter(db_util.Match.match_id == match_id).first()

        self.assertEqual(match_read.match_id, match['match_id'])
        self.assertEqual(json.loads(match_read.radiant_heroes),
                         match['radiant_heroes'])
        self.assertEqual(json.loads(match_read.dire_heroes),
                         match['dire_heroes'])


class TestFetchSummary(unittest.TestCase):
    """Testing of methods related to fetch statistics"""

    def test_get_health_summary(self):
        """Check service health"""

        df1, _ = fetch_summary.get_health_summary(
            30, 'US/Eastern', hour=False)
        df2, _ = fetch_summary.get_health_summary(
            3, 'US/Eastern', hour=True)

        mask = (df1.sum() >= df2.sum())
        self.assertTrue(mask.all())


class TestWinRatePosition(TestDBUtil):
    """Test cases for winrate by position probability model"""

    def test_winrate_position(self):
        """Test assignment of heroes to positions and winrates"""

        rows = []
        for match in self.session.query(db_util.Match).all():
            rows.append((
                match.match_id,
                match.radiant_heroes,
                match.dire_heroes,
                match.radiant_win
            ))

        hml = win_rate_position.HeroMaxLikelihood(
            os.path.join("analytics", "prior_final.json"))
        total_win_mat, total_count_mat = hml.matches_to_summary(rows)

        # 6 matches * 5 heroes, 1 winning each game = 30 wins, 60 total
        self.assertEqual(np.sum(total_win_mat), 30.0)
        self.assertEqual(np.sum(total_count_mat), 60.0)

        # Drow in three matches, 3 wins
        drow_id = meta.REVERSE_HERO_DICT['drow-ranger']
        drow_idx = meta.HEROES.index(drow_id)

        self.assertEqual(total_win_mat[drow_idx, :].sum(), 3)
        self.assertEqual(total_count_mat[drow_idx, :].sum(), 3)

        # Anti-mage in all, 2 wins
        am_id = meta.REVERSE_HERO_DICT['anti-mage']
        am_idx = meta.HEROES.index(am_id)

        self.assertEqual(total_win_mat[am_idx, :].sum(), 2)
        self.assertEqual(total_count_mat[am_idx, :].sum(), 6)

        # dazzle, mirana, mars, zeus, phantom-assassin
        max_h, _ = hml.find_max_likelihood([50, 9, 129, 22, 44])
        self.assertEqual(max_h, [44, 22, 129, 9, 50])


if __name__ == '__main__':
    fetch.log.setLevel(logging.CRITICAL)
    win_rate_pick_rate.log.setLevel(logging.CRITICAL)
    unittest.main()
