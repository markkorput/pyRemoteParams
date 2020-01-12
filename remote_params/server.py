from evento import Event
from .schema import schema_list
import logging

logger = logging.getLogger(__name__)

class Remote:
  def __init__(self, on_value=None, on_schema=None, on_connect_confirmation=None, on_disconnect=None):
    # the events notify other components (like Server) about incoming data from the remote
    self.valueEvent = Event()
    self.disconnectEvent = Event()
    self.confirmEvent = Event()

    # option hooks to handle outgoing data actions
    self.on_value = on_value
    self.on_schema=on_schema
    self.on_connect_confirmation =on_connect_confirmation
    self.on_disconnect = on_disconnect

  def send_value(self, path, value):
    '''
    Use this method to notify the connected client about
    a single param value change
    '''
    if self.on_value:
      self.on_value(path, value)

  def send_schema(self, schema_data):
    '''
    Use this method to send schema data
    to a remote client
    '''
    if self.on_schema:
      self.on_schema(schema_data)

  def send_connect_confirmation(self, schema_data=None):
    '''
    Use this method to send a connect confirmation
    to a connecting remote client
    '''
    if self.on_connect_confirmation:
      self.on_connect_confirmation(schema_data)

  def send_disconnect(self):
    '''
    Use this notify/confirm disconnect to the Remote
    '''
    if self.on_disconnect:
      self.on_disconnect

class Server:
  def __init__(self, params):
    self.params = params
    self.connected_remotes = []

    self.params.schemaChangeEvent += self.broadcast_schema
    self.params.valueChangeEvent += self.broadcast_value_change

  def __del__(self):
    self.params.schemaChangeEvent -= self.broadcast_schema
    self.params.valueChangeEvent -= self.broadcast_value_change

    for r in self.connected_remotes:
      self.disconnect(r)

  def broadcast_schema(self):
    logger.debug('[Server.broadcast_schema]')
    schema_data = schema_list(self.params)
    for r in self.connected_remotes:
      remote.send_schema(schema_data)

  def broadcast_value_change(self, path, value):
    logger.debug('[Server.broadcast_value_change]')
    for r in self.connected_remotes:
      r.send_value(path, value)

  def connect(self, remote):
    logger.debug('[Server.connect]')

    # register handler when receiving value from remote
    def value_handler(path, value):
      logger.debug('[Server.connect.value_handler remote={}]'.format(remote))
      self.handle_remote_value_change(remote, path, value)
    remote.valueEvent += value_handler

    # add remote to our list
    self.connected_remotes.append(remote)

    # done, send confirmation
    remote.send_connect_confirmation(schema_list(self.params))

  def disconnect(self, remote):
    remote.send_disconnect()  
    self.connected_remotes.remove(remote)

  def handle_remote_value_change(self, remote, path, value):
    self.params.get_path(path).set(value)
