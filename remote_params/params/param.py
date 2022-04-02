import logging
from typing import Any, Callable, Generic, Optional, TypeVar

from evento import Event

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Param(Generic[T]):
    def __init__(
        self,
        type_: str,
        default: Optional[T] = None,
        getter: Optional[Callable[[Any], T]] = None,
        setter: Optional[Callable[[Any], T]] = None,
        **opts: Any,
    ) -> None:
        self.type = type_
        self.value = default
        self.default = default
        self.getter = self._makeSafe(getter) if getter else None
        self.setter = self._makeSafe(setter) if setter else None
        self.opts = opts

        self.changeEvent: Event[T] = Event()

    def set(self, value: T) -> None:
        v = self.setter(value) if self.setter else value

        if self._equals(v, self.value):
            return

        self.value = value
        logger.debug("[Param.set] changevent")
        self.changeEvent()

    def _equals(self, v1: Optional[T], v2: Optional[T]) -> bool:
        return v1 is v2

    def onchange(self, func: Callable[[T], None]) -> None:
        def _f(val: Optional[T]) -> None:
            if val:
                func(val)

        self.changeEvent += _f

    def is_initialized(self) -> bool:
        return self.value is not None

    def val(self) -> Optional[T]:
        v = self.value if self.is_initialized() else self.default
        return self.getter(v) if self.getter else v

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type}

        if self.is_initialized():
            d["value"] = self.value

        if self.opts and len(self.opts) > 0:
            d["opts"] = self.opts

        return d

    def _makeSafe(
        self, func: Callable[[Optional[T]], Optional[T]]
    ) -> Callable[[Optional[T]], Optional[T]]:
        def safeFunc(val: Optional[T]) -> Optional[T]:
            v: Optional[T] = val
            try:
                v = func(val)
            except ValueError:
                v = self.value

            return v

        return safeFunc
