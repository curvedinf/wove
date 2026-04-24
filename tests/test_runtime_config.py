import copy
from pathlib import Path

import pytest

from wove import config, weave
from wove.runtime import RuntimeConfig, runtime


@pytest.fixture
def restore_runtime():
    snapshot = runtime.snapshot()
    yield
    runtime.default_environment = snapshot["default_environment"]
    runtime.environments = copy.deepcopy(snapshot["environments"])
    runtime.global_defaults = {
        key: value
        for key, value in snapshot.items()
        if key not in {"default_environment", "environments"}
    }


@pytest.mark.asyncio
async def test_config_default_environment_applies_to_weave(restore_runtime):
    attempts = 0
    config(
        default_environment="custom",
        environments={"custom": {"executor": "local", "retries": 1}},
    )

    async with weave() as w:
        @w.do
        async def sometimes_fails():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ValueError("fail once")
            return "ok"

    assert attempts == 2
    assert w.result.sometimes_fails == "ok"


@pytest.mark.asyncio
async def test_task_environment_override(restore_runtime):
    config(
        default_environment="default",
        environments={
            "default": {"executor": "local"},
            "secondary": {"executor": "local"},
        },
    )

    async with weave(environment="default") as w:
        @w.do(environment="secondary")
        async def in_secondary():
            return "done"

    assert w.result.in_secondary == "done"


@pytest.mark.asyncio
async def test_max_pending_limit(restore_runtime):
    config(max_pending=2)

    async with weave() as w:
        @w.do([1, 2, 3])
        async def too_many(item):
            return item

    with pytest.raises(RuntimeError, match="exceeds max_pending=2"):
        _ = w.result.too_many


@pytest.mark.asyncio
async def test_error_mode_return(restore_runtime):
    config(error_mode="return")

    async with weave() as w:
        @w.do
        async def fails():
            raise ValueError("bad")

    value = w.result.fails
    assert isinstance(value, ValueError)
    assert str(value) == "bad"


def test_config_autoload_from_default_file(tmp_path: Path, monkeypatch, restore_runtime):
    config_file = tmp_path / "wove_config.py"
    config_file.write_text(
        "WOVE_CONFIG = {\n"
        "    'default_environment': 'auto',\n"
        "    'environments': {\n"
        "        'auto': {'executor': 'local', 'retries': 7},\n"
        "    },\n"
        "    'timeout': 42.0,\n"
        "}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    config()
    resolved = runtime.resolve_environment_settings("auto")
    assert runtime.default_environment == "auto"
    assert resolved["retries"] == 7
    assert resolved["timeout"] == 42.0


def test_delivery_defaults_in_config(restore_runtime):
    config(
        delivery_timeout=11.0,
        delivery_cancel_mode="require_ack",
        delivery_heartbeat_seconds=3.0,
        delivery_max_in_flight=20,
        delivery_orphan_policy="requeue",
    )
    resolved = runtime.resolve_environment_settings("default")
    assert resolved["delivery_timeout"] == 11.0
    assert resolved["delivery_cancel_mode"] == "require_ack"
    assert resolved["delivery_heartbeat_seconds"] == 3.0
    assert resolved["delivery_max_in_flight"] == 20
    assert resolved["delivery_orphan_policy"] == "requeue"


def test_invalid_delivery_cancel_mode_raises(restore_runtime):
    with pytest.raises(ValueError, match="delivery_cancel_mode"):
        config(delivery_cancel_mode="bad_mode")


def test_invalid_delivery_orphan_policy_raises(restore_runtime):
    with pytest.raises(ValueError, match="delivery_orphan_policy"):
        config(delivery_orphan_policy="unknown_policy")


def test_runtime_config_unknown_environment_raises():
    rc = RuntimeConfig()
    with pytest.raises(NameError, match="not configured"):
        rc.resolve_environment_settings("missing")


def test_runtime_config_legacy_executor_config_alias():
    rc = RuntimeConfig()
    rc.configure(
        default_environment="legacy",
        environments={"legacy": {"executor": "local", "config": {"queue": "default"}}},
    )
    resolved = rc.resolve_environment_settings("legacy")
    assert resolved["executor_config"] == {"queue": "default"}


def test_runtime_config_merging_and_removal():
    rc = RuntimeConfig()
    rc.configure(environments={"temp": {"executor": "local", "timeout": 3}})
    assert "temp" in rc.environments

    rc.configure(environments={"temp": None})
    assert "temp" not in rc.environments


def test_runtime_config_merge_validation_errors():
    rc = RuntimeConfig()
    with pytest.raises(TypeError, match="environments must be"):
        rc.configure(environments=["bad"])  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="must be a dict"):
        rc.configure(environments={"bad": "value"})  # type: ignore[dict-item]

    with pytest.raises(ValueError, match="invalid delivery_cancel_mode"):
        rc.configure(environments={"bad": {"delivery_cancel_mode": "invalid"}})

    with pytest.raises(ValueError, match="invalid delivery_orphan_policy"):
        rc.configure(environments={"bad": {"delivery_orphan_policy": "invalid"}})


def test_runtime_config_resolve_config_file_missing(tmp_path: Path, monkeypatch):
    rc = RuntimeConfig()
    missing_abs = tmp_path / "missing.py"
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        rc.configure(config_file=str(missing_abs))

    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        rc.configure(config_file="nested/missing.py")

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        rc.configure(config_file="nope.py")


def test_runtime_config_default_environment_auto_insert():
    rc = RuntimeConfig()
    rc.configure(default_environment="custom", environments={"default": None})
    assert rc.default_environment == "custom"
    assert "custom" in rc.environments
    assert "default" in rc.environments


def test_runtime_config_load_module_spec_error(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "wove_config.py"
    cfg.write_text("WOVE_CONFIG = {}", encoding="utf-8")
    rc = RuntimeConfig()

    monkeypatch.setattr("wove.runtime.importlib.util.spec_from_file_location", lambda *_a, **_k: None)
    with pytest.raises(RuntimeError, match="Could not load config file"):
        rc._load_settings_module(cfg)


def test_runtime_config_wove_config_must_be_dict(tmp_path: Path):
    cfg = tmp_path / "wove_config.py"
    cfg.write_text("WOVE_CONFIG = 123", encoding="utf-8")
    rc = RuntimeConfig()

    with pytest.raises(TypeError, match="WOVE_CONFIG in config file must be a dictionary"):
        rc.configure(config_file=str(cfg))


def test_runtime_config_module_level_fallback(tmp_path: Path):
    cfg = tmp_path / "wove_config.py"
    cfg.write_text(
        "default_environment = 'env_a'\n"
        "environments = {'env_a': {'executor': 'local'}}\n"
        "error_mode = 'return'\n",
        encoding="utf-8",
    )
    rc = RuntimeConfig()
    rc.configure(config_file=str(cfg))
    assert rc.default_environment == "env_a"
    assert rc.global_defaults["error_mode"] == "return"


def test_runtime_config_discover_returns_none_when_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = RuntimeConfig()
    assert rc._discover_config_file("does-not-exist.py") is None
