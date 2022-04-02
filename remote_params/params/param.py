import logging
from typing import Any, Callable, Generic, Optional, TypeVar

from evento import Event

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Param(Generic[T]):
    def __init__(
        self,
        type_: str,
        value: T,
        parser: Optional[Callable[[Any], T]] = None,
        **opts: Any,
    ) -> None:
        self.type = type_
        self.value = value
        self.parser = parser
        self.opts = opts

        self.on_change: Event[T] = Event()

    def parse(self, value: Any) -> None:
        assert self.parser
        self.set(self.parser(value))

    def set(self, value: T) -> None:
        v = self.parser(value) if self.parser else value

        if self._equals(v, self.value):
            return

        self.value = v
        self.on_change(self.value)

    def get(self) -> T:
        return self.value

    def _equals(self, v1: Optional[T], v2: Optional[T]) -> bool:
        return v1 is v2

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type, "value": self.value}

        if opts := {k: v for k, v in self.opts.items() if v is not None}:
            d["opts"] = opts

        return d
