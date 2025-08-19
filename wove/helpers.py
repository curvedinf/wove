import asyncio
from functools import wraps

def sync_to_async(func):
    """
    A simple wrapper to run a synchronous function in asyncio's default
    thread pool executor. A more robust implementation would use asgiref.
    """
    @wraps(func)
    async def run_in_executor(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return run_in_executor
