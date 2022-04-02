import logging
from collections import OrderedDict
from typing import Any, Callable, Optional, TypeVar, Union, overload

from evento import decorators

from .param import Param
from .types import FloatParam, ImageParam, IntParam, VoidParam

log = logging.getLogger(__name__)

T = TypeVar("T")


def changeEvent() -> None:
    ...


def schemaChangeEvent() -> None:
    ...


def valueChangeEvent(path: str, value: Any, param: Param[Any]) -> None:
    ...


class Params(OrderedDict[str, Union[Param[Any], "Params"]]):
    def __init__(self) -> None:
        self.changeEvent = decorators.event(changeEvent)
        self.schemaChangeEvent = decorators.event(schemaChangeEvent)
        self.valueChangeEvent = decorators.event(valueChangeEvent)

        self.removers: dict[str, Callable[[], None]] = {}

    def __del__(self) -> None:
        for id in self.removers:
            remover = self.removers[id]
            remover()

        self.removers = {}

    def get_path(self, path: str) -> Union[None, Param[Any], "Params"]:
        parts = path.split("/")[1:]
        current: Union[None, Param[Any], "Params"] = self

        for p in parts:
            if not isinstance(current, Params):
                return None
            current = current.get(p, None)

        return current

    @overload
    def append(self, id: str, item: Param[T]) -> Param[T]:
        ...

    @overload
    def append(self, id: str, item: "Params") -> "Params":
        ...

    def append(self, id: str, item: Union[Param[T], "Params"]) -> Union[Param[T], "Params"]:
        if existing := self.get(id, None):
            logging.warning("Params already has an item with ID: {}".format(id))
            return existing

        remover = self._create_child(id, item)
        self.removers[id] = remover
        return item

    def remove(self, id: str) -> None:
        if id not in self.removers:
            logging.warning("[Params.remove] could not find item with id `{}` to remove".format(id))
            return

        # find remover (are created in self.append)
        remover = self.removers[id]
        del self.removers[id]
        # run remover
        remover()

    def string(self, id: str) -> Param[str]:
        return self.append(id, Param("s", setter=str))

    def int(self, id: str, min: Optional[int] = None, max: Optional[int] = None) -> Param[int]:
        return self.append(id, IntParam(min, max))

    def bool(self, id: str) -> Param[bool]:
        def converter(v: Any) -> bool:
            if str(v).lower() in ["false", "0", "no", "n"]:
                return False
            return bool(v)

        return self.append(id, Param[bool]("b", setter=converter))

    def float(
        self, id: str, min: Optional[float] = None, max: Optional[float] = None
    ) -> FloatParam:
        p = FloatParam(min, max)
        self.append(id, p)
        return p

    def void(self, id: str) -> VoidParam:
        p = VoidParam()
        self.append(id, p)
        return p

    def image(self, id: str) -> ImageParam:
        p = ImageParam()
        self.append(id, p)
        return p

    def group(self, id: str, params: "Params") -> None:
        self.append(id, params)

    def _create_child(self, id: str, item: Union[Param[Any], "Params"]) -> Callable[[], None]:
        """
        Adds a new item (param or sub-params-group) to self.
        Returns a callable (without args) that removes the added param
        """
        cleanups = []

        self[id] = item

        def remover() -> None:
            del self[id]
            self.schemaChangeEvent()
            self.changeEvent()

        cleanups.append(remover)

        # a single param added?
        if isinstance(item, Param):

            def onchange(v: Any) -> None:
                self.changeEvent()
                if isinstance(item, Param):
                    self.valueChangeEvent("/" + id, item.val(), item)

            _remove = item.changeEvent.add(onchange)
            cleanups.append(_remove)

        # another sub-self-group added?
        if isinstance(item, Params):
            item.changeEvent += self.changeEvent.fire
            item.schemaChangeEvent += self.schemaChangeEvent.fire

            def forwardValChange(path: str, val: Any, param: Param[Any]) -> None:
                self.valueChangeEvent("/" + id + path, val, param)

            _remove = item.valueChangeEvent.add(forwardValChange)
            cleanups.append(_remove)

        self.schemaChangeEvent()
        self.changeEvent()

        def _remove_child() -> None:
            for c in cleanups:
                c()

        return _remove_child
