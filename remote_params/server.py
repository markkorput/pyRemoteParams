from evento import Event
from .schema import schema_list

class Remote:
  def __init__(self, on_value=None, on_schema=None, on_connect_confirmation=None):
    self.valueEvent = Event()
    self.disconnectEvent = Event()
    self.confirmEvent = Event()

    self.on_value = on_value
    self.on_schema=on_schema
    self.on_connect_confirmation =on_connect_confirmation

  def send_value(self, path, value):
    if self.on_value:
      self.on_value(path, value)

  def send_schema(self, schema_data):
    if self.on_schema:
      self.on_schema(schema_data)

  def send_connect_confirmation(self, schema_data):
    if self.on_connect_confirmation:
      self.on_connect_confirmation(schema_data)

class Server:
  def __init__(self, params):
    self.params = params
    self.connected_remotes = []

  def connect(self, remote):
    # register handler when receiving value from remote
    def onVal(path, value):
      self.params.get_path(path).set(value)
    remote.valueEvent += onVal

    # register handler to forward value changes to remote
    def onValChange(path, value):
      # param = self.params.get_path(path)
      # param.set(value)
      for r in self.connected_remotes:
        r.send_value(path, value)
    self.params.valueChangeEvent += onValChange

    # add remote to our list
    self.connected_remotes.append(remote)

    # done, send confirmation
    remote.send_connect_confirmation(schema_list(self.params))

