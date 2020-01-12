#!/usr/bin/env python
import unittest
from remote_params import Params, schema_list

class TestSchema(unittest.TestCase):
  def test_schema_list_empty(self):
    pars = Params()
    self.assertEqual(schema_list(pars), [])

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
      {'path': '/count', 'type':'i', 'value':3, 'min':3, 'max':10},
      {'path': '/price', 'type':'f', 'value':1.0, 'min':0.0, 'max':1.0},
    ])

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
