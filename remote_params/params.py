from evento import Event
import logging

logger = logging.getLogger(__name__)

class Param:
  def __init__(self, type_, default=None, opts={}, getter=None, setter=None):
    self.type = type_
    self.value = None
    self.default = default
    self.opts = opts if opts else {}
    self.getter = getter
    self.setter = setter

    self.changeEvent = Event()

  def set(self, value):
    if self.setter:
      value = self.setter(value)
      
    logger.debug('[Param.set value=`{}`]'.format(value))
    if self.equals(value, self.value):
      return

    self.value = value
    self.changeEvent()

  def equals(self, v1, v2):
    return v1 == v2

  def onchange(self, func):
    def funcWithValue():
      func(self.value)
    self.changeEvent += funcWithValue

  def is_initialized(self):
    return self.value != None

  def val(self):
    v = self.value if self.is_initialized() else self.default
    return self.getter(v) if self.getter else v

  def to_dict(self):
    d = {'type': self.type}
    if self.is_initialized():
      d['value'] = self.value
    d.update(self.opts)
    return d

def convertParamNumberVal(v, converter, fallback, opts):
  try:
    v = converter(v)
  except ValueError:
    logger.warn('Param could not convert value to int: {}'.format(v))
    v = fallback

  if v and 'min' in opts and opts['min'] and v < opts['min']:
    v = opts['min']
  elif v and 'max' in opts and opts['min'] and v > opts['max']:
    v = opts['max']

  return v

class IntParam(Param):
  def __init__(self, min=None, max=None):
    Param.__init__(self, 'i', opts={'min':min, 'max':max}, setter=self.convert)

  def convert(self, v):
    return convertParamNumberVal(v, int, self.value, self.opts)

class FloatParam(Param):
  def __init__(self, min=None, max=None):
    Param.__init__(self, 'f',
      opts={'min':min, 'max':max},
      setter=self.convert)

  def convert(self, v):
    return convertParamNumberVal(v, float, self.value, self.opts)

def create_child(params, id, item):
  '''
  This function performs all logic for adding a new item (param or sub-params-group)
  to a Params groups and returns a single function the performs all cleanups for removing the item
  '''
  cleanups = []

  # add
  params.items_by_id[id] = item
  list.append(params, [id, item])
  # create remover
  def remover():
    del params.items_by_id[id]
    for pair in params:
      key, val = pair
      if val == item:
        list.remove(params, pair)

    params.schemaChangeEvent()
    params.changeEvent()
  cleanups.append(remover)

  # a single param added?
  if isinstance(item, Param):
    def onchange():
      params.changeEvent()
      params.valueChangeEvent('/'+id, item.val())
    item.changeEvent += onchange
    
    # register cleanup logic
    def cleanup():
      item.changeEvent -= onchange
    cleanups.append(cleanup)

  # another sub-params-group added?
  if isinstance(item, Params):
    item.changeEvent += params.changeEvent.fire
    item.schemaChangeEvent += params.schemaChangeEvent.fire
    def forwardValChange(path, val):
      params.valueChangeEvent('/'+id+path, val)
    item.valueChangeEvent += forwardValChange

    # record cleanup logic
    def cleanup():
      item.valueChangeEvent -= forwardValChange
    cleanups.append(cleanup)

  params.schemaChangeEvent()
  params.changeEvent()

  def cleanup():
    for c in cleanups:
      c()

  return cleanup

class Params(list):
  def __init__(self):
    self.changeEvent = Event()
    self.schemaChangeEvent = Event()
    self.valueChangeEvent = Event()

    self.items_by_id = {}
    self.removers = {}

  def __del__(self):
    for id in self.removers:
      remover =self.removers[id]
      remover()

    self.removers = {}

  def append(self, id, item):
    if id in self.removers:
      logging.warning('Params already has an item with ID: {}'.format(id))
      return

    # create_child returns a single function which removes
    # the child relationship again, which we save for calls to self.remove
    remover = create_child(self, id, item)
    self.removers[id] = remover
    return item

  def remove(self, id):
    if not id in self.removers:
      logging.warning('[Params.remove] could not find item with id `{}` to remove'.format(id))
      return

    # find remover (are created in self.append)
    remover = self.removers[id]
    del self.removers[id]
    # run remover
    remover()

  def append_param(self, id, type_):
    p = Param(type_)
    self.append(id, p)
    return p

  def string(self, id):
    return self.append_param(id, 's')

  def int(self, id, min=None, max=None):
    return self.append(id, IntParam(min, max))

  def bool(self, id):
    return self.append_param(id, 'b')

  def float(self, id, min=None, max=None):
    return self.append(id, FloatParam(min, max))

  def group(self, id, params):
    self.append(id, params)

  def get(self, id):
    return self.items_by_id[id] if id in self.items_by_id else None
