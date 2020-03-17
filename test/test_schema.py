#!/usr/bin/env python
import unittest, json
from remote_params import Params, schema_list, get_values, get_path

class TestSchema(unittest.TestCase):
  def test_schema_list_empty(self):
    pars = Params()
    self.assertEqual(schema_list(pars), [])

  def test_get_path_with_invalid_path(self):
    pars = Params()
    pars.string('foo')
    self.assertIsNone(get_path(pars, '/bar'))

  def test_schema_list(self):
    pars = Params()
    pars.string('name')
    pars.int('count')
    pars.float('price')
    pars.bool('soldout')

    details = Params()
    details.int('page_count')
    details.string('author')
    pars.group('details', details)

    self.assertEqual(schema_list(pars), [
      {'path': '/name', 'type':'s'},
      {'path': '/count', 'type':'i'},
      {'path': '/price', 'type':'f'},
      {'path': '/soldout', 'type':'b'},
      {'path': '/details/page_count', 'type':'i'},
      {'path': '/details/author', 'type':'s'}
    ])

  def test_schema_list_with_values(self):
    pars = Params()
    pars.string('name').set('Moby Dick')
    pars.int('count').set(100)
    pars.float('price').set(9.99)
    pars.bool('soldout').set(False)

    details = Params()
    details.int('page_count').set(345)
    details.string('author').set('Herman Melville')
    pars.group('details', details)

    self.assertEqual(schema_list(pars), [
      {'path': '/name', 'type':'s', 'value':'Moby Dick'},
      {'path': '/count', 'type':'i', 'value':100},
      {'path': '/price', 'type':'f', 'value':9.99},
      {'path': '/soldout', 'type':'b', 'value':False},
      {'path': '/details/page_count', 'type':'i','value':345},
      {'path': '/details/author', 'type':'s','value':'Herman Melville'}
    ])

  def test_schema_list_with_restrictions(self):
    pars = Params()
    pars.int('count', min=3, max=10).set(1)
    pars.float('price', min=0.0, max=1.0).set(9.99)

    self.assertEqual(schema_list(pars), [
      {'path': '/count', 'type':'i', 'value':3, 'opts': {'min':3, 'max':10}},
      {'path': '/price', 'type':'f', 'value':1.0, 'opts': {'min':0.0, 'max':1.0}},
    ])

  def test_get_values(self):
    pars = Params()
    pars.int('count').set(1)
    pars.float('price').set(9.99)

    vals = get_values(pars)

    self.assertEqual(vals['count'], 1)
    self.assertEqual(vals['price'], 9.99)
    self.assertEqual(json.loads(json.dumps(vals))['count'], 1)
    self.assertEqual(json.loads(json.dumps(vals))['price'], 9.99)

    pars.get('count').set(100)
    self.assertEqual(get_values(pars)['count'], 100)

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
