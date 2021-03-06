import logging
from .params import Param, Params, IntParam, FloatParam, ImageParam


logger = logging.getLogger(__name__)

def schema_list(params):
  result = []
  for pair in params:
    id, item = pair
    schema_list_append(result, '/', id, item)
  return result

def schema_list_append(schema, scope, id, item):
  if isinstance(item, Param):
    info = item.to_dict()
    info['path'] = scope+id
    if 'value' in info and item.type == 'g':
      info['value'] = ImageParam.serialize_value(info['value'])
    schema.append(info)
    return
  
  if isinstance(item, Params):
    for pair in item:
      sub_id, sub_item = pair
      schema_list_append(schema, scope+id+'/', sub_id, sub_item)

def get_path(params, path):
  parts = path.split('/')[1:]
  current = params

  for p in parts:
    if not current:
      return None
    current = current.get(p)

  return current

def set_path(params, path, param):
  parent_ids = '/'.join(path.split('/')[1:-1])
  current = params
  for id in parent_ids:
    current = current.get(id)
    if not current or not isinstance(current, Params):
      logger.warning('[set_path path=`{}`] could not set path because parent {} is not a Params group'.format(path, id))
      return
  
  param_id = path.split('/')[-1]
  current.append(param_id, param)

def remove_path(params, path):
  logger.debug('[remove_path] path={}'.format(path))
  parent_path = '/'.join(path.split('/')[0:-1])
  param_id = path.split('/')[-1]

  parent = params.get(parent_path)
  if not parent:
    logger.warning('[remove_path] could not find parent with path: {}'.format(parent_path))
    return

  parent.remove(param_id)

def create_param(param_data):
  if not 'type' in param_data:
    return None

  if param_data['type'] == 'i':
    return IntParam(
      min=param_data['min'] if 'min' in param_data else None,
      max=param_data['max'] if 'max' in param_data else None)

  if param_data['type'] == 'f':
    return FloatParam(
      min=param_data['min'] if 'min' in param_data else None,
      max=param_data['max'] if 'max' in param_data else None)

  return Param(param_data['type'])

def update_param(param, param_data):
  if 'value' in param_data:
    param.set(param_data['value'])
  # TODO; also apply config changes like min/max/default?

def apply_schema_list(params, schema_data):
  logger.debug('[apply_schema_list] schema_data={}'.format(schema_data))

  def add_new_items_and_values(params, schema_data):
    for param_data in schema_data:
      param = get_path(params, param_data['path'])
      
      # create if doesn't exist
      if not param:
        param = create_param(param_data)
        set_path(params, param_data['path'], param)

      # update (apply value etc.)
      update_param(param, param_data)

  def remove_items_not_in_schema_list(params, schema_data):
    dummy = Params()
    add_new_items_and_values(dummy, schema_data)

    # loop over all items in schema
    for item in schema_list(params):
      # if specified item doesn't appear in dummy
      if not get_path(dummy, item['path']):
        remove_path(params, item['path'])


  add_new_items_and_values(params, schema_data)
  remove_items_not_in_schema_list(params, schema_data)

def get_values(params):
  values = {}

  for pair in params:
    id, item = pair

    if isinstance(item, Param):
      if item.type == 'g':
        values[id] = item.get_serialized()
      else:
        values[id] = item.val()
    
    if isinstance(item, Params):
      values[id] = get_values(item)

  return values

def set_values(params, vals):
  for k, v in vals.items():
    param = params.get(k)

    if param is None:
      continue

    if type(v) is dict:
      set_values(param, v)
    else:
      if param.type == 'g':
        param.set_serialized(v)
      else:
        param.set(v)

