# import base64
# import distutils
import logging
from typing import Any, Callable, Generic, Optional, SupportsFloat, TypeVar

from .param import Param

# from evento import Event


# try:
#     import cv2
# except:
#     cv2 = None  # not supported
# cv2 = None

# try:
#     import numpy as np
# except:
#     np = None  # numpy not supported
# np = None

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=SupportsFloat)


class _NumberParam(Generic[T], Param[T]):
    def _default_converter(v: Any) -> T:
        raise NotImplementedError

    converter: Callable[[Any], T] = _default_converter
    type_identifier: str

    @property
    def min(self) -> Optional[T]:
        return self.opts.get("min", None)

    @property
    def max(self) -> Optional[T]:
        return self.opts.get("max", None)

    def __init__(
        self, value: Optional[T] = None, *, min: Optional[T] = None, max: Optional[T] = None
    ) -> None:
        v = self.__class__.converter(0) if value is None else value
        super().__init__(
            self.type_identifier,
            value=v,
            parser=self.__class__.converter,
            min=min,
            max=max,
        )

    def set(self, value: T) -> None:
        fl = float(value)

        if self.min is not None and fl < float(self.min):
            return
        if self.max is not None and fl > float(self.max):
            return

        super().set(value)


class IntParam(_NumberParam[int]):
    converter = int
    type_identifier = "i"


class FloatParam(_NumberParam[float]):
    converter = float
    type_identifier = "f"


class VoidParam(Param[int]):
    def __init__(self) -> None:
        super().__init__("v", 0)

    def set(self, _: Any) -> None:
        return super().set(self.value + 1)

    def trigger(self) -> None:
        self.set(0)

    def ontrigger(self, func: Callable[[], None]) -> None:
        def _middleman(_: int) -> None:
            func()

        self.on_change += _middleman


class ImageParam(Param[Any]):
    def __init__(self, **opts: Any) -> None:
        Param.__init__(self, "g", **opts)

    # def convert(self, v) -> None:
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

    def get_serialized(self) -> str:
        return self.serialize_value(self.get())

    def set_serialized(self, v: Any) -> None:
        raise NotImplementedError

    @staticmethod
    def serialize_value(value: Any) -> str:
        # if cv2 is not None and np is not None:
        #     if isinstance(value, np.array):  # type(value) == type(np.array([])):
        #         # TODO: make configurable
        #         # imparams = [cv2.IMWRITE_PNG_COMPRESSION, 9]
        #         ret, img = cv2.imencode(".png", value)  # , imparams)

        #         if not ret:
        #             logger.warning("cv2.imencode failed to encode image into png format")
        #             return None

        #         png_str = base64.b64encode(img).decode("ascii")
        #         logger.debug(f"Encoded image to {len(png_str)}-bytes png string")
        #         return png_str

        # no supported image processor
        # return str(value)
        raise NotImplementedError
