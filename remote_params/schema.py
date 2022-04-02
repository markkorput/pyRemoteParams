import logging
from typing import Any, Optional, Union

from .params import FloatParam, ImageParam, IntParam, Param, Params

logger = logging.getLogger(__name__)

SchemaData = list[dict[str, Any]]


def schema_list(params: Params) -> SchemaData:
    return [
        subitem for id, item in params.items() for subitem in _schema_list_scoped("/", id, item)
    ]


def _schema_list_scoped(scope: str, id: str, item: Union[Param[Any], Params]) -> SchemaData:
    if isinstance(item, Param):
        info = item.to_dict()
        info["path"] = scope + id
        if "value" in info and item.type == "g":
            info["value"] = ImageParam.serialize_value(info["value"])
        return [info]

    return [
        subitem
        for sub_id, sub_item in item.items()
        for subitem in _schema_list_scoped(scope + id + "/", sub_id, sub_item)
    ]


def set_path(params: Params, path: str, param: Param[Any]) -> None:
    parent_ids = "/".join(path.split("/")[1:-1])
    current = params
    for id in parent_ids:
        item = current.get(id)
        if not isinstance(item, Params):
            logger.warning(
                "[set_path path=`{}`] could not set path because parent {} is not a Params group"
                .format(path, id)
            )
            return

        current = item

    param_id = path.split("/")[-1]
    current.append(param_id, param)


def remove_path(params: Params, path: str) -> None:
    logger.debug("[remove_path] path={}".format(path))
    parent_path = "/".join(path.split("/")[0:-1])
    param_id = path.split("/")[-1]

    parent = params.get(parent_path)
    if not parent or not isinstance(parent, Params):
        logger.warning("[remove_path] could not find parent with path: {}".format(parent_path))
        return

    parent.remove(param_id)


def create_param(param_data: dict[str, Any]) -> Optional[Param[Any]]:
    if "type" not in param_data:
        return None

    if param_data["type"] == "i":
        return IntParam(
            min=param_data["min"] if "min" in param_data else None,
            max=param_data["max"] if "max" in param_data else None,
        )

    if param_data["type"] == "f":
        return FloatParam(
            min=param_data["min"] if "min" in param_data else None,
            max=param_data["max"] if "max" in param_data else None,
        )

    return Param(param_data["type"])


def update_param(param: Param[Any], param_data: dict[str, Any]) -> None:
    if value := param_data.get("value", None):
        param.set(value)

    # TODO; also apply config changes like min/max/default?


def apply_schema_list(params: Params, schema_data: SchemaData) -> None:
    logger.debug("[apply_schema_list] schema_data={}".format(schema_data))

    def add_new_items_and_values(params: Params, schema_data: SchemaData) -> None:
        for param_data in schema_data:
            param = params.get_path(param_data["path"])

            # create if doesn't exist
            if not param:
                param = create_param(param_data)
                if param:
                    set_path(params, param_data["path"], param)

            if isinstance(param, Param):
                # update (apply value etc.)
                update_param(param, param_data)

    def remove_items_not_in_schema_list(params: Params, schema_data: SchemaData) -> None:
        dummy = Params()
        add_new_items_and_values(dummy, schema_data)

        # loop over all items in schema
        for item in schema_list(params):
            # if specified item doesn't appear in dummy
            if not dummy.get_path(item["path"]):
                remove_path(params, item["path"])

    add_new_items_and_values(params, schema_data)
    remove_items_not_in_schema_list(params, schema_data)


def get_values(params: Params) -> dict[str, Any]:
    values: dict[str, Any] = {}

    for id, item in params.items():
        # TODO: not responsibility of schema
        if isinstance(item, ImageParam):
            values[id] = item.get_serialized()
        elif isinstance(item, Param):
            values[id] = item.val()
        else:
            values[id] = get_values(item)

    return values


def set_values(params: Params, vals: dict[str, Any]) -> None:
    for k, v in vals.items():
        param = params.get(k, None)

        if param is None:
            continue

        if isinstance(param, Params):
            set_values(param, v)
        else:
            if isinstance(param, ImageParam):
                param.set_serialized(v)
            else:
                param.set(v)
