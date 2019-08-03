import unittest
import util

class TestFramework(unittest.TestCase):
    def test_encoding(self):
        for hl in ([62,63,64,65,112],
                   [1,2,3,4,5],
                    [101,69,11,13,1]):
            z=util.encode_heroes(hl)
            self.assertEqual(sorted(hl),util.decode_heroes(z[0],z[1]))



if __name__ == '__main__':
    unittest.main()
