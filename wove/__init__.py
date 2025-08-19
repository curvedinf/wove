# Beautiful python async orchestration
from .context import WoveContextManager
from .result import WoveResult
from .helpers import sync_to_async

# The main context manager factory
weave = WoveContextManager()

def do(func):
    """A decorator to mark a function as a concurrent task within a weave block."""
    # This is a placeholder; the real registration happens when weave is active.
    # This implementation detail would require contextvars to be truly robust
    # in complex nested or concurrent scenarios, but for a single active
    # 'weave' instance, this direct approach works.
    try:
        weave._register_task(func)
    except AttributeError:
        raise RuntimeError("The @do decorator can only be used inside an 'async with weave()' block.")
    return func

__all__ = ['weave', 'do', 'WoveResult', 'sync_to_async']
