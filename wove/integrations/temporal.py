from typing import Any, Dict

from .base import RemoteTaskAdapter, maybe_await


class TemporalAdapter(RemoteTaskAdapter):
    required_modules = ("temporalio",)
    install_hint = "temporalio"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client: Any = None

    async def start(self) -> None:
        self._client = self.config.get("client")
        if self._client is not None:
            return

        target_host = self.config.get("target_host")
        if not target_host:
            raise TypeError("temporal executor_config requires `client` or `target_host`.")

        from temporalio.client import Client

        self._client = await Client.connect(target_host, **dict(self.config.get("connect_options") or {}))

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        workflow = self.config.get("workflow")
        task_queue = self.config.get("task_queue")
        if workflow is None or task_queue is None:
            raise TypeError("temporal executor_config requires `workflow` and `task_queue`.")

        workflow_id = self.config.get("workflow_id_prefix", "wove") + "-" + frame["run_id"]
        return await maybe_await(
            self._client.start_workflow(
                workflow,
                payload,
                id=workflow_id,
                task_queue=task_queue,
                **dict(self.config.get("start_options") or {}),
            )
        )

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del run_id, frame
        if submission is not None and hasattr(submission, "cancel"):
            await maybe_await(submission.cancel())
