import argparse
import asyncio
import base64
import json
import sys
import traceback
from typing import Any, Dict, Optional

from .serialization import dispatch_dumps, dispatch_loads, require_dispatch


class StdioWorkerRuntime:
    """
    Default JSON-lines worker used by the stdio executor and backend adapters.
    """

    def __init__(self, *, adapter: str = "stdio") -> None:
        require_dispatch("the stdio worker decodes dispatched task frames.")
        self._adapter = adapter
        self._active: Dict[str, asyncio.Task] = {}
        self._write_lock = asyncio.Lock()
        self._stopping = False

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        while not self._stopping:
            raw = await loop.run_in_executor(None, sys.stdin.buffer.readline)
            if not raw:
                break

            try:
                frame = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                await self._emit_log(f"Invalid stdio worker frame: {exc}")
                continue

            frame_type = frame.get("type")
            if frame_type == "run_task":
                await self._handle_run_task(frame)
                continue
            if frame_type == "cancel_task":
                await self._handle_cancel_task(frame)
                continue
            if frame_type == "shutdown":
                await self._handle_shutdown(frame)
                break

            await self._emit_log(f"Unknown frame type: {frame_type}")

        if self._active:
            for task in list(self._active.values()):
                task.cancel()
            await asyncio.gather(*self._active.values(), return_exceptions=True)
            self._active.clear()

    async def _handle_run_task(self, frame: Dict[str, Any]) -> None:
        run_id = frame["run_id"]
        task_id = frame["task_id"]
        task_callable = self._decode_pickle(frame.get("callable_pickle"))
        task_args = self._decode_pickle(frame.get("args_pickle")) if frame.get("args_pickle") else {}
        delivery = frame.get("delivery") or {}

        worker = asyncio.create_task(
            self._execute_task(
                run_id=run_id,
                task_id=task_id,
                task_callable=task_callable,
                task_args=task_args,
                delivery=delivery,
            )
        )
        self._active[run_id] = worker

    async def _handle_cancel_task(self, frame: Dict[str, Any]) -> None:
        run_id = frame.get("run_id")
        if not run_id:
            return
        worker = self._active.get(run_id)
        if worker is not None:
            worker.cancel()

    async def _handle_shutdown(self, frame: Dict[str, Any]) -> None:
        self._stopping = True
        orphan_policy = frame.get("delivery_orphan_policy", "cancel")
        if orphan_policy in {"cancel", "fail", "requeue", "detach"}:
            for task in list(self._active.values()):
                task.cancel()

    async def _execute_task(
        self,
        *,
        run_id: str,
        task_id: str,
        task_callable: Any,
        task_args: Dict[str, Any],
        delivery: Dict[str, Any],
    ) -> None:
        heartbeat_task: Optional[asyncio.Task] = None
        heartbeat_seconds = delivery.get("delivery_heartbeat_seconds")
        if isinstance(heartbeat_seconds, (int, float)) and heartbeat_seconds > 0:
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(
                    run_id=run_id,
                    task_id=task_id,
                    interval=float(heartbeat_seconds),
                )
            )

        await self._emit({"type": "task_started", "run_id": run_id, "task_id": task_id})
        try:
            maybe_result = task_callable(**task_args)
            if asyncio.iscoroutine(maybe_result):
                result = await maybe_result
            else:
                result = maybe_result
        except asyncio.CancelledError:
            await self._emit({"type": "task_cancelled", "run_id": run_id, "task_id": task_id})
            raise
        except Exception as exc:
            error_payload = {
                "kind": type(exc).__name__,
                "message": str(exc),
                "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                "retryable": False,
                "source": "task",
                "adapter": self._adapter,
            }
            await self._emit(
                {
                    "type": "task_error",
                    "run_id": run_id,
                    "task_id": task_id,
                    "exception_pickle": self._encode_pickle(exc),
                    "error_pickle": self._encode_pickle(error_payload),
                }
            )
        else:
            await self._emit(
                {
                    "type": "task_result",
                    "run_id": run_id,
                    "task_id": task_id,
                    "result_pickle": self._encode_pickle(result),
                }
            )
        finally:
            if heartbeat_task is not None:
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
            self._active.pop(run_id, None)

    async def _heartbeat_loop(self, *, run_id: str, task_id: str, interval: float) -> None:
        while True:
            await asyncio.sleep(interval)
            await self._emit({"type": "heartbeat", "run_id": run_id, "task_id": task_id})

    async def _emit_log(self, message: str) -> None:
        await self._emit({"type": "log", "message": message})

    async def _emit(self, frame: Dict[str, Any]) -> None:
        payload = json.dumps(frame, separators=(",", ":")) + "\n"
        async with self._write_lock:
            sys.stdout.write(payload)
            sys.stdout.flush()

    @staticmethod
    def _decode_pickle(value: Optional[str]) -> Any:
        if value is None:
            return None
        return dispatch_loads(
            base64.b64decode(value),
            reason="the stdio worker decodes dispatched task frames.",
        )

    @staticmethod
    def _encode_pickle(value: Any) -> str:
        return base64.b64encode(
            dispatch_dumps(
                value,
                reason="the stdio worker serializes dispatched task results and errors.",
            )
        ).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description="Wove stdio worker")
    parser.add_argument("--adapter", default="stdio", help="Adapter name used for metadata/logging.")
    args = parser.parse_args()

    stdio_worker = StdioWorkerRuntime(adapter=args.adapter)
    asyncio.run(stdio_worker.run())


if __name__ == "__main__":
    main()
