from typing import Any, Dict, Iterator, List


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
        self._results: Dict[str, Any] = {}
        self._errors: Dict[str, Exception] = {}
        self._definition_order: List[str] = []
        self.timings: Dict[str, float] = {}

    def __getitem__(self, key: str) -> Any:
        """
        Retrieves a task's result by its name. If the task failed,
        its exception is raised.
        Args:
            key: The name of the task.
        Returns:
            The result of the specified task.
        """
        if key in self._errors:
            raise self._errors[key]
        return self._results[key]

    def __iter__(self) -> Iterator[Any]:
        """
        Returns an iterator over the results in their definition order.
        """
        # This might need to be smarter if we want to iterate over failed tasks too.
        # For now, it iterates over successfully completed tasks' results.
        return (self._results[key] for key in self._definition_order if key in self._results)

    def __len__(self) -> int:
        """
        Returns the number of results currently available.
        """
        return len(self._results)

    def __getattr__(self, name: str) -> Any:
        """
        Retrieves a task's result by its name using attribute access.
        If the task failed, its exception is raised.
        Args:
            name: The name of the task.
        Returns:
            The result of the specified task.
        Raises:
            AttributeError: If no task with that name exists.
        """
        if name in self._errors:
            raise self._errors[name]
        if name in self._results:
            return self._results[name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    @property
    def final(self) -> Any:
        """
        Returns the result of the last task defined in the weave block.
        If the task failed, its exception is raised.
        Returns:
            The result of the final task, or None if no tasks were defined.
        """
        if not self._definition_order:
            return None
        final_key = self._definition_order[-1]
        if final_key in self._errors:
            raise self._errors[final_key]
        # It's possible the final task failed and thus isn't in results.
        return self._results.get(final_key)

    def _add_result(self, key: str, value: Any) -> None:
        """Adds a result for a given task key."""
        self._results[key] = value

    def _add_error(self, key: str, error: Exception) -> None:
        """Adds an error for a given task key."""
        self._errors[key] = error

    def _add_timing(self, key: str, duration: float) -> None:
        """Adds a timing duration for a given task key."""
        self.timings[key] = duration
