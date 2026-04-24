import unittest.mock
import pytest
import pickle
from wove.background import main

@pytest.fixture
def mock_dependencies():
    with unittest.mock.patch('sys.argv', ['wove/background.py', 'test_file']), \
         unittest.mock.patch('builtins.open', unittest.mock.mock_open()), \
         unittest.mock.patch('wove.background.dispatch_load') as mock_load, \
         unittest.mock.patch('os.remove') as mock_remove, \
         unittest.mock.patch('os.path.exists', return_value=True), \
         unittest.mock.patch('asyncio.run') as mock_run:
        mock_run.side_effect = lambda coro: coro.close()
        yield mock_load, mock_remove, mock_run

def test_main_success(mock_dependencies):
    mock_load, mock_remove, mock_run = mock_dependencies

    mock_wcm = unittest.mock.MagicMock()
    mock_wcm._on_done_callback = unittest.mock.MagicMock()
    mock_load.return_value = mock_wcm

    main()

    mock_load.assert_called_once()
    mock_remove.assert_called_once_with('test_file')
    mock_run.assert_called_once()

def test_main_file_not_found(mock_dependencies):
    mock_load, mock_remove, mock_run = mock_dependencies
    mock_load.side_effect = FileNotFoundError

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1

def test_main_unpickling_error(mock_dependencies):
    mock_load, mock_remove, mock_run = mock_dependencies
    mock_load.side_effect = pickle.UnpicklingError

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1

def test_main_no_args():
    with unittest.mock.patch('sys.argv', ['wove/background.py']), \
         pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_main_executes_sync_on_done_callback(tmp_path):
    events = []

    class FakeWCM:
        def __init__(self):
            self._background = True
            self.result = {"ok": True}
            self._on_done_callback = lambda result: events.append(("sync", result))

        async def __aenter__(self):
            events.append(("enter_background", self._background))
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            del exc_type, exc_val, exc_tb
            events.append(("exit_background", self._background))

    fake = FakeWCM()
    with unittest.mock.patch("sys.argv", ["wove/background.py", str(tmp_path / "ctx.pkl")]), \
         unittest.mock.patch("builtins.open", unittest.mock.mock_open()), \
         unittest.mock.patch("wove.background.dispatch_load", return_value=fake), \
         unittest.mock.patch("os.path.exists", return_value=False):
        main()

    assert ("enter_background", False) in events
    assert ("exit_background", False) in events
    assert ("sync", {"ok": True}) in events


def test_main_executes_async_on_done_callback(tmp_path):
    events = []

    class FakeWCM:
        def __init__(self):
            self._background = True
            self.result = {"ok": True}

            async def callback(result):
                events.append(("async", result))

            self._on_done_callback = callback

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            del exc_type, exc_val, exc_tb

    fake = FakeWCM()
    with unittest.mock.patch("sys.argv", ["wove/background.py", str(tmp_path / "ctx.pkl")]), \
         unittest.mock.patch("builtins.open", unittest.mock.mock_open()), \
         unittest.mock.patch("wove.background.dispatch_load", return_value=fake), \
         unittest.mock.patch("os.path.exists", return_value=False):
        main()

    assert ("async", {"ok": True}) in events
