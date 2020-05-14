
#!/usr/bin/env python
import unittest
from remote_params import HttpServer, Params, Server, Remote, create_sync_params, schema_list
import asyncio

from remote_params.WebsocketServer import WebsocketServer
class TestWebsocketServer(unittest.TestCase):
  def test_default_port(self):
    s = WebsocketServer(Server(Params()), start=False)

    self.assertEqual(s.port, 8081)

  def test_incoming_value(self):
    params = Params()
    p1 = params.int('some_int')
    p1.set(0)
    s = Server(params)
    ws = WebsocketServer(s)

    async def receive_message():
      await ws.onMessage(f'POST /some_int?value={4}', None)

    self.run_async(receive_message)

    self.assertEqual(p1.value, 4)

  def run_async(self, func):
    # https://jacobbridges.github.io/post/unit-testing-with-asyncio/
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    coro = asyncio.coroutine(func)
    event_loop.run_until_complete(coro())
    event_loop.close()

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
