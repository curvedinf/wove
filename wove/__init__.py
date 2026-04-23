"""
Wove: Beautiful Python Async Orchestration
Wove provides a simple `weave` context manager and `@do` decorator to run
async and sync functions concurrently, automatically managing dependencies.
It's designed for I/O-bound tasks like API calls or database queries.
"""

from .api import merge
from .context import WoveContextManager
from .environment import DeliveryOrphanedError, DeliveryTimeoutError, EnvironmentExecutor, RemoteAdapterEnvironmentExecutor
from .integrations.base import RemoteTaskAdapter
from .result import WoveResult
from .runtime import config
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
__all__ = [
    "weave",
    "Weave",
    "WoveResult",
    "EnvironmentExecutor",
    "RemoteAdapterEnvironmentExecutor",
    "RemoteTaskAdapter",
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
