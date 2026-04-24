from typing import Any, Dict

from .base import BackendAdapter, maybe_await


class ARQAdapter(BackendAdapter):
    required_modules = ("arq",)
    install_hint = "arq"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pool: Any = None
        self._owns_pool = False

    async def start(self) -> None:
        self._pool = self.config.get("pool")
        if self._pool is not None:
            return

        redis_settings = self.config.get("redis_settings")
        if redis_settings is None:
            raise TypeError("arq executor_config requires `pool` or `redis_settings`.")

        from arq.connections import create_pool

        self._pool = await create_pool(redis_settings)
        self._owns_pool = True

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        function_name = self.config.get("function_name", "wove_run_backend_payload")
        kwargs = dict(self.config.get("enqueue_options") or {})
        kwargs.setdefault("_job_id", frame["run_id"])
        queue_name = self.config.get("queue_name")
        if queue_name is not None:
            kwargs["_queue_name"] = queue_name
        return await maybe_await(self._pool.enqueue_job(function_name, payload, **kwargs))

    async def close(self) -> None:
        if self._owns_pool and self._pool is not None and hasattr(self._pool, "close"):
            await maybe_await(self._pool.close())
