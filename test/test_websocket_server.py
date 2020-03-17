
#!/usr/bin/env python
import unittest
from remote_params import HttpServer, Params, Server, Remote, create_sync_params, schema_list

from remote_params.WebsocketServer import WebsocketServer
class TestWebsocketServer(unittest.TestCase):
  def test_default_port(self):
    s = WebsocketServer(Server(Params()), start=False)

    self.assertEqual(s.port, 8081)

# run just the tests in this file
if __name__ == '__main__':
    unittest.main()
