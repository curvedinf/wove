from typing import Any, Dict

from ..remote import run_remote_payload, run_remote_payload_async


def run(payload: Dict[str, Any]) -> Any:
    return run_remote_payload(payload)


async def arun(payload: Dict[str, Any]) -> Any:
    return await run_remote_payload_async(payload)


run_remote_frame = run
