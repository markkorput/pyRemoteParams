#!/usr/bin/env python
import unittest
from remote_params import Params, Param, IntParam, FloatParam

class TestParams(unittest.TestCase):
  def test_string(self):
    params = Params()
    param = params.string('name')
    self.assertEqual(param.type, 's')
    self.assertTrue(isinstance(param, Param))

    param.set(4)
    self.assertEqual(param.val(), '4')

  def test_int(self):
    params = Params()
    param = params.int('age')
    self.assertEqual(param.type, 'i')
    self.assertTrue(isinstance(param, Param))

    param.set('4')
    self.assertEqual(param.val(), 4)
    param.set('zzz')
    self.assertEqual(param.val(), 4)

  def test_bool(self):
    params = Params()
    param = params.bool('checked')
    self.assertEqual(param.type, 'b')
    self.assertTrue(isinstance(param, Param))

    param.set('true')
    self.assertEqual(param.val(), True)
    param.set('xxx')
    self.assertEqual(param.val(), True)
    param.set('false')
    self.assertEqual(param.val(), False)
    param.set('yyy')
    self.assertEqual(param.val(), False)

  def test_float(self):
    params = Params()
    param = params.float('value')
    self.assertEqual(param.type, 'f')
    self.assertTrue(isinstance(param, Param))

    param.set('4.81')
    self.assertEqual(param.val(), 4.81)
    param.set('zzz')
    self.assertEqual(param.val(), 4.81)

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

  def test_get(self):
    params = Params()
    param = params.bool('check')
    self.assertEqual(params.get('check'), param)
    self.assertIsNone(params.get('foo'))

class TestParam(unittest.TestCase):
  def test_setter(self):
    p = Param('f', setter=float)
    p.set('5.50')
    self.assertEqual(p.val(), 5.5)

  def test_getter(self):
    p = Param('f', getter=float)
    p.set('5.50')
    self.assertEqual(p.value, '5.50')
    self.assertEqual(p.val(), 5.50)

  def test_opts(self):
    p = Param('s', opts={'minlength': 3})
    self.assertEqual(p.opts, {'minlength': 3})

class TestIntParam(unittest.TestCase):
  def test_set_with_invalid_value(self):
    p = IntParam()
    p.set(4)
    self.assertEqual(p.val(), 4)
    p.set('abc')
    self.assertEqual(p.val(), 4)
    p.set('05')
    self.assertEqual(p.val(), 5)

  def test_to_dict(self):
    p = IntParam(min=5, max=10)
    self.assertEqual(p.to_dict(), {'type':'i', 'min':5, 'max':10})

class TestFloatParam(unittest.TestCase):
  def test_set_with_invalid_value(self):
    p = FloatParam()
    p.set(4.0)
    self.assertEqual(p.val(), 4.0)
    p.set('abc')
    self.assertEqual(p.val(), 4.0)
    p.set('05')
    self.assertEqual(p.val(), 5.0)

  def test_to_dict(self):
    p = IntParam(min=5, max=10)
    self.assertEqual(p.to_dict(), {'type':'i', 'min':5, 'max':10})

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
