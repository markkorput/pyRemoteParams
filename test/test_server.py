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
    self.assertIsNone(p1.get('ranking'))
    # mutation; a new parameter is added to pars
    pars.int('ranking')

    # after; verify the mutation is applied to r1's synced params
    self.assertEqual(len(p1), 2)
    self.assertIsNotNone(p1.get('ranking'))

  def test_disconnect(self):
    # params
    pars = Params()
    pars.string('name').set('Abe')
    # server
    s = Server(pars)

    # remote
    r1 = Remote()
    s.connect(r1)
    p1 = create_sync_params(r1)

    # before
    self.assertEqual(p1.get('name').val(), 'Abe')

    # action-1; param value change
    pars.get('name').set('Bob')

    # after-1; verify value change arrived at r1
    self.assertEqual(p1.get('name').val(), 'Bob')

    # action-1.1; r1 send value change
    r1.valueEvent('/name', 'Cat')

    # after-1; verify value change was processed by server
    self.assertEqual(pars.get('name').val(), 'Cat')
    # ... and was sent back to r1
    self.assertEqual(p1.get('name').val(), 'Cat')


    # action-2; param value changes AFTER r1 disconnects
    s.disconnect(r1)
    pars.get('name').set('Don')

    # after-2; verify value change did NOT arrive at r1
    self.assertEqual(p1.get('name').val(), 'Cat')

    # action-2.1; r1 send value change
    r1.valueEvent('/name', 'Eve')

    # after-1; verify value change was NOT processed by server
    self.assertEqual(pars.get('name').val(), 'Don')
    # ... and was NOT sent back to r1
    self.assertEqual(p1.get('name').val(), 'Cat')
    
  def test_disconnect_with_invalid_remote(self):
    # params
    pars = Params()
    pars.string('name').set('Abe')
    # server
    s = Server(pars)

    r = Remote()
    s.disconnect(r)
    s.disconnect(None)

  def test_option_queueIncomingValuesUntilUpdate(self):
    # params
    pars = Params()
    pars.string('name').set('Abe')
    # server
    s = Server(pars, queueIncomingValuesUntilUpdate=True)
    # remote
    r1 = Remote()
    s.connect(r1)
    
    # remote sends value change event
    r1.valueEvent('/name', 'Bob')
    # incoming value NOT effectuated yet (operation queued)
    self.assertEqual(pars.get('name').val(), 'Abe')
    # process queued operations
    s.update()
    # incoming value effectuated 
    self.assertEqual(pars.get('name').val(), 'Bob') 

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
