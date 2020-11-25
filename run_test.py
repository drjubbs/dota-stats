# -*- coding: utf-8 -*-
"""Unit testing for dota-stats"""
import unittest
import logging
import os
import numpy as np
import ujson as json
import fetch
import meta
from dotautil import MatchSerialization, MLEncoding, Bitmask

# Globals
BIGINT=9223372036854775808  # Max bitmask
DUMP_BUG = False            # See "TestDumpBug"


class TestDumpBug(unittest.TestCase):
    """Use this class to dump a problematic match JSON for additional testing
    JSON is stored into the testing directory.

        python run_test.py TestDumpBug
    """

    def test_fetch_debug(self):
        """Dump problematic API result to JSON"""

        if DUMP_BUG:
            match="5609573360"
            match=fetch.fetch_match(match,0)
            with open("./testing/{}.json".format(match), "w") as filename:
                filename.write(json.dumps(match))
                self.assertTrue(match is not None)


class TestProtobuf(unittest.TestCase):
    """Testing of serializeation and deserialization to protobuf."""

    def test_serialization(self):
        """
        a1: Radiant heroes
        a2: Dire heroes
        a3: Items dictionary
        a4: Gold Spent dictionary

        """
        with open(os.path.join("testing", "protobuf.json"), "r") as filename:
            sample=json.loads(filename.read())

        test_pb=MatchSerialization.protobuf_match_details(
                        sample['radiant_heroes'],
                        sample['dire_heroes'],
                        sample['items'],
                        sample['gold'])

        radiant_heroes, dire_heroes, items, gold =\
                                MatchSerialization.unprotobuf_match_details(test_pb)

        self.assertEqual(sample['radiant_heroes'], radiant_heroes)
        self.assertEqual(sample['dire_heroes'], dire_heroes)
        self.assertEqual(sample['items'], items)
        self.assertEqual(sample['gold'], gold)


class TestFetch(unittest.TestCase):
    """Test routines in the main fetch.py logic"""

    def test_bad_api_key(self):
        """Check error handling on a bad API key"""

        old_key = os.environ["STEAM_KEY"]
        os.environ["STEAM_KEY"]="AAAAA"
        with self.assertRaises(Exception) as context:
            _ = fetch.fetch_match(111,1)
        self.assertEqual(str(context.exception),
                'Forbidden - Check Steam API key')
        os.environ["STEAM_KEY"]=old_key


    def test_bad_match_id(self):
        """Check handling of a bad match ID"""

        with self.assertRaises(fetch.APIException) as context:
            _ = fetch.fetch_match(111,1)
        self.assertEqual(str(context.exception), 'Match ID not found')


    def test_bot_detection(self):
        """Check feeding/bot detection"""
        with open("./testing/bots.json") as filename:
            match=json.loads(filename.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='Feeding')

    def test_backpack(self):
        """Check that items in backpack are registered as valid. In
        this match Jugg had phase boots in backpack"""

        with open("./testing/backpack.json") as filename:
            match=json.loads(filename.read())
        parsed_match = fetch.parse_match(match)
        item_dict=json.loads(parsed_match['items'])
        jugg = item_dict[str(meta.REVERSE_HERO_DICT['juggernaut'])]
        self.assertTrue(meta.ITEMS['phase_boots']['id'] in jugg)

    def test_no_items(self):
        """Test no items detection"""

        with open("./testing/no_items.json") as filename:
            match=json.loads(filename.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='No items')

    def test_null_hero(self):
        """Exception on missing hero"""

        with open("./testing/null_hero.json") as filename:
            match=json.loads(filename.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='Null Hero ID')


class TestBitmasks(unittest.TestCase):
    """Test code which encodes herolist to a bitmask and vice-versa"""

    def test_bitmask(self):
        """Test code which encodes herolist to a bitmask and vice-versa"""

        # Check some hand-selected patterns
        test_patterns=[
            [1, 2, 3],                # Basic
            [1, 63, 64, 123, 124],    # Test edges
            [28, 17, 93, 66, 26],     # From real games
            [23, 104, 9, 31, 8],  # From real games
        ]

        for test_pattern in test_patterns:
            enc=Bitmask.encode_heroes_bitmask(test_pattern)
            dec=Bitmask.decode_heroes_bitmask(enc)
            self.assertEqual(set(test_pattern), set(dec))

        # Check all the numbers [1,189]
        results=[]
        for idx in [t+1 for t in range(188)]:
            enc=Bitmask.encode_heroes_bitmask([idx])
            self.assertTrue(all([t<=BIGINT for t in enc]))
            dec=Bitmask.decode_heroes_bitmask(enc)
            results.append(idx==dec[0])
        self.assertTrue(all(results))


        # Check where clause generation, check edge cases
        self.assertEqual(Bitmask.where_bitmask(1),
                "WHERE hero_mask_low & 2 = 2")
        self.assertEqual(Bitmask.where_bitmask(63),
            "WHERE hero_mask_low & 9223372036854775808 = 9223372036854775808")
        self.assertEqual(Bitmask.where_bitmask(64),
            "WHERE hero_mask_mid & 1 = 1")
        self.assertEqual(Bitmask.where_bitmask(127),
            "WHERE hero_mask_mid & 9223372036854775808 = 9223372036854775808")
        self.assertEqual(Bitmask.where_bitmask(128),
            "WHERE hero_mask_high & 1 = 1")

        # Exceptions
        with self.assertRaises(Exception) as context:
            Bitmask.encode_heroes_bitmask([0])
        self.assertEqual(str(context.exception), "Hero out of range 0")

        with self.assertRaises(Exception) as context:
            Bitmask.encode_heroes_bitmask([200])
        self.assertEqual(str(context.exception), "Hero out of range 200")


class TestMLEncoding(unittest.TestCase):
    """Test one-hot encoding for machine learning"""

    def setUp(self):
        test_heroes=[
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

        rad_heroes=[t[0:5] for t in test_heroes]
        dire_heroes=[t[5:] for t in test_heroes]

        # First order matrix... this routine is vectorized over matches
        self.x1_test = MLEncoding.first_order_vector(rad_heroes, dire_heroes)

        # Second order matrix is upper triangular, without the diagonal,
        # rolled out. This is whether or not a team/enemy hero pair exists
        self.x2_test=np.zeros([len(test_heroes),
                               int((num_heroes)*(num_heroes-1)/2)],dtype='b')

        # Loop over all 'fake matches' and flatten first and second order
        # matrices
        counter=0
        for heroes in test_heroes:
            # self.x1_test[counter,:] = \
            #         MLEncoding.first_order_vector(heroes[0:5],heroes[5:])
            x2_mat = MLEncoding.second_order_hmatrix(heroes[0:5],heroes[5:])
            self.x2_test[counter,:] = \
                    MLEncoding.flatten_second_order_upper(x2_mat)
            counter=counter+1


    def test_first_order_vector(self):
        """Test the first oder mapping """

        # Rows for first order encoding should sum to zero since
        # 1 and -1 are used for randiant/dire
        row_sum = np.array(self.x1_test.sum(axis=1))
        row_zero = np.zeros([len(row_sum), 1])
        self.assertTrue(np.all(row_sum==row_zero))

        # First half should sum to 5
        sum_radiant = self.x1_test[:,0:meta.NUM_HEROES].sum(axis=1)
        sum_check = np.ones([len(sum_radiant), 1])*5
        self.assertTrue(np.all(sum_radiant == sum_check))

        ## First half should sum to -5
        sum_dire = self.x1_test[:,meta.NUM_HEROES:2*meta.NUM_HEROES].sum(axis=1)
        sum_check = -1 * sum_check
        self.assertTrue(np.all(sum_dire == sum_check))

    def test_flatten_unflatten_second_order_upper(self):
        """Test the code which `unravels` a matrix into the upper
        triangular format without the diagonal.
        """
        simple=np.array([[0,1,2,3,4],
                      [0,0,5,6,7],
                      [0,0,0,8,9],
                      [0,0,0,0,10],
                      [0,0,0,0,0]])
        flat_a=MLEncoding.flatten_second_order_upper(simple)
        flat_b=np.array([1,2,3,4,5,6,7,8,9,10])
        self.assertTrue(np.all(flat_a==flat_b))

        # When we unflatten, the upper triangle will be mirrored
        # and reflected over the diagonal which is still zero
        simple2_a=np.array([[ 0,  1,  2,   3,  4],
                            [-1,  0,  5,   6,  7],
                            [-2, -5,  0,   8,  9],
                            [-3, -6, -8,   0, 10],
                            [-4, -7, -9, -10,  0],
                           ])
        simple2_b=MLEncoding.unflatten_second_order_upper(flat_a)
        self.assertTrue(np.all(simple2_a==simple2_b))


    def test_second_order_hmatrix(self):
        """Some basic integrity checks on x2. All columns should be between
        [-25,25] the first two rows are constructed to be 25 and -25
        respectively. The sign convention depends on whether or not the first
        hero in the pair (radiant-dire) falls below or above the diagonal.

        Each row is a match.
        """

        row_sum = self.x2_test.sum(axis=1)
        # Upper limit
        upper=(np.ones(self.x2_test.shape[0])*25).reshape(self.x2_test.shape[0],1)
        # Lower limit
        lower=(np.ones(self.x2_test.shape[0])*-25).reshape(self.x2_test.shape[0],1)

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

        _, _, _, x3_data = \
                        MLEncoding.create_features(rad, dire, wins)

        # Convert to hero index from hero number
        rad_idx = []
        for row in rad:
            rad_idx.append([meta.HEROES.index(t) for t in row ])

        dire_idx = []
        for row in dire:
            dire_idx.append([meta.HEROES.index(t) for t in row ])

        # Look at 4th match, 2nd dire hero
        fourth = x3_data[3, :]
        idx_hero2_dire = dire_idx[3][1]

        # Should be zero for radiant "first order" and -1 for dire...
        self.assertEqual(fourth[idx_hero2_dire], 0)
        self.assertEqual(fourth[idx_hero2_dire+meta.NUM_HEROES], -1)

        # Now check 2nd order encoding for same match
        upper = MLEncoding.unflatten_second_order_upper(\
                            fourth[2*meta.NUM_HEROES:], mirror=False)

        # hero: [116, 116, 116, 116, 116]
        # other team: [113, 72, 0, 27, 117]
        hero_idx = 5*[idx_hero2_dire]
        enemy_idx = rad_idx[3]

        # Only the last entry should hold -1
        self.assertTrue(all(np.isclose(
            upper[(hero_idx, enemy_idx)],
            np.array([ 0.,  0.,  0.,  0., -1.])
        )))

        # Flipping around everything but the last should be populated
        self.assertTrue(all(np.isclose(
            upper[(enemy_idx, hero_idx)],
            np.array([ 1.,  1.,  1.,  1., 0.])
        )))


if __name__ == '__main__':
    fetch.log.setLevel(logging.CRITICAL)
    unittest.main()
