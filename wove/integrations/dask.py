from typing import Any, Dict

from .base import RemoteTaskAdapter, maybe_await
from .worker import run


class DaskAdapter(RemoteTaskAdapter):
    required_modules = ("distributed",)
    install_hint = "dask[distributed]"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client: Any = None
        self._owns_client = False

    async def start(self) -> None:
        self._client = self.config.get("client")
        if self._client is not None:
            return

        address = self.config.get("address")
        from distributed import Client

        self._client = Client(address, **dict(self.config.get("client_options") or {}))
        self._owns_client = True

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        kwargs = dict(self.config.get("submit_options") or {})
        kwargs.setdefault("key", frame["run_id"])
        return self._client.submit(run, payload, **kwargs)

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del run_id, frame
        if submission is not None and hasattr(self._client, "cancel"):
            await maybe_await(self._client.cancel(submission))

    async def close(self) -> None:
        if self._owns_client and self._client is not None and hasattr(self._client, "close"):
            await maybe_await(self._client.close())
