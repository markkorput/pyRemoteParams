#!/usr/bin/env python
import unittest
import json
from remote_params import Params, Server, Remote, create_sync_params, OscServer, schema_list

class TestOsc(unittest.TestCase):
  def test_osc_server(self):
    params = Params()
    params.string("name")

    server = Server(params)

    send_log = []
    def capture(host, port, addr, args):
      send_log.append((host,port,addr,args))

    osc_server = OscServer(server, capture_sends=capture)
    osc_server.process_message('/params/connect', '127.0.0.1:8081')

    self.assertEqual(send_log, [('127.0.0.1', 8081, '/params/connect/confirm', json.dumps(schema_list(params)))])








# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
