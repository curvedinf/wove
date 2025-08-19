import asyncio
from typing import Any, Dict, Iterator, List
import datetime

LOG_FILE = "/tmp/wove_debug.log"

def _wove_log(message: str):
    """Appends a timestamped message to the wove debug log."""
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.datetime.now().isoformat()
        f.write(f"[{timestamp}] {message}\n")

class WoveResult:
    """
    A container for the results of a weave block.
    Supports dictionary-style access by task name, unpacking in definition order,
    and a `.final` shortcut to the last-defined task's result.
    """
    def __init__(self) -> None:
        """
        Initializes the result container.
        """
        _wove_log(f"RESULT: Initializing WoveResult with id: {id(self)}")
        self._results: Dict[str, Any] = {}
        self._definition_order: List[str] = []
        self._is_complete = asyncio.Event()

    def __getitem__(self, key: str) -> Any:
        """
        Retrieves a task's result by its name.
        Args:
            key: The name of the task.
        Returns:
            The result of the specified task.
        """
        _wove_log(f"RESULT: Getting item '{key}' from WoveResult with id: {id(self)}. Available keys: {list(self._results.keys())}")
        return self._results[key]

    def __iter__(self) -> Iterator[Any]:
        """
        Returns an iterator over the results in their definition order.
        """
        return (self._results[key] for key in self._definition_order)

    def __len__(self) -> int:
        """
        Returns the number of results currently available.
        """
        return len(self._results)
    
    @property
    def final(self) -> Any:
        """
        Returns the result of the last task defined in the weave block.
        Returns:
            The result of the final task, or None if no tasks were defined.
        """
        if not self._definition_order:
            return None
        return self._results[self._definition_order[-1]]

    def _set_result(self, key: str, value: Any) -> None:
        """Sets a result for a given task key."""
        _wove_log(f"RESULT: Setting item '{key}' in WoveResult with id: {id(self)}")
        self._results[key] = value

    def _mark_complete(self) -> None:
        """Signals that a new result has been added."""
        self._is_complete.set()

    async def _wait_for_key(self, key: str) -> None:
        """Waits until a specific result is available."""
        while key not in self._results:
            await self._is_complete.wait()
            self._is_complete.clear()
