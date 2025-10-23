import sys
import unittest.mock
import pytest
import pickle
from wove.background import main

@pytest.fixture
def mock_dependencies():
    with unittest.mock.patch('sys.argv', ['wove/background.py', 'test_file']), \
         unittest.mock.patch('builtins.open', unittest.mock.mock_open()), \
         unittest.mock.patch('cloudpickle.load') as mock_load, \
         unittest.mock.patch('os.remove') as mock_remove, \
         unittest.mock.patch('os.path.exists', return_value=True), \
         unittest.mock.patch('asyncio.run') as mock_run:
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
