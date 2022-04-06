import logging
from collections import OrderedDict
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional, TypeVar, Union

from evento import decorators

from .param import Param
from .types import FloatParam, ImageParam, IntParam, VoidParam

log = logging.getLogger(__name__)

T = TypeVar("T")


def on_change() -> None:
    ...


def on_schema_change() -> None:
    ...


def on_value_change(path: str, value: Any, param: Param[Any]) -> None:
    ...


class Params(OrderedDict[str, Union[Param[Any], "Params"]]):
    def __init__(self) -> None:
        self.on_change = decorators.event(on_change)
        self.on_schema_change = decorators.event(on_schema_change)
        self.on_value_change = decorators.event(on_value_change)

        self.removers: dict[str, Callable[[], None]] = {}
        self._batches: list[list[Callable[[], Any]]] = []

    def __del__(self) -> None:
        for id in list(self.removers.keys()):
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

    def append(self, id: str, item: Union[Param[T], "Params"]) -> Callable[[], None]:
        if self.get(id, None):
            logging.warning("Param with duplicate ID: {}".format(id))
            self.remove(id)

        return self._add(id, item)

    def remove(self, item: Union[str, Param[Any]]) -> None:
        id = self._get_id(item) if isinstance(item, Param) else item

        if not id or id not in self.removers:
            logging.warning("Could not find item {}to remove".format("(id={id}) " if id else ""))
            return

        self.removers[id]()

    # types

    def group(self, id: str, params: "Params") -> None:
        self.append(id, params)

    def string(self, id: str) -> Param[str]:
        param = Param("s", "", parser=str)
        self.append(id, param)
        return param

    def int(self, id: str, min: Optional[int] = None, max: Optional[int] = None) -> Param[int]:
        param = IntParam(min=min, max=max)
        self.append(id, param)
        return param

    def bool(self, id: str) -> Param[bool]:
        def converter(v: Any) -> bool:
            if str(v).lower() in ["false", "0", "no", "n"]:
                return False
            return bool(v)

        param = Param[bool]("b", False, parser=converter)
        self.append(id, param)
        return param

    def float(
        self, id: str, min: Optional[float] = None, max: Optional[float] = None
    ) -> FloatParam:
        p = FloatParam(min=min, max=max)
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

    @contextmanager
    def batch(self) -> Generator[None, None, None]:
        self._batches.append([])

        yield

        for action in self._batches.pop():
            action()

    def _get_id(self, param: Param[Any]) -> Optional[str]:
        return next((id for id, item in self.items() if item == param), None)

    def _add(self, id: str, item: Union[Param[Any], "Params"]) -> Callable[[], None]:
        """
        Adds a new item (param or sub-params-group) to self.
        Returns a callable (without args) that removes the added param
        """
        cleanups = []

        self[id] = item

        def remover() -> None:
            del self[id]
            self.on_schema_change()
            self._fire_change()

        cleanups.append(remover)

        # a single param added?
        if isinstance(item, Param):

            def onchange(v: Any) -> None:
                self._fire_change()
                if isinstance(item, Param):
                    self._fire_value_change("/" + id, item.get(), item)

            _remove = item.on_change.add(onchange)
            cleanups.append(_remove)

        # another sub-self-group added?
        if isinstance(item, Params):
            item.on_change += self.on_change.fire
            item.on_schema_change += self.on_schema_change.fire

            def forwardValChange(path: str, val: Any, param: Param[Any]) -> None:
                self.on_value_change("/" + id + path, val, param)

            _remove = item.on_value_change.add(forwardValChange)
            cleanups.append(_remove)

        self._fire_schema_change()
        self._fire_change()

        def _remove_child() -> None:
            del self.removers[id]
            for c in cleanups:
                c()

        self.removers[id] = _remove_child
        return _remove_child

    def _fire_change(self) -> None:
        self._batch(self.on_change)

    def _fire_value_change(self, path: str, value: Any, param: Param[Any]) -> None:
        self._batch(lambda: self.on_value_change(path, value, param))

    def _fire_schema_change(self) -> None:
        self._batch(self.on_schema_change)

    def _batch(self, func: Callable[[], Any]) -> None:
        if self._batches:
            self._batches[-1].append(func)
        else:
            func()
