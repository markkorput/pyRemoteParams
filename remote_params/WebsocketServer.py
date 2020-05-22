import logging, json
logger = logging.getLogger(__name__)

import asyncio, websockets, threading
from remote_params import Params, Server, Remote, schema_list #, create_sync_params, schema_list

DEFAULT_PORT = 8081

class WebsocketServer:
  """
  Connect a private Remote instance on a given params.Server instance
  Accepts new websocket connections.
  Broadcasts any value and schema change notifications from the server
  to all connected client at that moment.
  Forwards any value change from a connected client to the server.
  Respond to schema requests from a connected client with the schema
  schema information for the server's params.
  """

  def __init__(self, server: Server, host: str='0.0.0.0', port: int=DEFAULT_PORT, start: bool=True):
    self.server = server
    self.host = host
    self.port = port
    self.thread = None
    self.sockets = set()

    self.remote = Remote(serialize=True)
    self.remote.outgoing.sendValueEvent += self._onValueFromServer
    self.remote.outgoing.sendSchemaEvent += self._onSchemaFromServer

    self._ws_server = None

    if start:
      self.start()

  def __del__(self):
    self.stop()
    self.remote.outgoing.sendValueEvent -= self._onValueFromServer
    self.remote.outgoing.sendSchemaEvent -= self._onSchemaFromServer

  def start(self):
    """
    Connect private Remote instance to server
    Start websockets server coroutine in a separate thread
    """
    self.server.connect(self.remote)

    async_action = websockets.serve(self._connectionFunc, self.host, self.port)
    
    eventloop = asyncio.get_event_loop()

    def func():
      eventloop.run_until_complete(async_action)
      eventloop.run_forever()

    self.thread = threading.Thread(target=func)
    self.thread.start()

  async def start_async(self):
    """
    Connect private Remote instance to server
    Start websockets server coroutine.

    Returns
    -------
    websocket WebsocketServer instance
    """
    self.server.connect(self.remote)
    self._ws_server = await websockets.serve(self._connectionFunc, self.host, self.port)
    return self._ws_server

  def stop(self, joinThread=True):
    """
    
    Disconnect private remote instance form server.
    Closes start WebsocketServer is any.
    Wait for spawned thread to end if any and if `joinThread` is True.

    Parameter
    ---------
    joinThread: boolean
      When True, will wait for started thread to finish 
    """
    self.server.disconnect(self.remote)

    if self._ws_server:
      self._ws_server.close()
      self._ws_server = None

    if not self.thread:
      return

    # asyncio.get_event_loop().stop()
    if joinThread:
      print('joining thread')
      self.thread.join()
    self.thread = None
    logger.debug('WebsocketServer thread stopped')

  async def _connectionFunc(self, websocket, path):
    """
    This method runs for every incoming websocket connection.
    It registers the websocket (add it to self.sockets)
    It awaits and processes incoming messages
    It removes the websocket from self.sockets when the connection is closed
    """
    logging.info('New websocket connection...')
    self.sockets.add(websocket)
    logger.debug('registered websocket, {} active'.format(len(self.sockets)))

    try:
      await websocket.send("welcome to pyRemoteParams websockets")
      async for msg in websocket:
        await self._onMessage(msg, websocket)
    except websockets.exceptions.ConnectionClosedError:
      logger.info('Connection closed.')
    except KeyboardInterrupt:
      logger.warning('KeyboardInterrupt in WebsocketServer connectionFunc')
    finally:
      self.sockets.remove(websocket)

      logger.debug('unregistered websocket, {} left'.format(len(self.sockets)))

  async def _onMessage(self, msg, websocket):
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
      self.remote.incoming.valueEvent(path, val)
      return

    logger.warning('Received unknown websocket message: {}'.format(msg))

  def _onValueFromServer(self, path, val):
    """
    This method gets called when our Remote instance gets notified by Server
    instance, about a param value-change. We'll send out the value-change
    to all connected websockets.
    """
    logger.debug('onValueFromServer(path={}, val={})'.format(path, val))
    msg = 'POST {}?value={}'.format(path, val)
    asyncio.ensure_future(self._sendToAllConnectedSockets(msg))

  def _onSchemaFromServer(self, schemadata):
    """
    This method gets called when our Remote instance gets notified by Server
    instance, about a schema change. We'll send out the schema change
    to all connected websockets.
    """
    msg = 'POST schema.json?schema={}'.format(json.dumps(schemadata))
    asyncio.ensure_future(self._sendToAllConnectedSockets(msg))

  async def _sendToAllConnectedSockets(self, msg):
    """
    This method broadcasts the given msg to all connected websockets
    """
    logger.debug('sendToAllConnectedSockets: {} websocket remote(s): {}'.format(msg, len(self.sockets)))
    for websocket in self.sockets:
      await websocket.send(msg)



if __name__ == '__main__':
  """
  Example: serve bunch of params
  """
  import time
  from optparse import OptionParser

  def parse_args():
    parser = OptionParser()
    parser.add_option('-p', '--port', default=8081, type='int')
    parser.add_option('--host', default='0.0.0.0')

    parser.add_option('--no-async', action='store_true')
    parser.add_option('-v', '--verbose', action='store_true', default=False)
    parser.add_option('--verbosity', action='store_true', default='info')

    opts, args = parser.parse_args()
    lvl = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning':logging.WARNING, 'error':logging.ERROR, 'critical':logging.CRITICAL}['debug' if opts.verbose else str(opts.verbosity).lower()]
    logging.basicConfig(level=lvl)
    return opts, args

  async def main(host, port):
    logger.info(f'Starting websocket server on port: {port}')
    # Create some vars to test with
    params = Params()
    params.string('name').set('John Doe')
    params.float('score')
    params.float('range', min=0.0, max=100.0)
    params.int('level')
    params.bool('highest-score')
    voidParam = params.void('stop')

    gr = Params()
    gr.string('name').set('Jane Doe')
    gr.float('score')
    gr.float('range', min=0.0, max=100.0)
    gr.int('level')
    gr.bool('highest-score')

    params.group('parner', gr)
    
    wss = WebsocketServer(Server(params), host=host, port=port, start=False)
    await wss.start_async()

    try:
      while True:
        await asyncio.sleep(0.5)
        pass
    except KeyboardInterrupt:
      print("Received Ctrl+C... initiating exit")

    print('Stopping...')
    wss.stop()

  def main_sync(host, port):
    logger.info(f'Starting websocket server on port: {port}')
    # Create some vars to test with
    params = Params()
    params.string('name').set('John Doe')
    params.float('score')
    params.float('range', min=0.0, max=100.0)
    params.int('level')
    params.bool('highest-score')
    voidParam = params.void('stop')

    gr = Params()
    gr.string('name').set('Jane Doe')
    gr.float('score')
    gr.float('range', min=0.0, max=100.0)
    gr.int('level')
    gr.bool('highest-score')

    params.group('parner', gr)
    
    wss = WebsocketServer(Server(params), host=host, port=port)

    try:
      while True:
        time.sleep(0.5)
    except KeyboardInterrupt:
      print("Received Ctrl+C... initiating exit")

    print('Stopping...')
    wss.stop()

  opts, args = parse_args()

  if opts.no_async:
    main_sync(opts.host, opts.port)
  else:
    asyncio.run(main(opts.host, opts.port))
