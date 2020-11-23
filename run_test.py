import unittest
import sys
import logging
import os
import numpy as np
import ujson as json
import fetch
import meta
import ml_encoding
import dotautil

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
            m=fetch.fetch_match(match,0)
            with open("./testing/{}.json".format(match), "w") as f:
                f.write(json.dumps(m))
            pm=fetch.parse_match(m)

class TestProtobuf(unittest.TestCase):
    """Testing of serializeation and deserialization to protobuf."""
 
    def test_serialization(self):
        """
        a1: Radiant heroes
        a2: Dire heroes
        a3: Items dictionary
        a4: Gold Spent dictionary

        """
        a1='[41, 25, 51, 75, 60]'
        a2='[30, 1, 22, 2, 50]'
        a3='{"41": [135, 108, 172, 75, 63, 75, 212, 0, 38, 0], "75": [206, 36, 216, 63, 77, 188, 354, 0, 0, 0], "25": [100, 273, 259, 48, 77, 77, 331, 39, 237, 0], "60": [1, 36, 8, 73, 108, 50, 357, 17, 0, 0], "51": [98, 223, 36, 214, 0, 0, 356, 0, 0, 0], "22": [41, 29, 232, 77, 77, 77, 287, 216, 0, 0], "2": [127, 34, 11, 0, 214, 0, 71, 0, 0, 0], "30": [254, 0, 0, 0, 0, 0, 0, 0, 0, 0], "1": [63, 27, 27, 75, 145, 0, 239, 288, 0, 0], "50": [216, 0, 23, 180, 27, 0, 349, 0, 0, 0]}'
        a4='{"41": 14180, "75": 6835, "25": 14470, "60": 13060, "51": 8630, "22": 5565, "2": 3985, "30": 5840, "1": 7710, "50": 3565}'

        test_pb=dotautil.protobuf_match_details(a1,a2,a3,a4)
        b1,b2,b3,b4=dotautil.unprotobuf_match_details(test_pb)

        self.assertEqual(json.loads(a1), json.loads(b1))
        self.assertEqual(json.loads(a2), json.loads(b2))
        self.assertEqual(json.loads(a3), json.loads(b3))
        self.assertEqual(json.loads(a4), json.loads(b4))


class TestFetch(unittest.TestCase):
    """Test routines in the main fetch.py logic"""

    def test_bad_api_key(self):
        """Check error handling on a bad API key"""

        old_key = os.environ["STEAM_KEY"]
        os.environ["STEAM_KEY"]="AAAAA"
        with self.assertRaises(Exception) as context:
            m=fetch.fetch_match(111,1)
        self.assertEqual(str(context.exception), 
                'Forbidden - Check Steam API key')
        os.environ["STEAM_KEY"]=old_key


    def test_bad_match_id(self):
        """Check handling of a bad match ID"""

        with self.assertRaises(fetch.APIException) as context:
            m=fetch.fetch_match(111,1)
        self.assertEqual(str(context.exception), 'Match ID not found')


    def test_bot_detection(self):
        """Check feeding/bot detection"""
        with open("./testing/bots.json") as f:
            match=json.loads(f.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='Feeding')

    def test_backpack(self):
        """Check that items in backpack are registered as valid"""
        
        with open("./testing/backpack.json") as f:
            match=json.loads(f.read())
        pm = fetch.parse_match(match)
        item_dict=json.loads(pm['items'])
        jugg=item_dict[str(meta.REVERSE_HERO_DICT['juggernaut'])]
        self.assertTrue(meta.ITEMS['phase_boots']['id'] in jugg)

    def test_no_items(self):
        """Test no items detection"""

        with open("./testing/no_items.json") as f:
            match=json.loads(f.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='No items')

    def test_null_hero(self):
        """Exception on missing hero"""

        with open("./testing/null_hero.json") as f:
            match=json.loads(f.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='Null Hero ID')


class TestBitmasks(unittest.TestCase):
    """Test code which encodes herolist to a bitmask and vice-versa"""

    def test_bitmask(self):
        """Test code which encodes herolist to a bitmask and vice-versa"""

        # Check some hand-selected patterns
        test_patterns=[
            [1,2,3],              # Basic
            [1,63,64,123,124],    # Test edges
            [28, 17, 93, 66, 26], # From real games
            [23, 104, 9, 31, 8],  # From real games    
        ]

        for test_pattern in test_patterns:
            enc=dotautil.encode_heroes_bitmask(test_pattern)
            dec=dotautil.decode_heroes_bitmask(enc)    
            self.assertEqual(set(test_pattern), set(dec))
        
        # Check all the numbers [1,189]
        results=[]
        for idx in [t+1 for t in range(188)]:
            enc=dotautil.encode_heroes_bitmask([idx])
            self.assertTrue(all([t<=BIGINT for t in enc]))
            dec=dotautil.decode_heroes_bitmask(enc)
            results.append(idx==dec[0])    
        self.assertTrue(all(results))


        # Check where clause generation, check edge cases
        self.assertEqual(dotautil.where_bitmask(1),
                "WHERE hero_mask_low & 2 = 2")
        self.assertEqual(dotautil.where_bitmask(63),
            "WHERE hero_mask_low & 9223372036854775808 = 9223372036854775808")
        self.assertEqual(dotautil.where_bitmask(64),
            "WHERE hero_mask_mid & 1 = 1")
        self.assertEqual(dotautil.where_bitmask(127),
            "WHERE hero_mask_mid & 9223372036854775808 = 9223372036854775808")
        self.assertEqual(dotautil.where_bitmask(128),
            "WHERE hero_mask_high & 1 = 1")

        # Exceptions
        with self.assertRaises(Exception) as context:
            dotautil.encode_heroes_bitmask([0])
        self.assertEqual(str(context.exception), "Hero out of range 0")

        with self.assertRaises(Exception) as context:
            dotautil.encode_heroes_bitmask([200])
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

        # First order matrix... 0 --> N radiant, N --> 2N dire markers. 
        # Number of rows = # of matches
        self.x1_test=np.zeros([len(test_heroes),
                               2*meta.NUM_HEROES],dtype='b')

        # Second order matrix is upper triangular, without the diagonal,
        # rolled out. This is whether or not a team/enemy hero pair exists
        self.x2_test=np.zeros([len(test_heroes),
                               int((num_heroes)*(num_heroes-1)/2)],dtype='b')

        # Loop over all 'fake matches' and flatten first and second order
        # matrices
        counter=0
        for heroes in test_heroes:
            self.x1_test[counter,:] = \
                    ml_encoding.first_order_vector(heroes[0:5],heroes[5:])    
            x2_mat = ml_encoding.second_order_hmatrix(heroes[0:5],heroes[5:])
            self.x2_test[counter,:] = \
                    ml_encoding.flatten_second_order_upper(x2_mat)
            counter=counter+1
       

    def test_first_order_vector(self):
        """Test the first oder mapping """

        # Rows for first order encoding should sum to zero since
        # 1 and -1 are used for randiant/dire
        row_sum = np.array(self.x1_test.sum(axis=1))
        row_zero = np.zeros([len(row_sum), 1])
        self.assertTrue(np.all(row_sum==row_zero))

        # First half should sum to 5
        a=self.x1_test[:,0:meta.NUM_HEROES].sum(axis=1)
        b=np.ones(self.x1_test.shape[0]).reshape(self.x1_test.shape[0],1)*5
        self.assertTrue(np.all(a==b))

        ## First half should sum to -5
        a=self.x1_test[:,meta.NUM_HEROES:2*meta.NUM_HEROES].sum(axis=1)
        b=np.ones(self.x1_test.shape[0]).reshape(self.x1_test.shape[0],1)*(-5)
        self.assertTrue(np.all(a==b))

    def test_flatten_unflatten_second_order_upper(self):
        """Test the code which `unravels` a matrix into the upper
        triangular format without the diagonal.
        """
        simple=np.array([[0,1,2,3,4],
                      [0,0,5,6,7],
                      [0,0,0,8,9],
                      [0,0,0,0,10],
                      [0,0,0,0,0]])
        flat_a=ml_encoding.flatten_second_order_upper(simple)
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
        simple2_b=ml_encoding.unflatten_second_order_upper(flat_a)        
        self.assertTrue(np.all(simple2_a==simple2_b))
        
    def test_second_order_hmatrix(self):
        # Some basic integrity checks on x2. All columns should be between [-25,25]
        # the first two rows are constructed to be 25 and -25 respectively

        a=self.x2_test.sum(axis=1)
        # Upper limit
        b=(np.ones(self.x2_test.shape[0])*25).reshape(self.x2_test.shape[0],1)
        # Lower limit
        c=(np.ones(self.x2_test.shape[0])*-25).reshape(self.x2_test.shape[0],1)
        
        self.assertEqual(a[0],25)
        self.assertEqual(a[1],-25)
        self.assertTrue(np.all(a<=b))
        self.assertTrue(np.all(a>=c))

if __name__ == '__main__':
    fetch.log.setLevel(logging.CRITICAL)
    unittest.main()
