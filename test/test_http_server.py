#!/usr/bin/env python
import unittest
import json
from remote_params import Params, Server, Remote, create_sync_params, schema_list

# class TestOsc(unittest.TestCase):
#   def test_osc_server_choreography(self):

# run just the tests in this file
# if __name__ == '__main__':
#     unittest.main()

import logging
from remote_params.http import HttpServer as _HttpServer

logger = logging.getLogger(__name__)

class HttpServer:
  def __init__(self, server, startServer=True):
    self.server = server
    self.remote = Remote()

    # register our remote instance through which we'll
    # inform the server about incoming information
    if self.server and self.remote:
      self.server.connect(self.remote)

    self.httpServer = _HttpServer(start=False)
    self.httpServer.requestEvent += self.onHttpRequest
    
    if startServer:
      self.start()

  def __del__(self):
    if self.server and self.remote:
      self.server.disconnect(self.remote)

  def start(self):
    self.httpServer.startServer()

  def stop(self):
    self.httpServer.stopServer()

  def onHttpRequest(self, req):
    logger.info('HTTP req: {}'.format(req))

    req.respond(404, b'WIP')

if __name__ == '__main__':
  params = Params()
  params.string('name')
  HttpServer(Server(params))