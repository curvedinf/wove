from typing import Any, Dict

from .base import RemoteTaskAdapter, maybe_await


class TaskiqAdapter(RemoteTaskAdapter):
    required_modules = ("taskiq",)
    install_hint = "taskiq"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._task: Any = None

    async def start(self) -> None:
        self._task = self.config.get("task")
        if self._task is not None:
            return

        broker = self.config.get("broker")
        task_name = self.config.get("task_name", "wove.run_remote_payload")
        if broker is None or not hasattr(broker, "find_task"):
            raise TypeError("taskiq executor_config requires `task` or a `broker` with find_task().")
        self._task = broker.find_task(task_name)

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        del frame
        if hasattr(self._task, "kiq"):
            return await maybe_await(self._task.kiq(payload))
        return await maybe_await(self._task(payload))
