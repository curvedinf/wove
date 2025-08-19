from .vars import current_weave_context

def do(func):
    """A decorator to mark a function as a concurrent task within a weave block."""
    ctx = current_weave_context.get()
    if ctx is None:
        raise RuntimeError("The @do decorator can only be used inside an 'async with weave()' block.")
    
    ctx._register_task(func)
    return func
