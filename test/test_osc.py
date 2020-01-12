#!/usr/bin/env python
import unittest
import json
from remote_params import Params, Server, Remote, create_sync_params, OscServer, schema_list

class TestOsc(unittest.TestCase):
  def test_osc_server_choreography(self):
    #
    # setup
    #

    # param
    params = Params()
    params.string("name")
    # server
    server = Server(params)
    
    # intercept all outgoing osc messages into send_log
    send_log = []
    def capture(host, port, addr, args):
      send_log.append((host,port,addr,args))

    # create osc server
    osc_server = OscServer(server, capture_sends=capture)

    #
    # Client connects
    #

    # create fake incoming connect message
    osc_server.receive('/params/connect', ['127.0.0.1:8081'])
    # verify a connect confirmation was sent
    self.assertEqual(send_log, [
      ('127.0.0.1', 8081, '/params/connect/confirm', (json.dumps(schema_list(params))))])

    #
    # Client sends new value
    #
    self.assertIsNone(params.get('name').val())
    send_log.clear()
    osc_server.receive('/params/value', ['/name', 'Fab'])
    # verify value got applied into our local params
    self.assertEqual(params.get('name').val(), 'Fab')
    # verify the value was broadcasted back to client
    self.assertEqual(send_log, [
      ('127.0.0.1', 8081, '/params/value', ('/name', 'Fab'))])


    #
    # Client sends invalid new value
    #
    send_log.clear()
    osc_server.receive('/params/value', ['/foo', 'bar'])
    # verify nothing sent out to client(s)
    self.assertEqual(len(send_log), 0)

    #
    # Schema change broadcasted to client
    #
    send_log.clear()
    params.int('age')
    self.assertEqual(send_log, [
      ('127.0.0.1', 8081, '/params/schema', (json.dumps(schema_list(params))))])

    #
    # Client requests schema
    #
    send_log.clear()
    osc_server.receive('/params/schema', ['192.168.1.2:8080'])
    # verify response
    self.assertEqual(send_log, [
      ('192.168.1.2', 8080, '/params/schema', (json.dumps(schema_list(params))))])

    #
    # Client disconnected by server
    #
    send_log.clear()
    # osc_server.receive('/params/disconnect', ('127.0.0.1:8081'))
    for r in server.connected_remotes:
      r.send_disconnect()
      # server.disconnect(r)
    self.assertEqual(send_log, [
      ('127.0.0.1', 8081, '/params/disconnect', ())])




# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
