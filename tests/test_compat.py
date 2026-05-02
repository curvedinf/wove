import asyncio
import contextvars
import threading

import pytest

from wove._compat import to_thread


@pytest.mark.asyncio
async def test_to_thread_fallback_preserves_context(monkeypatch):
    monkeypatch.delattr(asyncio, "to_thread", raising=False)
    marker = contextvars.ContextVar("marker")
    marker.set("value")
    event_loop_thread_id = threading.get_ident()

    def read_context():
        return marker.get(), threading.get_ident() != event_loop_thread_id

    assert await to_thread(read_context) == ("value", True)
