
from .oscpy.client import OSCClient

import logging, json
from .server import Remote
from .schema import schema_list

logger = logging.getLogger(__name__)

class Client:
  '''
  This Client class performs all server-to-client OSC communications.
  The id given to the constructor specifies where all communications
  should be addressed to and should have the following format:
    '<host>:<port>'
    
    ie.

    '127.0.0.1:8082'

    or

    'localhost:6000'
  '''

  def __init__(self, server, id, prefix='/params'):
    self.send_raw = server.send

    parts = id.split(':')

    if len(parts) < 2 or not str(parts[1]).isdigit():
      logger.warning('[Connection.__init__] invalid response details: {}'.format(id))
      self.isValid = False
    else:
      self.host = parts[0]
      self.port = int(parts[1])
      self.isValid = True

    self.connect_confirm_addr = prefix+'/connect/confirm'
    self.disconnect_addr = prefix+'/disconnect'
    self.schema_addr = prefix+'/schema'
    self.value_addr = prefix+'/value'

  def send(self, addr, args=()):
    self.send_raw(self.host, self.port, addr, args)

  def sendValue(self, path, value):
    self.send(self.value_addr, (path, value))

  def sendSchema(self, data):
    if not self.isValid: return
    self.send(self.schema_addr, (json.dumps(data)))

  def sendConnectConfirmation(self, data):
    if not self.isValid: return
    self.send(self.connect_confirm_addr, (json.dumps(data)))

  def sendDisconnect(self):
    self.send(self.disconnect_addr)

class Connection:
  '''
  This responds to all server-to-client instructions from the Server
  and translates them into OSC actions
  '''
  def __init__(self, osc_server, id, connect=True):
    logger.debug('[Connection.__init__] id: {}'.format(id))
    self.osc_server = osc_server
    self.server = osc_server.server
    self.client = Client(osc_server, id)
    self.isActive = self.client.isValid and connect

    r = Remote()
    r.sendConnectConfirmationEvent += self.onConnectConfimToRemote
    r.sendValueEvent += self.onValueToRemote
    r.sendSchemaEvent += self.onSchemaToRemote
    r.sendDisconnectEvent += self.onDisconnectToRemote
    self.remote = r

    if self.isActive:
      self.server.connect(self.remote)

  def __del__(self):
    self.disconnect()

  def disconnect(self):
    self.osc_server = None # break circular dependency
    # self.osc_server.connections.remove(self)
    self.isActive = False

    if self.remote and self.server:
      self.server.disconnect(self.remote)

  def onValueToRemote(self, path, value):
    if not self.isActive: return
    self.client.sendValue(path, value)

  def onSchemaToRemote(self, schema_data):
    if not self.isActive: return
    self.client.sendSchema(schema_data)

  def onConnectConfimToRemote(self, schema_data):
    if not self.isActive: return
    self.client.sendConnectConfirmation(schema_data)

  def onDisconnectToRemote(self):
    logger.debug('[Connection.onDisconnectToRemote isActive={}]'.format(self.isActive))
    if not self.isActive: return
    self.disconnect()
    self.client.sendDisconnect()

def create_osc_listener(port=8000, callback=None):
  '''
  Create a threaded OSC server that listens for incoming UDP messages
  '''
  from .oscpy.server import OSCThreadServer

  logger.debug('[create_osc_listener port={}]'.format(port))

  def converter(addr, *args):
    logger.debug("[create_osc_listener.converter] addr={} args={}".format(addr, args))
    if callback:
      callback(addr.decode('utf-8'), args)

  osc = OSCThreadServer(advanced_matching=True, encoding='utf8')  # See sources for all the arguments
  sock = osc.listen(address='0.0.0.0', port=port, default=True)
  osc.bind_all(converter, get_address=True)

  def disconnect():
    osc.stop()  # Stop the default socket
    osc.stop_all()  # Stop all sockets

    # Here the server is still alive, one might call osc.listen() again
    osc.terminate_server()  # Request the handler thread to stop looping
    osc.join_server()

  return osc, disconnect

class OscServer:
  def __init__(self, server, prefix=None, capture_sends=None, listen=True):
    self.server = server
    self.capture_sends = capture_sends
    self.connections = []
    self.remote = Remote()
    # register our remote instance, through which we'll
    # inform the server about incoming information
    if self.server and self.remote:
      self.server.connect(self.remote)
  
    self.prefix = prefix if prefix else '/params'
    self.connect_addr = self.prefix+'/connect'
    self.disconnect_addr = self.prefix+'/disconnect'
    self.value_addr = self.prefix+'/value'
    self.schema_addr = self.prefix+'/schema'

    self.disconnect_listener = None
    if listen:
      server, disconnect = create_osc_listener(callback=self.receive)

      self.disconnect_listener = disconnect

  def __del__(self):
    # this triggers cleanup in destructor of the Connection instances
    self.connection = [] 
    if self.server and self.remote:
      self.server.disconnect(self.remote)

    for c in self.connections:
      c.disconnect()
    self.connections.clear()

    if self.disconnect_listener:
      self.disconnect_listener()

  def receive(self, addr, args):
    logger.debug('[OscServer.receive] addr={} args={}'.format(addr, args))
    if addr == self.value_addr:
      if len(args) == 2:
        self.onValueReceived(args[0], args[1])
      else:
        logger.warning('[OscServer.receive] received value message with invalid number ({}) of arguments: {}. Expecting two arguments (path and value)'.format(len(args), args))
      return

    if addr == self.connect_addr:
      if len(args) == 1:
        self.onConnect(args[0])
      else:
        logger.warning('[OscServer.receive] got connect message without host/port info')
      return
    
    if addr == self.schema_addr and len(args) == 1:
      self.onSchemaRequest(args[0])

  def send(self, host, port, addr, args=()):
    logger.debug('[OscServer.send host={} port={}] {} {}'.format(host,port,addr,args))
    # for debugging only, really
    if self.capture_sends:
      self.capture_sends(host, port, addr, args)
      return

    client = OSCClient(host, port)
    client.send_message(bytes(addr, 'utf-8'), args)

  def onConnect(self, response_info):
    connection = Connection(self, response_info)
    if connection.isActive:
      self.connections.append(connection)

  def onValueReceived(self, path, value):
    logger.debug('[OscServer.onValueReceived path={} value={}]'.format(path, value))
    # pass it on to the server through our remote instance
    self.remote.valueEvent(path, value)
  
  def onSchemaRequest(self, responseInfo):
    Client(self, responseInfo).sendSchema(schema_list(self.server.params))


if __name__ == '__main__':
  from .server import Server
  from .params import Params
  import time

  logging.basicConfig(level=logging.DEBUG)

  # Create params
  params = Params()
  def log(val): print(val)
  params.string('name').onchange(log)

  # Create Server and Osc server
  osc_server = OscServer(Server(params))

  try:
    print('Waiting for incoming messages')

    while True:
      time.sleep(0.1)

  except KeyboardInterrupt:
    print('[timer] KeyboardInterrupt, stopping.')
