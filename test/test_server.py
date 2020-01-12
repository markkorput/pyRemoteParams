#!/usr/bin/env python
import unittest
from remote_params import Params, Server, Remote




class TestServer(unittest.TestCase):
  def test_server(self):
    # params
    pars = Params()
    pars.string('name')
    pars.int('age')
    # server
    s = Server(pars)
    # remote r1
    r1 = Remote()
    s.connect(r1)

    r2_value_log = []
    def onval(path, val):
      print ('--- on val {}'.format(path))
      r2_value_log.append((path, val))
    
    r2 = Remote(on_value=onval)
    s.connect(r2)

    self.assertEqual(r2_value_log, [])
    # remote r1 send value change to server
    r1.valueEvent('/age', 41)
    # verify the change was broadcasted to r2
    self.assertEqual(r2_value_log, [('/age', 41)])

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
