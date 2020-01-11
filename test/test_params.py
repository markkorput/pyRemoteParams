#!/usr/bin/env python
import unittest
from remote_params import Params

class TestParams(unittest.TestCase):
  def test_add(self):
    p = Params()
    self.assertEqual(len(p), 0)
    p2 = Params()
    p.append(p2)
    self.assertEqual(len(p), 1)
    self.assertEqual(p[0], p2)


# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
