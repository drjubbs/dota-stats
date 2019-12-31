import unittest
import sys
import json
import util
import fetch
import meta

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


if __name__ == '__main__':
    unittest.main()
