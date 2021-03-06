from evento import Event
import logging, distutils, base64

try:
  import cv2
except:
  cv2 = None # not supported

try:
  import numpy as np
except:
  np = None # numpy not supported

logger = logging.getLogger(__name__)

class Param:

  class InvalidValue(ValueError):
    def __init__(self, value):
      ValueError.__init__(self, "Invalid value: {}".format(value))
      self.value = value

    @classmethod
    def isInvalid(cls, value):
      return isinstance(value, cls)

  def __init__(self, type_, default=None, opts={}, getter=None, setter=None):
    self.type = type_
    self.value = None
    self.default = default
    self.opts = opts if opts else {}
    self.getter = self._makeSafe(getter) if getter else None
    self.setter = self._makeSafe(setter) if setter else None

    self.changeEvent = Event()

  def set(self, value):
    if self.setter:
      settervalue = self.setter(value)
      if Param.InvalidValue.isInvalid(settervalue):
        logger.warning('[Param.set value={}] InvalidValue'.format(value))
        return

      value = settervalue

    # logger.debug('[Param.set value=`{}`]'.format(value))
    if self.equals(value, self.value):
      # logger.debug('equal')
      return
    
    self.value = value
    logger.debug('[Param.set] changevent')
    self.changeEvent()

  def equals(self, v1, v2):
    return v1 is v2
    # return v1 == v2

  def onchange(self, func):
    def funcWithValue():
      func(self.value)
    self.changeEvent += funcWithValue

  def is_initialized(self):
    return self.value is not None

  def val(self):
    v = self.value if self.is_initialized() else self.default
    return self.getter(v) if self.getter else v

  def to_dict(self):
    d = {'type': self.type}

    if self.is_initialized():
      d['value'] = self.value

    if self.opts and len(self.opts) > 0:
      d['opts'] = self.opts

    return d

  def _makeSafe(self, func):
    def safeFunc(val):
      try:
        val = func(val)
      except ValueError:
        val = self.value

      return val
    return safeFunc

def convertParamNumberVal(v, converter, fallback, opts={}):
  try:
    v = converter(v)
  except ValueError:
    logger.warning('Param could not convert value to int: {}'.format(v))
    v = fallback

  if v and 'min' in opts and opts['min'] and v < opts['min']:
    v = opts['min']
  elif v and 'max' in opts and opts['max'] and v > opts['max']:
    v = opts['max']

  return v

class IntParam(Param):
  def __init__(self, min=None, max=None):
    opts = {}
    if min != None: opts['min'] = convertParamNumberVal(min, int, None)
    if max != None: opts['max'] = convertParamNumberVal(max, int, None)
    Param.__init__(self, 'i', opts=opts, setter=self.convert)

  def convert(self, v):
    return convertParamNumberVal(v, int, self.value, self.opts)

class FloatParam(Param):
  def __init__(self, min=None, max=None):
    opts = {}
    if min != None: opts['min'] = convertParamNumberVal(min, float, None)
    if max != None: opts['max'] = convertParamNumberVal(max, float, None)

    Param.__init__(self, 'f',
      opts=opts,
      setter=self.convert)

  def convert(self, v):
    # print(f'converting: {v} with {self.opts}')
    vv = convertParamNumberVal(v, float, self.value, self.opts)
    # print(f'converting after: {vv}')
    return vv

class VoidParam(Param):
  def __init__(self):
    Param.__init__(self, 'v')
    self.value = 0

  def set(self, *value):
    Param.set(self, self.value + 1)

  def trigger(self):
    self.set(None)

  def ontrigger(self, func):
    self.changeEvent += func

class ImageParam(Param):
  def __init__(self, opts={}):
    Param.__init__(self, 'g', opts=opts)
  
  # def convert(self, v):
  #   if cv2 is not None and np is not None:
  #     if type(v) == type(np.array([])):
  #       # imparams = [cv2.IMWRITE_PNG_COMPRESSION, 9] # TODO: make configurable
  #       ret, img = cv2.imencode('.png', v) #, imparams)

  #       if not ret:
  #         logger.warning('cv2.imencode failed to encode image into png format')
  #         return None

  #       png_str = base64.b64encode(img).decode('ascii')
  #       # img = base64.b64decode(img.tostring()) #.encode('utf-8')
  #       # img = img.tostring().decode('utf-8')
  #       # png_str = str(img.tostring()) #str(img_str)

  #       logger.debug(f'Encoded image {len(png_str)}-bytes')
  #       return png_str

  #   # no supported image processor 
  #   return None

  def get_serialized(self):
    return self.serialize_value(self.val())

  def set_serialized(self, v) -> None:
    pass # TODO

  @staticmethod
  def serialize_value(value) -> str:
    if cv2 is not None and np is not None:
      if type(value) == type(np.array([])):
        # TODO: make configurable
        # imparams = [cv2.IMWRITE_PNG_COMPRESSION, 9] 
        ret, img = cv2.imencode('.png', value) #, imparams)

        if not ret:
          logger.warning('cv2.imencode failed to encode image into png format')
          return None

        png_str = base64.b64encode(img).decode('ascii')
        logger.debug(f'Encoded image to {len(png_str)}-bytes png string')
        return png_str

    # no supported image processor 
    return value

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
      params.valueChangeEvent('/'+id, item.val(), item)
    item.changeEvent += onchange
    
    # register cleanup logic
    def cleanup():
      item.changeEvent -= onchange
    cleanups.append(cleanup)

  # another sub-params-group added?
  if isinstance(item, Params):
    item.changeEvent += params.changeEvent.fire
    item.schemaChangeEvent += params.schemaChangeEvent.fire
    def forwardValChange(path, val, param):
      params.valueChangeEvent('/'+id+path, val, param)
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

  def append_param(self, id, type_, setter=None, opts={}):
    p = Param(type_, setter=setter, opts=opts)
    self.append(id, p)
    return p

  def string(self, id):
    return self.append_param(id, 's', setter=str)

  def int(self, id, min=None, max=None):
    return self.append(id, IntParam(min, max))

  def bool(self, id):
    def converter(v):
      if type(v) == type(True) or type(v) == type(False):
        return v
      if str(v).lower() in ['true', '1', 'yes', 'y']:
        return True
      if str(v).lower() in ['false', '0', 'no', 'n']:
        return False
      return Param.InvalidValue(v)

      # if distutils.util.strtobool(v) == 1 if 'util' in dir(distutils) else str(v) in ['True', 'true', '1'])

    return self.append_param(id, 'b', setter=converter)

  def float(self, id, min=None, max=None):
    return self.append(id, FloatParam(min, max))

  def void(self, id):
    return self.append(id, VoidParam())

  def image(self, id):
    return self.append(id, ImageParam())

  def group(self, id, params):
    self.append(id, params)

  def get(self, id):
    return self.items_by_id[id] if id in self.items_by_id else None

