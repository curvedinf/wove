from typing import Any, Dict, Optional

from .base import BackendAdapter


class CeleryAdapter(BackendAdapter):
    required_modules = ("celery",)
    install_hint = "celery"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._app: Any = None

    async def start(self) -> None:
        self._app = self.config.get("app")
        if self._app is not None:
            return

        broker_url = self.config.get("broker_url")
        result_backend = self.config.get("result_backend") or self.config.get("backend_url")
        if not broker_url:
            raise TypeError("celery executor_config requires `app` or `broker_url`.")

        from celery import Celery

        self._app = Celery(self.config.get("app_name", "wove"), broker=broker_url, backend=result_backend)

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        del frame
        task_name = self.config.get("task_name", "wove.run_backend_payload")
        options = dict(self.config.get("send_task_options") or {})
        queue: Optional[str] = self.config.get("queue")
        if queue is not None:
            options["queue"] = queue
        return self._app.send_task(task_name, args=[payload], **options)

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del run_id, frame
        if submission is not None and hasattr(submission, "revoke"):
            submission.revoke(terminate=bool(self.config.get("terminate_on_cancel", False)))
