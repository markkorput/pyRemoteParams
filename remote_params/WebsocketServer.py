import logging, json
logger = logging.getLogger(__name__)

import asyncio, websockets, threading
from remote_params import Params, Server, Remote, schema_list #, create_sync_params, schema_list

DEFAULT_PORT = 8081

class WebsocketServer:
  def __init__(self, server: Server, port: int=DEFAULT_PORT, start: bool=True):
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
    """
    This method is ran for every incoming websocket connection.
    It'll register the websocket (add it to the internal list of sockets)
    And await incoming messages (basically be the async server/receiver for this)
    specific websocket and process incoming schema requests and value changes.
    """

    logging.info('New websocket connection...')
    self.register(websocket)

    try:
      await websocket.send("welcome to pyRemoteParams websockets")
      async for msg in websocket:
        await self.onMessage(msg, websocket)
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

  async def onMessage(self, msg, websocket):
    """
    onMessage is called with the connectionFunc to process
    incoming message from a specific websocket.
    """

    if msg == 'stop':
      logger.info('Websocket connection stopped')
      websocket.close()
      return

    if msg.startswith('GET schema.json'):
      logger.info('Got websocket schema request ({})'.format('GET schema.json'))
      # immediately respond
      data = schema_list(self.server.params)
      msg = 'POST schema.json?schema={}'.format(json.dumps(data))
      logger.debug('Websocket schema request response: ({})'.format(msg))
      await websocket.send(msg)
      return

    # POST <param-path>?value=<value>
    if msg.startswith('POST /') and '?value=' in msg:
      no_prefix = msg[len('POST '):] # assume no query in the url
      path, val = no_prefix.split('?value=')
      logger.info('Value received via websocket: {} = {}'.format(path, val))
      self.remote.valueEvent(path, val)
      return

    logger.warn('Received unknown websocket message: {}'.format(msg))

  async def sendToAllConnectedSockets(self, msg):
    """
    This method broadcasts the given msg to all connected websockets
    """
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

if __name__ == '__main__':
  import time
  from optparse import OptionParser

  def parse_args():
    parser = OptionParser()
    parser.add_option('-p', '--port', dest="port", default=8081, type='int')

    parser.add_option('-v', '--verbose', dest="verbose", action='store_true', default=False)
    parser.add_option('--verbosity', dest="verbosity", action='store_true', default='info')

    opts, args = parser.parse_args()
    lvl = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning':logging.WARNING, 'error':logging.ERROR, 'critical':logging.CRITICAL}['debug' if opts.verbose else str(opts.verbosity).lower()]
    logging.basicConfig(level=lvl)
    return opts, args

  opts, args = parse_args()


  logger.info(f'Starting websocket server on port: {opts.port}')
  # Create some vars to test with
  params = Params()
  params.string('name')
  params.float('score')
  params.float('range', min=0.0, max=100.0)
  params.int('level')
  params.bool('highest-score')

  s = WebsocketServer(Server(params), port=opts.port)
  try:
    while True:
      time.sleep(0.5)
  except KeyboardInterrupt:
    print("Received Ctrl+C... initiating exit")

  s.stop()
