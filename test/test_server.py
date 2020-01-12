#!/usr/bin/env python
import unittest
from remote_params import Params, Server, Remote




class TestServer(unittest.TestCase):
  def test_server(self):
    pars = Params()
    pars.string('name')
    pars.int('age')

    s = Server(pars)
    r1 = Remote()
    s.connect(r1)

    r2_value_log = []
    def onval(path, val):
      r2_value_log.append((path, val))
    r2 = Remote(on_value=onval)

    self.assertEqual(r2_value_log, [])

    r1.valueEvent('/age', 41)
    self.assertEqual(r2_value_log, [('/age', 41)])

    # # s.set_value('/name', 'Jane')

    # osc_server = OscServer(port=8083)
    # osc_server.onMessage += osc_interface.onMessage

    # osc_interface = OscInterface(pars, prefix)





# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
