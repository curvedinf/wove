from typing import Any, Dict

from .base import RemoteTaskAdapter
from .worker import run


class RayAdapter(RemoteTaskAdapter):
    required_modules = ("ray",)
    install_hint = "ray"

    async def start(self) -> None:
        import ray

        if self.config.get("init", True) and not ray.is_initialized():
            init_kwargs = dict(self.config.get("init_options") or {})
            address = self.config.get("address")
            if address is not None:
                init_kwargs["address"] = address
            init_kwargs.setdefault("ignore_reinit_error", True)
            ray.init(**init_kwargs)

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        del frame
        import ray

        options = dict(self.config.get("remote_options") or {})
        remote_run = ray.remote(**options)(run) if options else ray.remote(run)
        return remote_run.remote(payload)

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del run_id, frame
        if submission is None:
            return
        import ray

        ray.cancel(submission, force=bool(self.config.get("force_cancel", False)))
