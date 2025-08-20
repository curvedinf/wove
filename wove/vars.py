"""
Internal context variables for Wove.
These are used to pass context-specific data, such as the `merge`
function, down through the call stack without explicitly passing it
as an argument.
"""

from contextvars import ContextVar
from typing import Callable, Optional

# ContextVar to hold the active `merge` function implementation.
# The `WoveContextManager` will set this when it enters.
merge_context: ContextVar[Optional[Callable]] = ContextVar(
    "merge_context", default=None
)
