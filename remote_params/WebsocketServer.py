import logging, json
logger = logging.getLogger(__name__)

import asyncio, websockets, threading
from remote_params import Params, Server, Remote, schema_list #, create_sync_params, schema_list

class WebsocketServer:
  def __init__(self, server: Server, port: int=8081, start: bool=True):
    self.server = server
    self.port = port
    self.thread = None
    self.sockets = set()

    self.remote = Remote()
    self.remote.sendValueEvent += self.onValueFromServer
    self.remote.sendSchemaEvent += self.onSchemaFromServer

    if start:
      self.start()

  def __del__(self):
    self.stop()
    self.remote.sendValueEvent -= self.onValueFromServer
    self.remote.sendSchemaEvent -= self.onSchemaFromServer

  def start(self):
    self.server.connect(self.remote)

    action = websockets.serve(self.connectionFunc, "127.0.0.1", self.port)
    eventloop = asyncio.get_event_loop()

    def func():
      eventloop.run_until_complete(action)
      eventloop.run_forever()

    thread = threading.Thread(target=func)
    thread.start()

  def stop(self):
    self.server.disconnect(self.remote)

    if not self.thread:
      return
    
    logger.debug('Trying to stop WebsocketServer thread')
    asyncio.get_event_loop().stop()
    self.thread.join()
    self.thread = None
    logger.debug('WebsocketServer thread stopped')

  async def connectionFunc(self, websocket, path):
    logging.info('New websocket connection...')
    self.register(websocket)

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
          logger.debug('Responding to schema request ({})'.format(msg))
          await websocket.send(msg)

        # POST <param-path>?value=<value>
        elif msg.startswith('POST /') and '?value=' in msg:
          no_prefix = msg[len('POST '):] # assume no query in the url
          path, val = no_prefix.split('?value=')
          logger.info('Value received via websocket: {} = {}'.format(path, val))
          self.remote.valueEvent(path, val)

        else:
          logger.warn('Received unknown websocket message: {}'.format(msg))
    except websockets.exceptions.ConnectionClosedError:
      logger.info('Connection closed.')
    finally:
      self.unregister(websocket)

  def register(self, websocket):
    self.sockets.add(websocket)
    logger.debug('registered websocket, {} active'.format(len(self.sockets)))

  def unregister(self, websocket):
    self.sockets.remove(websocket)
    logger.debug('unregistered websocket, {} left'.format(len(self.sockets)))

  async def sendToAllConnectedSockets(self, msg):
    logger.debug('sendToAllConnectedSockets: {} websocket remote(s): {}'.format(msg, len(self.sockets)))
    for websocket in self.sockets:
      await websocket.send(msg)

  def onValueFromServer(self, path, val):
    """
    This method gets called when our Remote instance gets notified by Server
    instance, about a param value-change. We'll send out the value-change
    to all connected websockets.
    """
    logger.debug('onValueFromServer(path={}, val={})'.format(path, val))
    msg = 'POST {}?value={}'.format(path, val)
    asyncio.ensure_future(self.sendToAllConnectedSockets(msg))

  def onSchemaFromServer(self, schemadata):
    """
    This method gets called when our Remote instance gets notified by Server
    instance, about a schema change. We'll send out the schmea change
    to all connected websockets.
    """
    msg = 'POST schema.json?schema={}'.format(json.dumps(schemadata))
    asyncio.ensure_future(self.sendToAllConnectedSockets(msg))

