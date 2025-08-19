from contextvars import ContextVar

# Holds the currently active WoveContextManager instance.
current_weave_context = ContextVar('current_weave_context', default=None)
