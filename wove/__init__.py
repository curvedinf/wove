"""
Wove: Beautiful Python Async Orchestration
Wove provides a simple `weave` context manager and `@do` decorator to run
async and sync functions concurrently, automatically managing dependencies.
It's designed for I/O-bound tasks like API calls or database queries.
"""
from .context import WoveContextManager
from .result import WoveResult
from .helpers import sync_to_async
from .decorator import do
# The main context manager factory. Using the class itself makes it re-entrant.
weave = WoveContextManager
__all__ = ['weave', 'do', 'WoveResult', 'sync_to_async']
