from typing import Any, Dict

from ..backend import run_backend_payload, run_backend_payload_async


def run(payload: Dict[str, Any]) -> Any:
    return run_backend_payload(payload)


async def arun(payload: Dict[str, Any]) -> Any:
    return await run_backend_payload_async(payload)


run_backend_frame = run
