import asyncio
import importlib.util
from typing import Any, Dict, Optional, Tuple


async def maybe_await(value: Any) -> Any:
    if asyncio.iscoroutine(value) or hasattr(value, "__await__"):
        return await value
    return value


class BackendAdapter:
    """
    Backend-specific submit/cancel bridge used by BackendAdapterEnvironmentExecutor.
    """

    required_modules: Tuple[str, ...] = ()
    install_hint: Optional[str] = None

    def __init__(
        self,
        *,
        name: str,
        config: Dict[str, Any],
        callback_url: str,
        run_config: Dict[str, Any],
    ) -> None:
        self.name = name
        self.config = config
        self.callback_url = callback_url
        self.run_config = run_config

    @classmethod
    def missing_dependencies(cls) -> Tuple[str, ...]:
        return tuple(module for module in cls.required_modules if importlib.util.find_spec(module) is None)

    async def start(self) -> None:
        return None

    async def submit(self, payload: Dict[str, Any], frame: Dict[str, Any]) -> Any:
        raise NotImplementedError(f"{type(self).__name__}.submit() is not implemented.")

    async def cancel(self, run_id: str, submission: Any, frame: Dict[str, Any]) -> None:
        del run_id, submission, frame

    async def close(self) -> None:
        return None
