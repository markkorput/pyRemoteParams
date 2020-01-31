import logging, os.path, json


from .http_utils import HttpServer as UtilHttpServer
from remote_params import Params, Server, Remote, schema_list #, create_sync_params, schema_list

logger = logging.getLogger(__name__)

import asyncio, websockets, threading

class HttpServer:
  def __init__(self, server, port=8080, startServer=True):
    self.server = server
    self.remote = Remote()

    self.remote.sendValueEvent += self.onValueFromServer
    self.remote.sendSchemaEvent += self.onSchemaFromServer

    # register our remote instance through which we'll
    # inform the server about incoming information
    if self.server and self.remote:
      self.server.connect(self.remote)

    self.httpServer = UtilHttpServer(port=port, start=False)
    self.httpServer.requestEvent += self.onHttpRequest

    self.websocketServerThread = None
    self.activeWebsockets = set()

    self.uiHtmlFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__),'ui.html'))

    if startServer:
      self.start()

  def __del__(self):
    if self.server and self.remote:
      self.server.disconnect(self.remote)

    self.remote.sendValueEvent -= self.onValueFromServer
    self.remote.sendSchemaEvent -= self.onSchemaFromServer


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

    if self.onGetRequest(req.path):
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
    await self.register(websocket)

    try:
      await websocket.send("welcome to pyRemoteParams websockets")
      async for msg in websocket:
        if msg == 'stop':
          logger.info('Websocket connection stopped')
          websocket.close()

        elif msg.startswith('GET schema.json'):
          logger.info('Got schema request ({})'.format('GET schema.json'))
          data = schema_list(self.server.params)
          msg = 'POST schema.json?schema={}'.format(json.dumps(data))
          logger.info('Responding to schema request ({})'.format(msg))
          await websocket.send(msg)

        # POST <param-path>?value=<value>
        elif msg.startswith('POST /') and '?value=' in msg:
          no_prefix = msg[len('POST '):] # assume no query in the url
          path, val = no_prefix.split('?value=')
          logger.info('Setting value received from remote: {} = {}'.format(path, val))
          self.remote.valueEvent(path, val)

        # # fake some sort of HTTP-like format, so http server
        # # and websocket share the onPathRequest handler
        # elif msg.startswith('GET /'):
        #   path = msg[4:] # assume no query in the url
        #   res = self.onGetRequest(path)
        #   if res:
        #     # respond 'OK: '+<original message>
        #     await websocket.send('OK: {}'.format(msg))
        #   else:

        else:
          logger.warn('Received unknown websocket message: {}'.format(msg))
    except websockets.exceptions.ConnectionClosedError:
      logger.info('Connection closed.')
    finally:
      await self.unregister(websocket)

  async def register(self, websocket):
    self.activeWebsockets.add(websocket)
    logger.info('registered websocket, {} active'.format(len(self.activeWebsockets)))

  async def unregister(self, websocket):
    
    self.activeWebsockets.remove(websocket)
    logger.info('unregistered websocket, {} left'.format(len(self.activeWebsockets)))

  def onValueFromServer(self, path, val):
    msg = 'POST {}?value={}'.format(path, val)

    async def send():
      logger.info('Sending value to {} websocket remote(s): {}'.format(len(self.activeWebsockets), msg))
      for websocket in self.activeWebsockets:      
        
        websocket.send(msg)

      asyncio.wait(send)

  def onSchemaFromServer(self, schemadata):
    msg = 'POST schema.json?schema={}'.format(json.dumps(schemadata))

    async def send():
      logger.info('Sending schema to {} websocket remote(s): {}'.format(len(self.activeWebsockets), msg))
      for websocket in self.activeWebsockets:
        websocket.send(msg)

      asyncio.wait(send)

  def onGetRequest(self, path):
    logger.info('onPathRequest: {}'.format(path))

    if path == '/params/value':
      # TODO
      return True

    return False
