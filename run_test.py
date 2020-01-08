import unittest
import sys
import json
import util
import fetch
import meta
import hero_analysis

"""
Fetching a match for debugging:

import fetch
import json
m=fetch.fetch_match("5173397139",2)
with open("backpack.json", "w") as f:
    f.write(json.dumps(m))

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

    def test_unpack_match(self):
        
        a, b = hero_analysis.unpack_match("1234", 'axe', 
                "[1,2,3,4,5]", "[6,7,8,9,10]", False)
        c, d = hero_analysis.unpack_match("1234", 'drow-ranger', 
                "[1,2,3,4,5]", "[6,7,8,9,10]", False)
        e, f = hero_analysis.unpack_match("1234", 'phantom-lancer', 
                "[1,2,3,4,5]", "[6,7,8,9,10]", False)

        self.assertEqual(a, 
                [('1234', 'axe', 1, 'drow-ranger', 0),
                 ('1234', 'axe', 1, 'earthshaker', 0),
                 ('1234', 'axe', 1, 'juggernaut', 0),
                 ('1234', 'axe', 1, 'mirana', 0),
                 ('1234', 'axe', 1, 'morphling', 0)])

        self.assertEqual(b,
                [('1234', 'axe', 1, 'anti-mage', 0),
                 ('1234', 'axe', 1, 'bane', 0),
                 ('1234', 'axe', 1, 'bloodseeker', 0),
                 ('1234', 'axe', 1, 'crystal-maiden', 0)])

        self.assertEqual(c,
            [('1234', 'drow-ranger', 0, 'anti-mage', 1),
             ('1234', 'drow-ranger', 0, 'axe', 1),
             ('1234', 'drow-ranger', 0, 'bane', 1),
             ('1234', 'drow-ranger', 0, 'bloodseeker', 1),
             ('1234', 'drow-ranger', 0, 'crystal-maiden', 1)])

        self.assertEqual(d,
            [('1234', 'drow-ranger', 0, 'earthshaker', 1),
             ('1234', 'drow-ranger', 0, 'juggernaut', 1),
             ('1234', 'drow-ranger', 0, 'mirana', 1),
             ('1234', 'drow-ranger', 0, 'morphling', 1)])

        self.assertEqual(e, [])
        self.assertEqual(f, [])


if __name__ == '__main__':
    unittest.main()
