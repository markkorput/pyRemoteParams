#!/usr/bin/env python
import unittest
from remote_params import Param, Params

class TestParams(unittest.TestCase):
  def test_string(self):
    params = Params()
    param = params.string('name')
    self.assertEqual(param.type, 's')
    self.assertTrue(isinstance(param, Param))

  def test_int(self):
    params = Params()
    param = params.int('age')
    self.assertEqual(param.type, 'i')
    self.assertTrue(isinstance(param, Param))

  def test_bool(self):
    params = Params()
    param = params.bool('checked')
    self.assertEqual(param.type, 'b')
    self.assertTrue(isinstance(param, Param))

  def test_float(self):
    params = Params()
    param = params.float('value')
    self.assertEqual(param.type, 'f')
    self.assertTrue(isinstance(param, Param))

  def test_group(self):
    p = Params()
    self.assertEqual(len(p), 0)
    p2 = Params()
    p.group('P2', p2)
    self.assertEqual(len(p), 1)
    self.assertEqual(p.get('P2'), p2)

  def test_propagates_param_changes(self):
    p = Params()
    self.assertEqual(p.changeEvent._fireCount, 0)
    name = p.string('name')
    self.assertEqual(p.changeEvent._fireCount, 1)
    name.set('John')
    self.assertEqual(p.changeEvent._fireCount, 2)

  def test_propagates_params_changes(self):
    p = Params()
    self.assertEqual(len(p), 0)
    p2 = Params()
    p.group('P2', p2)
    self.assertEqual(p.changeEvent._fireCount, 1)
    p2.int('foo')
    self.assertEqual(p.changeEvent._fireCount, 2)

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
