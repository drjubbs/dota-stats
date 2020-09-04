import unittest
import sys
import json
import util
import fetch
import meta

#class TestDumpBug(unittest.TestCase):
#    """Use this class to dump a problematic match JSON for
#    additional testing. JSON is stored into the testing
#    directory.
#    
#        python run_test.py TestDumpBug
#    
#    """
#    def test_fetch_debug(self):
#        match="5553775652"
#        m=fetch.fetch_match(match,0)
#        with open("./testing/{}.json".format(match), "w") as f:
#            f.write(json.dumps(m))
#        pm=fetch.parse_match(m)

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


if __name__ == '__main__':
    unittest.main()
