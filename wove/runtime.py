import importlib.util
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional


_CONFIG_FILENAME = "wove_config.py"
_KNOWN_DELIVERY_CANCEL_MODES = {"best_effort", "require_ack"}
_KNOWN_ORPHAN_POLICIES = {"fail", "cancel", "requeue", "detach"}
_KNOWN_CONFIG_KEYS = {
    "default_environment",
    "environments",
    "max_workers",
    "background",
    "fork",
    "retries",
    "timeout",
    "workers",
    "limit_per_minute",
    "max_pending",
    "error_mode",
    "delivery_timeout",
    "delivery_idempotency_key",
    "delivery_cancel_mode",
    "delivery_heartbeat_seconds",
    "delivery_max_in_flight",
    "delivery_orphan_policy",
}
_DEFAULTS = {
    "max_workers": 256,
    "background": False,
    "fork": False,
    "retries": 0,
    "timeout": None,
    "workers": None,
    "limit_per_minute": None,
    "max_pending": None,
    "error_mode": "raise",
    "delivery_timeout": None,
    "delivery_idempotency_key": None,
    "delivery_cancel_mode": "best_effort",
    "delivery_heartbeat_seconds": None,
    "delivery_max_in_flight": None,
    "delivery_orphan_policy": None,
}


class RuntimeConfig:
    """
    Process-wide runtime configuration singleton for Wove.
    """

    def __init__(self) -> None:
        self.default_environment = "default"
        self.environments: Dict[str, Dict[str, Any]] = {"default": {"executor": "local"}}
        self.global_defaults: Dict[str, Any] = dict(_DEFAULTS)

    def configure(
        self,
        *,
        config_file: Optional[str] = None,
        default_environment: Optional[str] = None,
        environments: Optional[Dict[str, Dict[str, Any]]] = None,
        max_workers: Optional[int] = None,
        background: Optional[bool] = None,
        fork: Optional[bool] = None,
        retries: Optional[int] = None,
        timeout: Optional[float] = None,
        workers: Optional[int] = None,
        limit_per_minute: Optional[int] = None,
        max_pending: Optional[int] = None,
        error_mode: Optional[str] = None,
        delivery_timeout: Optional[float] = None,
        delivery_idempotency_key: Optional[Any] = None,
        delivery_cancel_mode: Optional[str] = None,
        delivery_heartbeat_seconds: Optional[float] = None,
        delivery_max_in_flight: Optional[int] = None,
        delivery_orphan_policy: Optional[str] = None,
    ) -> "RuntimeConfig":
        explicit_values = {
            "default_environment": default_environment,
            "environments": environments,
            "max_workers": max_workers,
            "background": background,
            "fork": fork,
            "retries": retries,
            "timeout": timeout,
            "workers": workers,
            "limit_per_minute": limit_per_minute,
            "max_pending": max_pending,
            "error_mode": error_mode,
            "delivery_timeout": delivery_timeout,
            "delivery_idempotency_key": delivery_idempotency_key,
            "delivery_cancel_mode": delivery_cancel_mode,
            "delivery_heartbeat_seconds": delivery_heartbeat_seconds,
            "delivery_max_in_flight": delivery_max_in_flight,
            "delivery_orphan_policy": delivery_orphan_policy,
        }

        has_non_file_overrides = any(value is not None for value in explicit_values.values())
        should_attempt_autoload = config_file is None and not has_non_file_overrides

        if should_attempt_autoload:
            maybe_path = self._discover_config_file(_CONFIG_FILENAME)
            if maybe_path:
                self._apply_file_settings(maybe_path)
        elif config_file is not None:
            maybe_path = self._resolve_config_file(config_file)
            self._apply_file_settings(maybe_path)

        if default_environment is not None:
            self.default_environment = default_environment

        if environments is not None:
            self._merge_environments(environments)

        for key in (
            "max_workers",
            "background",
            "fork",
            "retries",
            "timeout",
            "workers",
            "limit_per_minute",
            "max_pending",
            "error_mode",
            "delivery_timeout",
            "delivery_idempotency_key",
            "delivery_cancel_mode",
            "delivery_heartbeat_seconds",
            "delivery_max_in_flight",
            "delivery_orphan_policy",
        ):
            value = explicit_values[key]
            if value is not None:
                self._set_default(key, value)

        if self.default_environment not in self.environments:
            self.environments[self.default_environment] = {"executor": "local"}
        if "default" not in self.environments:
            self.environments["default"] = {"executor": "local"}

        return self

    def _set_default(self, key: str, value: Any) -> None:
        if key == "error_mode" and value not in {"raise", "return"}:
            raise ValueError("error_mode must be one of: 'raise', 'return'")
        if key == "delivery_cancel_mode" and value not in _KNOWN_DELIVERY_CANCEL_MODES:
            raise ValueError("delivery_cancel_mode must be one of: 'best_effort', 'require_ack'")
        if key == "delivery_orphan_policy" and value not in _KNOWN_ORPHAN_POLICIES:
            allowed = "', '".join(sorted(_KNOWN_ORPHAN_POLICIES))
            raise ValueError(f"delivery_orphan_policy must be one of: '{allowed}'")
        self.global_defaults[key] = value

    def _merge_environments(self, environments: Dict[str, Dict[str, Any]]) -> None:
        if not isinstance(environments, dict):
            raise TypeError("environments must be a dict[str, dict]")
        for name, definition in environments.items():
            if definition is None:
                self.environments.pop(name, None)
                continue
            if not isinstance(definition, dict):
                raise TypeError(f"Environment '{name}' must be a dict.")
            existing = self.environments.get(name, {})
            merged = dict(existing)
            merged.update(definition)
            self._validate_environment_definition(name, merged)
            self.environments[name] = merged

    def _validate_environment_definition(self, name: str, definition: Dict[str, Any]) -> None:
        cancel_mode = definition.get("delivery_cancel_mode")
        if cancel_mode is not None and cancel_mode not in _KNOWN_DELIVERY_CANCEL_MODES:
            raise ValueError(
                f"Environment '{name}' has invalid delivery_cancel_mode. "
                "Expected 'best_effort' or 'require_ack'."
            )

        orphan_policy = definition.get("delivery_orphan_policy")
        if orphan_policy is not None and orphan_policy not in _KNOWN_ORPHAN_POLICIES:
            allowed = "', '".join(sorted(_KNOWN_ORPHAN_POLICIES))
            raise ValueError(
                f"Environment '{name}' has invalid delivery_orphan_policy. "
                f"Expected one of: '{allowed}'."
            )

    def resolve_environment_name(self, requested: Optional[str]) -> str:
        return requested or self.default_environment

    def resolve_environment_settings(self, environment_name: str) -> Dict[str, Any]:
        environment = self.environments.get(environment_name)
        if environment is None:
            raise NameError(f"Environment '{environment_name}' is not configured.")

        effective = dict(self.global_defaults)
        effective.update(environment)
        effective["executor"] = effective.get("executor", "local")
        if "executor_config" not in effective and "config" in effective:
            effective["executor_config"] = effective.get("config")
        effective["executor_config"] = effective.get("executor_config") or {}
        return effective

    def snapshot(self) -> Dict[str, Any]:
        return deepcopy({
            "default_environment": self.default_environment,
            "environments": {name: dict(config) for name, config in self.environments.items()},
            **dict(self.global_defaults),
        })

    def _apply_file_settings(self, config_path: Path) -> None:
        settings = self._load_settings_module(config_path)
        for key in _KNOWN_CONFIG_KEYS:
            if key not in settings:
                continue
            value = settings[key]
            if key == "default_environment":
                self.default_environment = value
            elif key == "environments":
                self._merge_environments(value)
            else:
                self._set_default(key, value)

    def _load_settings_module(self, path: Path) -> Dict[str, Any]:
        module_name = f"_wove_user_config_{abs(hash(str(path)))}"
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load config file: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "WOVE"):
            data = getattr(module, "WOVE")
            if not isinstance(data, dict):
                raise TypeError("WOVE in config file must be a dictionary.")
            return data

        result: Dict[str, Any] = {}
        for key in _KNOWN_CONFIG_KEYS:
            if hasattr(module, key):
                result[key] = getattr(module, key)
        return result

    def _resolve_config_file(self, config_file: str) -> Path:
        candidate = Path(config_file)
        if candidate.is_absolute():
            if not candidate.exists():
                raise FileNotFoundError(f"Config file not found: {candidate}")
            return candidate

        if os.path.sep in config_file:
            resolved = Path.cwd() / candidate
            if not resolved.exists():
                raise FileNotFoundError(f"Config file not found: {resolved}")
            return resolved

        discovered = self._discover_config_file(config_file)
        if discovered is None:
            raise FileNotFoundError(f"Config file not found: {config_file}")
        return discovered

    def _discover_config_file(self, filename: str) -> Optional[Path]:
        current = Path.cwd()
        search_roots = [current, *current.parents]
        for root in search_roots:
            candidate = root / filename
            if candidate.exists():
                return candidate
        return None


runtime = RuntimeConfig()


def config(
    *,
    config_file: Optional[str] = None,
    default_environment: Optional[str] = None,
    environments: Optional[Dict[str, Dict[str, Any]]] = None,
    max_workers: Optional[int] = None,
    background: Optional[bool] = None,
    fork: Optional[bool] = None,
    retries: Optional[int] = None,
    timeout: Optional[float] = None,
    workers: Optional[int] = None,
    limit_per_minute: Optional[int] = None,
    max_pending: Optional[int] = None,
    error_mode: Optional[str] = None,
    delivery_timeout: Optional[float] = None,
    delivery_idempotency_key: Optional[Any] = None,
    delivery_cancel_mode: Optional[str] = None,
    delivery_heartbeat_seconds: Optional[float] = None,
    delivery_max_in_flight: Optional[int] = None,
    delivery_orphan_policy: Optional[str] = None,
) -> RuntimeConfig:
    """
    Configure process-wide Wove runtime behavior.

    Calling `wove.config()` with no args attempts to autoload `wove_config.py`
    from the current working directory or one of its parents.
    """

    return runtime.configure(
        config_file=config_file,
        default_environment=default_environment,
        environments=environments,
        max_workers=max_workers,
        background=background,
        fork=fork,
        retries=retries,
        timeout=timeout,
        workers=workers,
        limit_per_minute=limit_per_minute,
        max_pending=max_pending,
        error_mode=error_mode,
        delivery_timeout=delivery_timeout,
        delivery_idempotency_key=delivery_idempotency_key,
        delivery_cancel_mode=delivery_cancel_mode,
        delivery_heartbeat_seconds=delivery_heartbeat_seconds,
        delivery_max_in_flight=delivery_max_in_flight,
        delivery_orphan_policy=delivery_orphan_policy,
    )
