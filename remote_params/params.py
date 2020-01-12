from evento import Event
import logging

logger = logging.getLogger(__name__)

class Param:
  def __init__(self, type_, default=None):
    self.type = type_
    self.value = None
    self.default = default

    self.changeEvent = Event()

  def set(self, value):
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
    return self.value if self.is_initialized() else self.default

  def to_dict(self):
    d = {'type': self.type}
    if self.is_initialized():
      d['value'] = self.value
    return d

class IntParam(Param):
  def __init__(self, min=None, max=None):
    Param.__init__(self, 'i')
    self.min = int(min) if min != None else None
    self.max = int(max) if max != None else None

  def to_dict(self):
    d = Param.to_dict(self)
    if self.min != None: d['min'] = self.min
    if self.max != None: d['max'] = self.max
    return d

  def set(self, v):
    if self.min != None and v < self.min:
      self.set(self.min)
      return
    if self.max != None and v > self.max:
      self.set(self.max)
      return

    Param.set(self, int(v))

class FloatParam(Param):
  def __init__(self, min=None, max=None):
    Param.__init__(self, 'f')
    self.min = float(min) if min != None else None
    self.max = float(max) if max != None else None

  def to_dict(self):
    return IntParam.to_dict(self)

  def set(self, v):
    if self.min != None and v < self.min:
      self.set(self.min)
      return
    if self.max != None and v > self.max:
      self.set(self.max)
      return

    Param.set(self, float(v))

class Params(list):
  def __init__(self):
    self.changeEvent = Event()
    self.schemaChangeEvent = Event()
    self.valueChangeEvent = Event()
    self.dict = {}

  def append(self, id, item):
    if id in self.dict:
      logging.warning('Params already has an item with ID: {}'.format(id))
      return

    self.dict[id] = item
    list.append(self, [id, item])

    # a single param added?
    if isinstance(item, Param):
      def onchange():
        self.changeEvent()
        self.valueChangeEvent('/'+id, item.val())
      item.changeEvent += onchange

    # another sub-params-group added?
    if isinstance(item, Params):
      item.changeEvent += self.changeEvent.fire
      item.schemaChangeEvent += self.schemaChangeEvent.fire
      def forwardValChange(path, val):
        self.valueChangeEvent('/'+id+path, val)
      item.valueChangeEvent += forwardValChange
  
    self.schemaChangeEvent()
    self.changeEvent()
    return item

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
    return self.dict[id]

  def get_path(self, path):
    parts = path.split('/')[1:]
    current = self

    for p in parts:
      current = current.get(p)

    return current
