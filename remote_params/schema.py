from remote_params import Param, Params
def schema_list(params):
  result = []
  for pair in params:
    id, item = pair
    schema_list_append(result, '/', id, item)
  return result

def schema_list_append(schema, scope, id, item):
  if isinstance(item, Param):
    info = {'path': scope+id, 'type':item.type}
    if item.is_initialized():
      info['value'] = item.val()
    schema.append(info)
    return
  
  if isinstance(item, Params):
    for pair in item:
      sub_id, sub_item = pair
      schema_list_append(schema, scope+id+'/', sub_id, sub_item)
