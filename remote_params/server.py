from evento import Event
from .params import Params
from .schema import schema_list, get_path, apply_schema_list
import logging

logger = logging.getLogger(__name__)

class Remote:
  def __init__(self):
    # events for remote-to-server communications
    self.valueEvent = Event()
    self.disconnectEvent = Event()
    self.confirmEvent = Event()
    self.requestSchemaEvent = Event()

    # events notifying about server-to-remote communications
    self.sendValueEvent = Event()
    self.sendSchemaEvent = Event()
    self.sendConnectConfirmationEvent = Event()
    self.sendDisconnectEvent = Event()

  def send_value(self, path, value):
    '''
    Use this method to notify the connected client about
    a single param value change
    '''
    self.sendValueEvent(path, value)

  def send_schema(self, schema_data):
    '''
    Use this method to send schema data
    to a remote client
    '''
    self.sendSchemaEvent(schema_data)

  def send_connect_confirmation(self, schema_data=None):
    '''
    Use this method to send a connect confirmation
    to a connecting remote client
    '''
    self.sendConnectConfirmationEvent(schema_data)

  def send_disconnect(self):
    '''
    Use this notify/confirm disconnect to the Remote
    '''
    self.sendDisconnectEvent()

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
      r.send_schema(schema_data)

  def broadcast_value_change(self, path, value):
    logger.debug('[Server.broadcast_value_change]')
    for r in self.connected_remotes:
      r.send_value(path, value)

  def connect(self, remote):
    logger.debug('[Server.connect]')

    # register handler when receiving value from remote
    def value_handler(path, value):
      logger.debug('[Server.connect.value_handler]')
      self.handle_remote_value_change(remote, path, value)
    remote.valueEvent += value_handler

    # register handler when receiving schema request from remote
    def schema_request_handler():
      logger.debug('[Server.connect.schema_request_handler]')
      self.handle_remote_schema_request(remote)
    remote.requestSchemaEvent += schema_request_handler

    # add remote to our list
    self.connected_remotes.append(remote)

    # done, send confirmation
    remote.send_connect_confirmation(schema_list(self.params))

  def disconnect(self, remote):
    remote.send_disconnect()  
    self.connected_remotes.remove(remote)

  def handle_remote_value_change(self, remote, path, value):
    logger.debug('[Server.handle_remote_value_change]')
    get_path(self.params, path).set(value)

  def handle_remote_schema_request(self, remote):
    logger.debug('[Server.handle_remote_schema_request]')
    schema_data = schema_list(self.params)
    remote.send_schema(schema_data)

def create_sync_params(remote, request_initial_schema=True):
  '''
  Create an instance of Params, which is updated with information
  received by the given remote
  '''
  params = Params()

  # catch incoming schema data and apply it
  def onSchema(schema_data):
    logger.debug('[create_sync_params.onSchema] schema_data={}'.format(schema_data))
    apply_schema_list(params, schema_data)

  remote.sendSchemaEvent += onSchema

  # request schema data
  if request_initial_schema:
    remote.requestSchemaEvent()

  return params
