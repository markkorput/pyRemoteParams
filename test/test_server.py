#!/usr/bin/env python
import unittest
from remote_params import Params, Server, Remote, create_sync_params

class TestServer(unittest.TestCase):
  def test_broadcast_incoming_value_changes(self):
    # params
    pars = Params()
    pars.string('name')
    pars.int('age')
    # server
    s = Server(pars)
    # remote r1
    r1 = Remote()
    s.connect(r1)

    # remote r2
    r2_value_log = []
    def onval(path, val):
      print ('--- on val {}'.format(path))
      r2_value_log.append((path, val))
    
    r2 = Remote()
    r2.sendValueEvent += onval
    s.connect(r2)

    self.assertEqual(r2_value_log, [])
    # remote r1 send value change to server
    r1.valueEvent('/age', 41)
    # verify the change was broadcasted to r2
    self.assertEqual(r2_value_log, [('/age', 41)])
  
  def test_create_sync_params(self):
    # params
    pars = Params()
    pars.string('name')
    # server
    s = Server(pars)
    # remote
    r1 = Remote()
    s.connect(r1)
    p1 = create_sync_params(r1)

    # before
    self.assertEqual(len(p1), 1)

    # mutation
    pars.int('ranking')

    # after
    self.assertEqual(len(p1), 2)



# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
