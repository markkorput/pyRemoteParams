import logging, os.path, json


from .http_utils import HttpServer as UtilHttpServer
from remote_params import Params, Server, Remote, schema_list #, create_sync_params, schema_list

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

    def onValueFromServer(path, val):
      msg = 'POST {}?value={}'.format(path, val)
      logger.info('Sending value to websocket remote: {}'.format(msg))
      websocket.send(msg)
      # await websocket.send(msg)

    def onSchemaFromServer(schemadata):
      msg = 'POST schema.json?schema={}'.format(json.dumps(schemadata))
      logger.info('Sending schema data to websocket remote: {}'.format(msg))
      websocket.send(msg)

    self.remote.sendValueEvent += onValueFromServer
    self.remote.sendSchemaEvent += onSchemaFromServer

    await websocket.send("welcome to pyRemoteParams websockets")

    ended = False
    while not ended:
      # msg = await asyncio.wait_for(websocket.recv(), timeout=1.0)
      msg = await websocket.recv()

      if msg == 'stop':
        logger.info('Websocket connection stopped')
        ended = True
        continue

      if msg.startswith('GET schema.json'):
        logger.info('Got schema request ({})'.format('GET schema.json'))
        data = schema_list(self.server.params)
        msg = 'POST schema.json?schema={}'.format(json.dumps(data))
        logger.info('Responding to schema request ({})'.format(msg))
        await websocket.send(msg)
        continue

      # POST <param-path>?value=<value>
      if msg.startswith('POST /') and '?value=' in msg:
        no_prefix = msg[len('POST '):] # assume no query in the url
        path, val = no_prefix.split('?value=')
        logger.info('Setting value received from remote: {} = {}'.format(path, val))
        self.remote.valueEvent(path, val)
        continue

      # fake some sort of HTTP-like format, so http server
      # and websocket share the onPathRequest handler
      if msg.startswith('GET /'):
        path = msg[4:] # assume no query in the url
        res = self.onGetRequest(path)
        if res:
          # respond 'OK: '+<original message>
          await websocket.send('OK: {}'.format(msg))
          continue
    
      logger.warn('Received unknown websocket message: {}'.format(msg))


  def onGetRequest(self, path):
    logger.info('onPathRequest: {}'.format(path))

    if path == '/params/value':
      # TODO
      return True

    return False
