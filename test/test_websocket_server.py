
#!/usr/bin/env python
import unittest
from remote_params import HttpServer, Params, Server, Remote, create_sync_params, schema_list
import asyncio, asynctest

from remote_params.WebsocketServer import WebsocketServer
class TestWebsocketServer(asynctest.TestCase):
  def setUp(self):
    self.params = params = Params()
    self.p1 = params.int('some_int')
    self.p1.set(0)

    self.wss = WebsocketServer(Server(self.params), start=False)

  def test_default_port(self):
    self.assertEqual(self.wss.port, 8081)

  async def test_incoming_value(self):
    await self.wss.start_async()
    await self.wss.onMessage(f'POST /some_int?value={4}', None)
    self.assertEqual(self.p1.value, 4)
    self.wss.stop()

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
