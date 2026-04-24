from typing import Any, Dict

from .base import BackendAdapter
from .worker import run


class RQAdapter(BackendAdapter):
    required_modules = ("rq",)
    install_hint = "rq"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._queue: Any = None

    async def start(self) -> None:
        self._queue = self.config.get("queue")
        if self._queue is not None:
            return

        redis_url = self.config.get("redis_url")
        if not redis_url:
            raise TypeError("rq executor_config requires `queue` or `redis_url`.")

        from redis import Redis
        from rq import Queue

        self._queue = Queue(self.config.get("queue_name", "default"), connection=Redis.from_url(redis_url))

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        kwargs = dict(self.config.get("enqueue_options") or {})
        if "job_id" not in kwargs:
            kwargs["job_id"] = frame["run_id"]
        return self._queue.enqueue(run, payload, **kwargs)

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del run_id, frame
        if submission is not None and hasattr(submission, "cancel"):
            submission.cancel()
