
from oscpy.client import OSCClient
import logging, json
from .server import Remote

logger = logging.getLogger(__name__)

class Connection:
  def __init__(self, osc_server, id):
    self.osc_server = osc_server
    self.server = osc_server.server
    self.id = id

    parts = id.split(':')

    if len(parts) < 2 or not str(parts[1]).isdigit():
      logger.warning('[Connection.__init__] invalid response details: {}'.format(id))
      self.isValid = False
    else:
      self.host = parts[0]
      self.port = int(parts[1])
      self.isValid = True
    
    self.remote = self.create_remote_instance()
    self.isActive = self.isValid
    
    if self.isValid and self.isActive:
      self.server.connect(self.remote)

  def __del__(self):
    if self.remote and self.server:
      self.server.disconnect(self.remote)


  # def send_connect_confirmation(self):
  #   self.server.send(self.host, self.port, self.server.connect_confirm_addr, )

  def create_remote_instance(self):
    r = Remote()
    r.sendConnectConfirmationEvent += self.onConnectConfimToRemote
    r.sendValueEvent += self.onValueToRemote
    r.sendSchemaEvent += self.onSchemaToRemote
    r.sendDisconnectEvent += self.onDisconnectToRemote
    return r

  def send(self, addr, args=()):
    self.osc_server.send(self.host, self.port, addr, args)

  def onValueToRemote(self, path, value):
    self.send(self.osc_server.value_addr, (path, value))

  def onSchemaToRemote(self, schema_data):
    self.send(self.osc_server.schema_addr, (json.dumps(schema_data)))

  def onConnectConfimToRemote(self, schema_data):
    self.send(self.osc_server.connect_confirm_addr, (json.dumps(schema_data)))

  def onDisconnectToRemote(self):
    self.send(self.osc_server.disconnect_addr)
    self.isActive = False
    self.osc_server.connections.remove(self)
    self.osc_server = None # break circular dependency

class OscServer:
  def __init__(self, server, prefix=None, capture_sends=None):
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
    self.connect_confirm_addr = self.prefix+'/connect/confirm'
    self.value_addr = self.prefix+'/value'
    self.schema_addr = self.prefix+'/schema'

  def __del__(self):
    # this triggers cleanup in destructor of the Connection instances
    self.connection = [] 
    if self.server and self.remote:
      self.server.disconnect(self.remote)

  def receive(self, addr, args):
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
    if connection.isValid:
      self.connections.append(connection)

  def onValueReceived(self, path, value):
    logger.debug('[OscServer.onValueReceived path={} value={}]'.format(path, value))
    # pass it on to the server through our remote instance
    self.remote.valueEvent(path, value)
    