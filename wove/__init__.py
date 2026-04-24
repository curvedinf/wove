"""
Wove.

Inline task orchestration for Python code that needs concurrent work without
restructuring the surrounding function around an event loop. Wove keeps the
workflow in ordinary Python: define tasks where the result is needed, let
dependencies come from function signatures, and route selected work through
named environments when it belongs in another process or service.
"""

from .api import merge
from .context import WoveContextManager
from .environment import (
    BackendAdapterEnvironmentExecutor,
    DeliveryOrphanedError,
    DeliveryTimeoutError,
    EnvironmentExecutor,
    GrpcEnvironmentExecutor,
    HttpEnvironmentExecutor,
    WebSocketEnvironmentExecutor,
)
from .errors import MissingDispatchFeatureError
from .integrations.base import BackendAdapter
from .result import WoveResult
from .runtime import config
from .security import NetworkExecutorSecurity
from .weave import Weave
from .helpers import (
    sync_to_async,
    flatten,
    fold,
    batch,
    undict,
    redict,
    denone,
)

# The main context manager factory. Using the class itself makes it re-entrant.
weave = WoveContextManager
__version__ = "2.0.0"
__all__ = [
    "__version__",
    "weave",
    "Weave",
    "WoveResult",
    "EnvironmentExecutor",
    "BackendAdapterEnvironmentExecutor",
    "HttpEnvironmentExecutor",
    "GrpcEnvironmentExecutor",
    "WebSocketEnvironmentExecutor",
    "BackendAdapter",
    "NetworkExecutorSecurity",
    "MissingDispatchFeatureError",
    "DeliveryOrphanedError",
    "DeliveryTimeoutError",
    "config",
    "sync_to_async",
    "merge",
    "flatten",
    "fold",
    "batch",
    "undict",
    "redict",
    "denone",
]
