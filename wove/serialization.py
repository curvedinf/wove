import importlib
from typing import Any, BinaryIO, Optional

from .errors import MissingDispatchFeatureError


_cloudpickle: Optional[Any] = None


def require_dispatch(reason: str) -> Any:
    """
    Load the optional dispatch serialization dependency.
    """
    global _cloudpickle
    if _cloudpickle is not None:
        return _cloudpickle
    try:
        _cloudpickle = importlib.import_module("cloudpickle")
    except ImportError as exc:
        raise MissingDispatchFeatureError(reason) from exc
    return _cloudpickle


def dispatch_dumps(value: Any, *, reason: str) -> bytes:
    return require_dispatch(reason).dumps(value)


def dispatch_loads(value: bytes, *, reason: str) -> Any:
    return require_dispatch(reason).loads(value)


def dispatch_dump(value: Any, file: BinaryIO, *, reason: str) -> None:
    require_dispatch(reason).dump(value, file)


def dispatch_load(file: BinaryIO, *, reason: str) -> Any:
    return require_dispatch(reason).load(file)
