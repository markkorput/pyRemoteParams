import logging, os.path


from .http_utils import HttpServer as UtilHttpServer
from remote_params import Params, Server, Remote #, create_sync_params, schema_list

logger = logging.getLogger(__name__)

import asyncio, websockets, threading

class HttpServer:
  def __init__(self, server, port=8080, startServer=True):
    self.server = server
    self.remote = Remote()

    # register our remote instance through which we'll
    # inform the server about incoming information
    if self.server and self.remote:
      self.server.connect(self.remote)

    self.httpServer = UtilHttpServer(port=port, start=False)
    self.httpServer.requestEvent += self.onHttpRequest

    self.websocketServerThread = None
    
    self.uiHtmlFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__),'ui.html'))

    if startServer:
      self.start()

  def __del__(self):
    if self.server and self.remote:
      self.server.disconnect(self.remote)

  def start(self):
    logger.info('Starting HTTP server on port: {}'.format(self.httpServer.port))
    self.httpServer.startServer()
    
    logger.info('Starting Websockets server on port {}'.format(self.httpServer.port+1))
    self.websocketServerThread = self.createWebsocketThread(self.httpServer.port+1)

  def stop(self):
    if self.websocketServerThread:
      logger.debug('Trying to stop websocket thread')
      asyncio.get_event_loop().stop()
      self.websocketServerThread.join()
      logger.debug('Websocket thread stopped')
      self.websocketServer = None

    self.httpServer.stopServer()

  def onHttpRequest(self, req):
    # logger.info('HTTP req: {}'.format(req))
    # logger.info('HTTP req path: {}'.format(req.path))

    if req.path == '/':
      logger.debug('Responding with ui file: {}'.format(self.uiHtmlFilePath))
      req.respondWithFile(self.uiHtmlFilePath)
      # req.respond(200, b'TODO: respond with html file')
      return

    if self.onPathRequest(req.path):
      req.respond(200, b'ok')
      return

    req.respond(404, b'WIP')

  def createWebsocketThread(self, port=8081, start=True):
    action = websockets.serve(self._websockconnectionfunc, "127.0.0.1", port)
    eventloop = asyncio.get_event_loop()

    def func():
      eventloop.run_until_complete(action)
      eventloop.run_forever()

    thread = threading.Thread(target=func)
    if start:
      thread.start()
    return thread

  async def _websockconnectionfunc(self, websocket, path):
    logging.info('New websocket connection...')

    await websocket.send("welcome to pyRemoteParams websockets")

    ended = False
    while not ended:
      # msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
      msg = await websocket.recv()

      if msg == 'stop':
        logger.info('Websocket connection stopped')
        ended = True
        continue

      # fake some sort of HTTP-like format, so http server
      # and websocket share the onPathRequest handler
      if msg.startswith('GET /'):
        path = msg[4:] # assume no query in the url
        res = self.onPathRequest(path)
        if res:
          # respond 'OK: '+<original message>
          await websocket.send('OK: {}'.format(msg))
          continue

    
      logger.warn('Received unknown websocket message: {}'.format(msg))
      


  def onPathRequest(self, path):
    logger.info('onPathRequest: {}'.format(path))

    if path == '/params/value':
      # TODO
      return True

    return False
