import subprocess
import sys

import pytest

from wove.environment import BackendAdapterEnvironmentExecutor, StdioEnvironmentExecutor
from wove.errors import MissingDispatchFeatureError
from wove import serialization


def _hide_cloudpickle(monkeypatch):
    monkeypatch.setattr(serialization, "_cloudpickle", None)
    real_import_module = serialization.importlib.import_module

    def fake_import_module(name):
        if name == "cloudpickle":
            raise ImportError("missing cloudpickle")
        return real_import_module(name)

    monkeypatch.setattr(serialization.importlib, "import_module", fake_import_module)


def test_require_dispatch_reports_install_extra(monkeypatch):
    _hide_cloudpickle(monkeypatch)

    with pytest.raises(MissingDispatchFeatureError) as exc_info:
        serialization.require_dispatch("testing a dispatch-only path.")

    message = str(exc_info.value)
    assert "Wove dispatch features require cloudpickle" in message
    assert 'pip install "wove[dispatch]"' in message
    assert "testing a dispatch-only path" in message


def test_import_wove_does_not_require_dispatch_dependency():
    script = """
import importlib.abc
import sys

class BlockCloudpickle(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "cloudpickle":
            raise ImportError("blocked cloudpickle")
        return None

sys.meta_path.insert(0, BlockCloudpickle())
import wove
assert "MissingDispatchFeatureError" in wove.__all__
"""
    completed = subprocess.run([sys.executable, "-c", script], check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


@pytest.mark.asyncio
async def test_stdio_requires_dispatch_dependency(monkeypatch):
    _hide_cloudpickle(monkeypatch)

    executor = StdioEnvironmentExecutor()
    with pytest.raises(MissingDispatchFeatureError, match="stdio executor"):
        await executor.start(environment_name="stdio", environment_config={}, run_config={})


@pytest.mark.asyncio
async def test_backend_adapter_requires_dispatch_dependency(monkeypatch):
    _hide_cloudpickle(monkeypatch)

    class Adapter:
        required_modules = ()

        def __init__(self, **_kwargs):
            pass

    executor = BackendAdapterEnvironmentExecutor("custom", adapter_class=Adapter)
    with pytest.raises(MissingDispatchFeatureError, match="custom executor"):
        await executor.start(environment_name="backend", environment_config={}, run_config={})
