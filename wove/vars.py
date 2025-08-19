"""
This module contains context variables used by Wove.
Context variables are used to manage the state of the active `weave` block
in a way that is safe for concurrent execution.
"""
from contextvars import ContextVar

# Holds the currently active WoveContextManager instance.
current_weave_context = ContextVar('current_weave_context', default=None)
