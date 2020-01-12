from evento import Event
import logging

logger = logging.getLogger(__name__)

class Param:
  def __init__(self, id, type_):
    self.id = id
    self.type = type_
    self.value = None

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


class Params(list):
  def __init__(self):
    self.changeEvent = Event()
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
      item.changeEvent += onchange
    
    # another sub-params-group added?
    if isinstance(item, Params):
      def onchange():
        self.changeEvent()
      item.changeEvent += onchange
      
      pass
  
    self.changeEvent()

  def append_param(self, id, type_):
    p = Param(id, type_)
    self.append(id, p)
    return p

  def string(self, id):
    return self.append_param(id, 's')

  def int(self, id):
    return self.append_param(id, 'i')

  def bool(self, id):
    return self.append_param(id, 'b')

  def float(self, id):
    return self.append_param(id, 'f')

  def group(self, id, params):
    self.append(id, params)

  def get(self, id):
    return self.dict[id]
