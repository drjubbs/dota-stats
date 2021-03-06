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
    fetch_summary, win_rate_position

# Globals
BIGINT = 9223372036854775808    # Max bitmask
DUMP_BUG = None                 # Set to none for no dump


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
        if os.environ['DOTA_DB_URI'].split("/")[-1] != "dota_dev":
            raise NotImplementedError("Must be on development environment!")

        # Create and upgrade database
        db_util.create_database()
        os.system("alembic upgrade head >/dev/null 2>&1")

        cls.engine, cls.session = db_util.connect_database()

        # Populate tables
        filename = os.path.join("testing", "test_database.txt")
        with open(filename, "r") as filehandle:
            db_txt = filehandle.read()

        conn = cls.engine.connect()
        for stmt in db_txt.split("\n"):
            conn.execute(stmt)

    def test_dummy(self):
        """Dummy routine to ensure class setUp and tearDown are called.
        This will eventually contain code which tests the upgrade prcoess.
        process.
        """
        self.assertEqual(1, 1)

    def tearDown(self):
        self.session.close()


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

        match_read = self.session.query(db_util.Match).\
            filter(db_util.Match.match_id == match_id).first()

        self.assertEqual(match_read.match_id, match['match_id'])
        self.assertEqual(json.loads(match_read.radiant_heroes),
                         match['radiant_heroes'])
        self.assertEqual(json.loads(match_read.dire_heroes),
                         match['dire_heroes'])


class TestDBUtil(unittest.TestCase):
    """Test utility functions in DBUtil"""

    def test_get_hour_blocks(self):
        """Given `timestamp`, return list of begin and end times on the near
        hour going back `hours` from the timestamp."""
        text, begin, end = dotautil.TimeMethods.get_hour_blocks(1609251250, 11)

        self.assertEqual(text[0], "20201229_1400")
        self.assertEqual(text[-1], "20201229_0400")
        self.assertEqual(end[0], 1609250400)
        self.assertEqual(begin[-1], 1609210800)


class TestWinRatePickRate(TestDB):
    """Test code to calculate win rate vs. pick rate tables"""

    def test_win_rate_pick_rate(self):
        """Test code to calculate win rate vs. pick rate tables"""

        win_rate_pick_rate.main(days=1, skill=1)

        engine, _ = db_util.connect_database()
        stmt = "select * from dota_hero_win_rate"

        df_out = pd.read_sql(stmt, engine)

        # Integrity checks
        summary = df_out.sum()
        self.assertEqual(
            summary['radiant_win'] + summary['dire_win'],
            25)
        self.assertEqual(summary['radiant_total'], summary['dire_total'])
        self.assertEqual(
            50,
            sum(df_out[['radiant_total', 'dire_total']].sum(axis=1)))


class TestMLEncoding(unittest.TestCase):
    """Test one-hot encoding for machine learning"""

    def setUp(self):
        test_heroes = [
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            [10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
            [57, 55, 58, 81, 27, 92, 63, 14, 89, 26],
            [84, 89, 43, 121, 57, 71, 63, 110, 34, 35],
            [121, 37, 93, 1, 12, 77, 92, 72, 98, 33],
            [96, 108, 73, 28, 58, 101, 52, 3, 94, 129],
            [121, 58, 51, 17, 81, 18, 67, 72, 68, 77],
            [120, 47, 34, 112, 19, 1, 90, 63, 9, 43],
            [58, 17, 52, 84, 7, 74, 3, 9, 16, 57],
            [69, 55, 89, 8, 46, 91, 53, 109, 85, 14]
        ]
        num_heroes = meta.NUM_HEROES

        rad_heroes = [t[0:5] for t in test_heroes]
        dire_heroes = [t[5:] for t in test_heroes]

        # First order matrix... this routine is vectorized over matches
        self.x1_test = dotautil.MLEncoding.first_order_vector(
            rad_heroes, dire_heroes)

        # Second order matrix is upper triangular, without the diagonal,
        # rolled out. This is whether or not a team/enemy hero pair exists
        self.x2_test = np.zeros([len(test_heroes), int(num_heroes*(
                num_heroes-1)/2)], dtype='b')

        # Loop over all 'fake matches' and flatten first and second order
        # matrices
        counter = 0
        for heroes in test_heroes:
            x2_mat = dotautil.MLEncoding.second_order_hmatrix(
                heroes[0:5], heroes[5:])
            self.x2_test[counter, :] = \
                dotautil.MLEncoding.flatten_second_order_upper(
                x2_mat)
            counter = counter+1

    def test_first_order_vector(self):
        """Test the first oder mapping """

        # Rows for first order encoding should sum to zero since
        # 1 and -1 are used for randiant/dire
        row_sum = np.array(self.x1_test.sum(axis=1))
        row_zero = np.zeros([len(row_sum), 1])
        self.assertTrue(np.all(row_sum == row_zero))

        # First half should sum to 5
        sum_radiant = self.x1_test[:, 0:meta.NUM_HEROES].sum(axis=1)
        sum_check = np.ones([len(sum_radiant), 1])*5
        self.assertTrue(np.all(sum_radiant == sum_check))

        # First half should sum to -5
        sum_dire = self.x1_test[:, meta.NUM_HEROES:2*meta.NUM_HEROES].sum(
            axis=1)
        sum_check = -1 * sum_check
        self.assertTrue(np.all(sum_dire == sum_check))

    def test_flatten_unflatten_second_order_upper(self):
        """Test the code which `unravels` a matrix into the upper
        triangular format without the diagonal.
        """
        simple = np.array([[0, 1, 2, 3, 4],
                           [0, 0, 5, 6, 7],
                           [0, 0, 0, 8, 9],
                           [0, 0, 0, 0, 10],
                           [0, 0, 0, 0, 0]])
        flat_a = dotautil.MLEncoding.flatten_second_order_upper(simple)
        flat_b = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        self.assertTrue(np.all(flat_a == flat_b))

        # When we unflatten, the upper triangle will be mirrored
        # and reflected over the diagonal which is still zero
        simple2_a = np.array([[0,   1,  2,   3,  4],
                              [-1,  0,  5,   6,  7],
                              [-2, -5,  0,   8,  9],
                              [-3, -6, -8,   0, 10],
                              [-4, -7, -9, -10,  0]
                              ])
        simple2_b = dotautil.MLEncoding.unflatten_second_order_upper(flat_a)
        self.assertTrue(np.all(simple2_a == simple2_b))

    def test_second_order_hmatrix(self):
        """Some basic integrity checks on x2. All columns should be between
        [-25,25] the first two rows are constructed to be 25 and -25
        respectively. The sign convention depends on whether or not the first
        hero in the pair (radiant-dire) falls below or above the diagonal.

        Each row is a match.
        """

        row_sum = self.x2_test.sum(axis=1)
        # Upper limit
        upper = (np.ones(self.x2_test.shape[0])*25).reshape(
            self.x2_test.shape[0], 1)
        # Lower limit
        lower = (np.ones(self.x2_test.shape[0])*-25).reshape(
            self.x2_test.shape[0], 1)

        self.assertEqual(row_sum[0], 25)
        self.assertEqual(row_sum[1], -25)
        self.assertTrue(np.all(row_sum <= upper))
        self.assertTrue(np.all(row_sum >= lower))

    def test_create_features(self):
        """Check of the higher level one-hot encoding function"""

        # Sample data
        rad = [[1, 22, 110, 33, 14],
               [71, 7, 1, 86, 59],
               [39, 107, 13, 98, 20],
               [119, 74, 1, 29, 128],
               [53, 128, 1, 50, 2]]

        dire = [[35, 128, 31, 60, 111],
                [10, 2, 70, 31, 83],
                [1, 35, 67, 42, 68],
                [84, 126, 64, 120, 54],
                [87, 76, 93, 29, 100]]

        wins = [1, 0, 1, 0, 1]

        _, _, _, x3_data = dotautil.MLEncoding.create_features(
            rad, dire, wins, verbose=False)

        # Convert to hero index from hero number
        rad_idx = []
        for row in rad:
            rad_idx.append([meta.HEROES.index(t) for t in row])

        dire_idx = []
        for row in dire:
            dire_idx.append([meta.HEROES.index(t) for t in row])

        # Look at 4th match, 2nd dire hero
        fourth = x3_data[3, :]
        idx_hero2_dire = dire_idx[3][1]

        # Should be zero for radiant "first order" and -1 for dire...
        self.assertEqual(fourth[idx_hero2_dire], 0)
        self.assertEqual(fourth[idx_hero2_dire+meta.NUM_HEROES], -1)

        # Now check 2nd order encoding for same match
        upper = dotautil.MLEncoding.unflatten_second_order_upper(
                            fourth[2*meta.NUM_HEROES:], mirror=False)

        # hero: [116, 116, 116, 116, 116]
        # other team: [113, 72, 0, 27, 117]
        hero_idx = 5*[idx_hero2_dire]
        enemy_idx = rad_idx[3]

        # Only the last entry should hold -1
        self.assertTrue(all(np.isclose(
            upper[(hero_idx, enemy_idx)],
            np.array([0.,  0.,  0.,  0., -1.])
        )))

        # Flipping around everything but the last should be populated
        self.assertTrue(all(np.isclose(
            upper[(enemy_idx, hero_idx)],
            np.array([1.,  1.,  1.,  1., 0.])
        )))


class TestWinRatePosition(TestDB):
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
