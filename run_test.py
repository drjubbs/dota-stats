import unittest
import sys
import json
import numpy as np
import fetch
import meta
import ml_encoding

"""
class TestDumpBug(unittest.TestCase):
    #
    # Use this class to dump a problematic match JSON for
    # additional testing. JSON is stored into the testing
    # directory.
    #
    #    python run_test.py TestDumpBug
    #
    def test_fetch_debug(self):
        match="5599868955"
        m=fetch.fetch_match(match,0)
        with open("./testing/{}.json".format(match), "w") as f:
            f.write(json.dumps(m))
        pm=fetch.parse_match(m)
"""

class TestFramework(unittest.TestCase):
    def test_encoding(self):
        for hl in ([62,63,64,65,112],
                   [1,2,3,4,5],
                    [101,69,11,13,1]):
            z=util.encode_heroes(hl)
            self.assertEqual(sorted(hl),util.decode_heroes(z[0],z[1]))

    def test_bot_detection(self):
        with open("./testing/bots.json") as f:
            match=json.loads(f.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='Feeding')

    def test_backpack(self):
        with open("./testing/backpack.json") as f:
            match=json.loads(f.read())

        pm = fetch.parse_match(match)

        item_dict=json.loads(pm['items'])
        jugg=item_dict[str(meta.REVERSE_HERO_DICT['juggernaut'])]
        self.assertTrue(meta.ITEMS['phase_boots']['id'] in jugg)

    def test_no_items(self):
        with open("./testing/no_items.json") as f:
            match=json.loads(f.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='No items')

    def test_null_hero(self):
        with open("./testing/null_hero.json") as f:
            match=json.loads(f.read())

        with self.assertRaises(Exception) as context:
            fetch.parse_match(match)

        self.assertTrue(context.exception.__str__()=='Null Hero ID')


class TestMLEncoding(unittest.TestCase):
    def setUp(self):
        # Build a sample matrix
        self.X1_test=np.zeros([10,2*meta.NUM_HEROES],dtype='b')
        self.X2_test=np.zeros([10,int((meta.NUM_HEROES)*(meta.NUM_HEROES-1)/2)],dtype='b')

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

        counter=0
        for heroes in test_heroes:
            self.X1_test[counter,:]=ml_encoding.first_order_vector(heroes[0:5],heroes[5:])    
            t=ml_encoding.second_order_hmatrix(heroes[0:5],heroes[5:])
            self.X2_test[counter,:]=ml_encoding.flatten_second_order_upper(t)
            counter=counter+1
    
    def test_first_order_vector(self):
        # Row should sum to zero
        a=np.array(self.X1_test.sum(axis=1))
        b=np.zeros(self.X1_test.shape[0]).reshape(self.X1_test.shape[0],1)
        self.assertTrue(np.all(a==b))
            

        # First half should sum to 5
        a=self.X1_test[:,0:meta.NUM_HEROES].sum(axis=1)
        b=np.ones(self.X1_test.shape[0]).reshape(self.X1_test.shape[0],1)*5
        self.assertTrue(np.all(a==b))

        ## First half should sum to -5
        a=self.X1_test[:,meta.NUM_HEROES:2*meta.NUM_HEROES].sum(axis=1)
        b=np.ones(self.X1_test.shape[0]).reshape(self.X1_test.shape[0],1)*(-5)
        self.assertTrue(np.all(a==b))

    def test_flatten_unflatten_second_order_upper(self):
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
        # Some basic integrity checks on X2. All columns should be between [-25,25]
        # the first two rows are constructed to be 25 and -25 respectively

        a=self.X2_test.sum(axis=1)
        # Upper limit
        b=(np.ones(self.X2_test.shape[0])*25).reshape(self.X2_test.shape[0],1)
        # Lower limit
        c=(np.ones(self.X2_test.shape[0])*-25).reshape(self.X2_test.shape[0],1)
        
        self.assertEqual(a[0],25)
        self.assertEqual(a[1],-25)
        self.assertTrue(np.all(a<=b))
        self.assertTrue(np.all(a>=c))

if __name__ == '__main__':
    unittest.main()
