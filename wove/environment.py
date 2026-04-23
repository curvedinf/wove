import abc
import asyncio
import base64
import importlib.util
import json
import shlex
import sys
import time
import traceback
from asyncio.subprocess import Process
from typing import Any, Dict, Optional, Set, Tuple, Type
from uuid import uuid4

import cloudpickle

from .integrations import get_adapter_class, get_adapter_dependencies, get_adapter_install_hints
from .integrations.base import RemoteTaskAdapter
from .remote import RemoteCallbackServer, build_remote_payload

_ADAPTER_DEPENDENCIES: Dict[str, Tuple[str, ...]] = get_adapter_dependencies()
_ADAPTER_INSTALL_HINTS: Dict[str, str] = get_adapter_install_hints()
_KNOWN_ORPHAN_POLICIES: Set[str] = {"fail", "cancel", "requeue", "detach"}
_KNOWN_CANCEL_MODES: Set[str] = {"best_effort", "require_ack"}


class EnvironmentExecutionError(RuntimeError):
    """
    Error raised when an executor reports a remote/normalized error payload.
    """

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        message = payload.get("message", "Task execution failed.")
        super().__init__(message)


class DeliveryTimeoutError(RuntimeError):
    """
    Raised when remote delivery does not complete within configured delivery_timeout.
    """


class DeliveryOrphanedError(RuntimeError):
    """
    Raised when a remote run becomes orphaned during runtime shutdown/failure handling.
    """


def normalize_exception(
    exc: BaseException,
    *,
    source: str = "task",
    retryable: bool = False,
) -> Dict[str, Any]:
    return {
        "kind": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        "retryable": retryable,
        "source": source,
    }


class EnvironmentExecutor(abc.ABC):
    """
    CGI-like stream transport contract for environment executors.
    """

    @abc.abstractmethod
    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        """
        Initialize a run/session for this executor.
        """

    @abc.abstractmethod
    async def send(self, frame: Dict[str, Any]) -> None:
        """
        Send one command frame.
        """

    @abc.abstractmethod
    async def recv(self) -> Dict[str, Any]:
        """
        Receive one event frame.
        """

    @abc.abstractmethod
    async def stop(self) -> None:
        """
        Stop the executor session and clean up resources.
        """


class LocalEnvironmentExecutor(EnvironmentExecutor):
    """
    In-process executor implementation.
    """

    def __init__(self) -> None:
        self._events: asyncio.Queue = asyncio.Queue()
        self._active_runs: Dict[str, asyncio.Task] = {}

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name, environment_config, run_config

    async def send(self, frame: Dict[str, Any]) -> None:
        frame_type = frame.get("type")
        if frame_type == "run_task":
            run_id = frame["run_id"]
            task_id = frame["task_id"]
            task_func = frame["callable"]
            task_args = frame["args"]
            worker = asyncio.create_task(
                self._execute_task(run_id=run_id, task_id=task_id, task_func=task_func, task_args=task_args)
            )
            self._active_runs[run_id] = worker
            return

        if frame_type == "cancel_task":
            run_id = frame["run_id"]
            task = self._active_runs.get(run_id)
            if task:
                task.cancel()
            return

        if frame_type == "shutdown":
            for active in list(self._active_runs.values()):
                active.cancel()
            return

        raise ValueError(f"Unsupported frame type: {frame_type}")

    async def recv(self) -> Dict[str, Any]:
        return await self._events.get()

    async def stop(self) -> None:
        for task in list(self._active_runs.values()):
            task.cancel()
        if self._active_runs:
            await asyncio.gather(*self._active_runs.values(), return_exceptions=True)
        self._active_runs.clear()

    async def _execute_task(
        self,
        *,
        run_id: str,
        task_id: str,
        task_func: Any,
        task_args: Dict[str, Any],
    ) -> None:
        await self._events.put({"type": "task_started", "run_id": run_id, "task_id": task_id})
        try:
            maybe_result = task_func(**task_args)
            if asyncio.iscoroutine(maybe_result):
                result = await maybe_result
            else:
                result = maybe_result
        except asyncio.CancelledError:
            await self._events.put({"type": "task_cancelled", "run_id": run_id, "task_id": task_id})
        except Exception as exc:
            await self._events.put(
                {
                    "type": "task_error",
                    "run_id": run_id,
                    "task_id": task_id,
                    "exception": exc,
                    "error": normalize_exception(exc, source="task"),
                }
            )
        else:
            await self._events.put({"type": "task_result", "run_id": run_id, "task_id": task_id, "result": result})
        finally:
            self._active_runs.pop(run_id, None)


class StdioEnvironmentExecutor(EnvironmentExecutor):
    """
    Subprocess JSON-lines stream executor.
    """

    def __init__(self) -> None:
        self._process: Optional[Process] = None
        self._write_lock = asyncio.Lock()

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name, run_config
        command = environment_config.get("command")
        if not command:
            command = [sys.executable, "-m", "wove.gateway"]

        if isinstance(command, str):
            command = shlex.split(command)
        if not isinstance(command, list) or not command:
            raise TypeError("executor_config.command must be a non-empty list or command string.")

        self._process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,
        )

    async def send(self, frame: Dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("Stdio executor is not started.")
        payload = self._serialize_frame(frame)
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        async with self._write_lock:
            self._process.stdin.write(data)
            await self._process.stdin.drain()

    async def recv(self) -> Dict[str, Any]:
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("Stdio executor is not started.")
        raw = await self._process.stdout.readline()
        if not raw:
            raise RuntimeError("Gateway process closed stdout unexpectedly.")
        payload = json.loads(raw.decode("utf-8"))
        return self._deserialize_frame(payload)

    async def stop(self) -> None:
        if self._process is None:
            return
        if self._process.returncode is None:
            try:
                await self.send({"type": "shutdown"})
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._process.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                self._process.terminate()
                await self._process.wait()
        self._process = None

    def _serialize_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(frame)
        if "callable" in payload:
            payload["callable_pickle"] = base64.b64encode(cloudpickle.dumps(payload.pop("callable"))).decode("ascii")
        if "args" in payload:
            payload["args_pickle"] = base64.b64encode(cloudpickle.dumps(payload.pop("args"))).decode("ascii")
        return payload

    def _deserialize_frame(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        frame = dict(payload)
        if "result_pickle" in frame:
            frame["result"] = cloudpickle.loads(base64.b64decode(frame.pop("result_pickle")))
        if "exception_pickle" in frame:
            frame["exception"] = cloudpickle.loads(base64.b64decode(frame.pop("exception_pickle")))
        if "error_pickle" in frame:
            frame["error"] = cloudpickle.loads(base64.b64decode(frame.pop("error_pickle")))
        return frame


class RemoteAdapterEnvironmentExecutor(EnvironmentExecutor):
    """
    Executor that submits Wove task payloads to a backend adapter and receives
    remote worker frames over a callback server.
    """

    def __init__(
        self,
        name: str,
        adapter_class: Optional[Type[RemoteTaskAdapter]] = None,
        required_modules: Optional[Tuple[str, ...]] = None,
    ) -> None:
        self._name = name
        self._adapter_class = adapter_class or get_adapter_class(name)
        self._required_modules = required_modules or self._adapter_class.required_modules
        self._callback_server: Optional[RemoteCallbackServer] = None
        self._adapter: Optional[RemoteTaskAdapter] = None
        self._submissions: Dict[str, Any] = {}

    async def start(
        self,
        *,
        environment_name: str,
        environment_config: Dict[str, Any],
        run_config: Dict[str, Any],
    ) -> None:
        del environment_name
        missing = [module for module in self._required_modules if importlib.util.find_spec(module) is None]
        if missing:
            quoted = ", ".join(f"`{name}`" for name in missing)
            install_hint = _ADAPTER_INSTALL_HINTS.get(self._name, " ".join(missing))
            raise RuntimeError(
                f"{self._name} executor requested, but dependency {quoted} is not installed. "
                f"Install with: pip install {install_hint}"
            )

        self._callback_server = RemoteCallbackServer(
            host=environment_config.get("callback_host", "127.0.0.1"),
            port=environment_config.get("callback_port", 0),
            public_url=environment_config.get("callback_url"),
            token=environment_config.get("callback_token"),
        )
        await self._callback_server.start()
        assert self._callback_server.callback_url is not None
        self._adapter = self._adapter_class(
            name=self._name,
            config=environment_config,
            callback_url=self._callback_server.callback_url,
            run_config=run_config,
        )
        try:
            await self._adapter.start()
        except Exception:
            await self._callback_server.stop()
            self._callback_server = None
            self._adapter = None
            raise

    async def send(self, frame: Dict[str, Any]) -> None:
        if self._adapter is None or self._callback_server is None or self._callback_server.callback_url is None:
            raise RuntimeError(f"{self._name} executor was not started.")

        frame_type = frame.get("type")
        if frame_type == "run_task":
            payload = build_remote_payload(
                frame,
                callback_url=self._callback_server.callback_url,
                adapter=self._name,
            )
            self._submissions[frame["run_id"]] = await self._adapter.submit(payload, frame)
            return

        if frame_type == "cancel_task":
            run_id = frame["run_id"]
            submission = self._submissions.get(run_id)
            await self._adapter.cancel(run_id, submission, frame)
            return

        if frame_type == "shutdown":
            return

        raise ValueError(f"Unsupported frame type: {frame_type}")

    async def recv(self) -> Dict[str, Any]:
        if self._callback_server is None:
            raise RuntimeError(f"{self._name} executor was not started.")
        return await self._callback_server.recv()

    async def stop(self) -> None:
        try:
            if self._adapter is not None:
                await self._adapter.close()
        finally:
            if self._callback_server is not None:
                await self._callback_server.stop()
            self._adapter = None
            self._callback_server = None
            self._submissions.clear()


class OptionalDependencyExecutor(RemoteAdapterEnvironmentExecutor):
    """
    Backwards-compatible alias for older tests/imports.
    """

    def __init__(self, name: str, required_modules: Tuple[str, ...]) -> None:
        super().__init__(name, required_modules=required_modules)


def build_executor_from_name(name: str) -> EnvironmentExecutor:
    if name == "local":
        return LocalEnvironmentExecutor()
    if name == "stdio":
        return StdioEnvironmentExecutor()
    if name in _ADAPTER_DEPENDENCIES:
        return RemoteAdapterEnvironmentExecutor(name)
    raise ValueError(f"Unknown executor '{name}'.")


def coerce_executor(executor_value: Any) -> EnvironmentExecutor:
    if isinstance(executor_value, EnvironmentExecutor):
        return executor_value
    if isinstance(executor_value, str):
        return build_executor_from_name(executor_value)
    raise TypeError("Environment 'executor' must be a string or EnvironmentExecutor instance.")


class ExecutorRuntime:
    """
    Multiplexes task execution over environment executors.
    """

    def __init__(self, environment_definitions: Dict[str, Dict[str, Any]], run_config: Dict[str, Any]) -> None:
        self._environment_definitions = environment_definitions
        self._run_config = run_config
        self._executors: Dict[str, EnvironmentExecutor] = {}
        self._recv_tasks: Dict[str, asyncio.Task] = {}
        self._pending: Dict[str, Dict[str, asyncio.Future]] = {}
        self._run_metadata: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._inflight_semaphores: Dict[Tuple[str, int], asyncio.Semaphore] = {}

    async def start(self) -> None:
        for environment_name, definition in self._environment_definitions.items():
            executor = coerce_executor(definition.get("executor", "local"))
            executor_config = definition.get("executor_config") or {}
            await executor.start(
                environment_name=environment_name,
                environment_config=executor_config,
                run_config=self._run_config,
            )
            self._executors[environment_name] = executor
            self._pending[environment_name] = {}
            self._run_metadata[environment_name] = {}
            self._recv_tasks[environment_name] = asyncio.create_task(
                self._recv_loop(environment_name, executor)
            )

    async def stop(self) -> None:
        await self._orphan_pending_futures()

        for environment_name, futures in self._pending.items():
            for run_id, future in list(futures.items()):
                if not future.done():
                    future.set_exception(asyncio.CancelledError())
                futures.pop(run_id, None)
                self._run_metadata.get(environment_name, {}).pop(run_id, None)

        for task in self._recv_tasks.values():
            task.cancel()
        if self._recv_tasks:
            await asyncio.gather(*self._recv_tasks.values(), return_exceptions=True)
        self._recv_tasks.clear()

        for executor in self._executors.values():
            await executor.stop()
        self._executors.clear()
        self._pending.clear()
        self._run_metadata.clear()
        self._inflight_semaphores.clear()

    async def run_task(
        self,
        *,
        task_name: str,
        task_func: Any,
        task_args: Dict[str, Any],
        task_info: Dict[str, Any],
    ) -> Any:
        environment_name = task_info.get("environment")
        if environment_name not in self._executors:
            raise NameError(f"Task '{task_name}' references unknown environment '{environment_name}'.")

        recv_task = self._recv_tasks.get(environment_name)
        if recv_task is not None and recv_task.done():
            if recv_task.cancelled():
                raise RuntimeError(f"Executor receiver for environment '{environment_name}' was cancelled.")
            recv_exc = recv_task.exception()
            if recv_exc is not None:
                raise RuntimeError(
                    f"Executor receiver for environment '{environment_name}' stopped unexpectedly."
                ) from recv_exc
            raise RuntimeError(f"Executor receiver for environment '{environment_name}' is not running.")

        executor = self._executors[environment_name]
        delivery_timeout = task_info.get("delivery_timeout")
        cancel_mode = task_info.get("delivery_cancel_mode") or "best_effort"
        if cancel_mode not in _KNOWN_CANCEL_MODES:
            raise ValueError(
                "delivery_cancel_mode must be one of: 'best_effort', 'require_ack'"
            )
        heartbeat_seconds = task_info.get("delivery_heartbeat_seconds")
        orphan_policy = self._resolve_orphan_policy(environment_name, task_info)
        max_in_flight = task_info.get("delivery_max_in_flight")

        idempotency_key = self._resolve_delivery_idempotency_key(task_info, task_args, task_name)
        delivery = {
            "delivery_timeout": delivery_timeout,
            "delivery_idempotency_key": idempotency_key,
            "delivery_cancel_mode": cancel_mode,
            "delivery_heartbeat_seconds": heartbeat_seconds,
            "delivery_orphan_policy": orphan_policy,
        }
        delivery = {key: value for key, value in delivery.items() if value is not None}

        run_id = f"{task_name}:{uuid4().hex}"
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[environment_name][run_id] = future
        self._run_metadata[environment_name][run_id] = {
            "task_id": task_name,
            "delivery_cancel_mode": cancel_mode,
            "delivery_orphan_policy": orphan_policy,
            "delivery_heartbeat_seconds": heartbeat_seconds,
            "started_at": time.monotonic(),
            "last_heartbeat": time.monotonic(),
        }

        run_frame = {
            "type": "run_task",
            "run_id": run_id,
            "task_id": task_name,
            "callable": task_func,
            "args": task_args,
            "delivery": delivery,
        }
        cancel_frame = {
            "type": "cancel_task",
            "run_id": run_id,
            "task_id": task_name,
            "delivery_cancel_mode": cancel_mode,
            "delivery_orphan_policy": orphan_policy,
        }

        semaphore = self._resolve_inflight_semaphore(environment_name, max_in_flight)
        if semaphore is not None:
            async with semaphore:
                await executor.send(run_frame)
                try:
                    return await self._await_result(
                        environment_name=environment_name,
                        run_id=run_id,
                        future=future,
                        executor=executor,
                        cancel_frame=cancel_frame,
                        delivery_timeout=delivery_timeout,
                        heartbeat_seconds=heartbeat_seconds,
                        task_name=task_name,
                    )
                finally:
                    self._pending[environment_name].pop(run_id, None)
                    self._run_metadata[environment_name].pop(run_id, None)

        try:
            await executor.send(run_frame)
            return await self._await_result(
                environment_name=environment_name,
                run_id=run_id,
                future=future,
                executor=executor,
                cancel_frame=cancel_frame,
                delivery_timeout=delivery_timeout,
                heartbeat_seconds=heartbeat_seconds,
                task_name=task_name,
            )
        finally:
            self._pending[environment_name].pop(run_id, None)
            self._run_metadata[environment_name].pop(run_id, None)

    async def _await_result(
        self,
        *,
        environment_name: str,
        run_id: str,
        future: asyncio.Future,
        executor: EnvironmentExecutor,
        cancel_frame: Dict[str, Any],
        delivery_timeout: Optional[float],
        heartbeat_seconds: Optional[float],
        task_name: str,
    ) -> Any:
        started_at = time.monotonic()
        try:
            while True:
                if future.done():
                    return future.result()

                timeout_window = self._next_wait_timeout(
                    environment_name=environment_name,
                    run_id=run_id,
                    started_at=started_at,
                    delivery_timeout=delivery_timeout,
                    heartbeat_seconds=heartbeat_seconds,
                )

                try:
                    if timeout_window is None:
                        return await future
                    return await asyncio.wait_for(asyncio.shield(future), timeout=timeout_window)
                except asyncio.TimeoutError as exc:
                    timed_out_on_delivery = (
                        delivery_timeout is not None and (time.monotonic() - started_at) >= delivery_timeout
                    )
                    if timed_out_on_delivery:
                        await executor.send(cancel_frame)
                        raise DeliveryTimeoutError(
                            f"Delivery timeout exceeded for task '{task_name}' ({delivery_timeout}s)."
                        ) from exc

                    if heartbeat_seconds is not None:
                        metadata = self._run_metadata.get(environment_name, {}).get(run_id, {})
                        last_heartbeat = metadata.get("last_heartbeat", started_at)
                        if (time.monotonic() - last_heartbeat) >= heartbeat_seconds:
                            await executor.send(cancel_frame)
                            raise DeliveryTimeoutError(
                                f"Delivery heartbeat timed out for task '{task_name}' "
                                f"after {heartbeat_seconds}s without heartbeat."
                            ) from exc
                    continue
        except asyncio.CancelledError:
            await executor.send(cancel_frame)
            raise

    def _next_wait_timeout(
        self,
        *,
        environment_name: str,
        run_id: str,
        started_at: float,
        delivery_timeout: Optional[float],
        heartbeat_seconds: Optional[float],
    ) -> Optional[float]:
        windows = []
        now = time.monotonic()
        if delivery_timeout is not None:
            windows.append(max(delivery_timeout - (now - started_at), 0))

        if heartbeat_seconds is not None:
            metadata = self._run_metadata.get(environment_name, {}).get(run_id, {})
            last_heartbeat = metadata.get("last_heartbeat", started_at)
            windows.append(max(heartbeat_seconds - (now - last_heartbeat), 0))

        if not windows:
            return None
        return min(windows)

    def _resolve_orphan_policy(self, environment_name: str, task_info: Dict[str, Any]) -> str:
        raw_policy = task_info.get("delivery_orphan_policy")
        if raw_policy is None:
            raw_policy = self._environment_definitions.get(environment_name, {}).get("delivery_orphan_policy")
        if raw_policy is None:
            raw_policy = self._run_config.get("delivery_orphan_policy")
        if raw_policy is None:
            return "cancel"
        if raw_policy not in _KNOWN_ORPHAN_POLICIES:
            allowed = "', '".join(sorted(_KNOWN_ORPHAN_POLICIES))
            raise ValueError(f"delivery_orphan_policy must be one of: '{allowed}'")
        return raw_policy

    def _resolve_inflight_semaphore(
        self,
        environment_name: str,
        max_in_flight: Optional[int],
    ) -> Optional[asyncio.Semaphore]:
        if not isinstance(max_in_flight, int) or max_in_flight <= 0:
            return None
        key = (environment_name, max_in_flight)
        semaphore = self._inflight_semaphores.get(key)
        if semaphore is None:
            semaphore = asyncio.Semaphore(max_in_flight)
            self._inflight_semaphores[key] = semaphore
        return semaphore

    async def _orphan_pending_futures(self) -> None:
        for environment_name, futures in self._pending.items():
            executor = self._executors.get(environment_name)
            metadata_map = self._run_metadata.get(environment_name, {})
            for run_id, future in list(futures.items()):
                if future.done():
                    continue

                metadata = metadata_map.get(run_id, {})
                orphan_policy = metadata.get("delivery_orphan_policy", "cancel")
                cancel_mode = metadata.get("delivery_cancel_mode", "best_effort")
                task_id = metadata.get("task_id", run_id)

                if (
                    executor is not None
                    and orphan_policy in {"cancel", "fail", "requeue"}
                ):
                    cancel_frame = {
                        "type": "cancel_task",
                        "run_id": run_id,
                        "task_id": task_id,
                        "delivery_cancel_mode": cancel_mode,
                        "delivery_orphan_policy": orphan_policy,
                    }
                    try:
                        await executor.send(cancel_frame)
                    except Exception:
                        pass

                if orphan_policy == "cancel":
                    future.set_exception(asyncio.CancelledError())
                    continue

                future.set_exception(
                    DeliveryOrphanedError(
                        f"Task '{task_id}' became orphaned in environment '{environment_name}' "
                        f"with policy '{orphan_policy}'."
                    )
                )

    def _resolve_delivery_idempotency_key(
        self,
        task_info: Dict[str, Any],
        task_args: Dict[str, Any],
        task_name: str,
    ) -> Optional[str]:
        raw_key = task_info.get("delivery_idempotency_key")
        if raw_key is None:
            return None

        if callable(raw_key):
            try:
                value = raw_key(task_args)
            except TypeError:
                value = raw_key(**task_args)
            return str(value)

        if isinstance(raw_key, str):
            if "{" in raw_key:
                try:
                    return raw_key.format_map(task_args)
                except KeyError:
                    return raw_key
            return raw_key

        return str(raw_key)

    def is_local_environment(self, environment_name: str) -> bool:
        definition = self._environment_definitions.get(environment_name, {})
        executor_value = definition.get("executor", "local")
        if isinstance(executor_value, str):
            return executor_value == "local"
        return isinstance(executor_value, LocalEnvironmentExecutor)

    async def _recv_loop(self, environment_name: str, executor: EnvironmentExecutor) -> None:
        pending = self._pending[environment_name]
        metadata_map = self._run_metadata[environment_name]
        try:
            while True:
                frame = await executor.recv()
                run_id = frame.get("run_id")
                if not run_id:
                    continue
                future = pending.get(run_id)
                if future is None or future.done():
                    continue

                frame_type = frame.get("type")
                if frame_type == "task_started":
                    if run_id in metadata_map:
                        metadata_map[run_id]["last_heartbeat"] = time.monotonic()
                    continue
                if frame_type == "heartbeat":
                    if run_id in metadata_map:
                        metadata_map[run_id]["last_heartbeat"] = time.monotonic()
                    continue
                if frame_type == "log":
                    continue
                if frame_type == "task_result":
                    future.set_result(frame.get("result"))
                    continue
                if frame_type == "task_cancelled":
                    future.set_exception(asyncio.CancelledError())
                    continue
                if frame_type == "task_error":
                    future.set_exception(self._exception_from_error_frame(frame))
                    continue

                future.set_exception(
                    RuntimeError(
                        f"Unknown executor frame type '{frame_type}' from environment '{environment_name}'."
                    )
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for run_id, future in list(pending.items()):
                if future.done():
                    continue
                orphan_policy = metadata_map.get(run_id, {}).get("delivery_orphan_policy", "cancel")
                if orphan_policy == "cancel":
                    future.set_exception(exc)
                else:
                    future.set_exception(
                        DeliveryOrphanedError(
                            f"Task '{metadata_map.get(run_id, {}).get('task_id', run_id)}' "
                            f"orphaned after receiver failure in environment '{environment_name}' "
                            f"(policy='{orphan_policy}')."
                        )
                    )
            raise

    def _exception_from_error_frame(self, frame: Dict[str, Any]) -> BaseException:
        if "exception" in frame and isinstance(frame["exception"], BaseException):
            return frame["exception"]
        payload = frame.get("error") or {}
        if not isinstance(payload, dict):
            payload = {"message": str(payload), "kind": "ExecutionError", "source": "executor"}
        return EnvironmentExecutionError(payload)
