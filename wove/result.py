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
        self._definition_order: List[str] = []
        print("--- [WOVE DEBUG] WoveResult initialized ---")

    def __getitem__(self, key: str) -> Any:
        """
        Retrieves a task's result by its name.

        Args:
            key: The name of the task.

        Returns:
            The result of the specified task.
        """
        print(f"--- [WOVE DEBUG] WoveResult __getitem__('{key}'). Available keys: {list(self._results.keys())}")
        return self._results[key]

    def __iter__(self) -> Iterator[Any]:
        """
        Returns an iterator over the results in their definition order.
        """
        print(f"--- [WOVE DEBUG] WoveResult __iter__(). Definition order: {self._definition_order}")
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
        print(f"--- [WOVE DEBUG] WoveResult .final accessed. Definition order: {self._definition_order}")
        if not self._definition_order:
            print("--- [WOVE DEBUG] .final -> No tasks defined, returning None.")
            return None
        final_key = self._definition_order[-1]
        print(f"--- [WOVE DEBUG] .final -> Returning result for key '{final_key}'.")
        return self._results[final_key]

    def _set_result(self, key: str, value: Any) -> None:
        """Sets a result for a given task key."""
        print(f"--- [WOVE DEBUG] WoveResult _set_result('{key}', ...). Current keys: {list(self._results.keys())}")
        self._results[key] = value
        print(f"--- [WOVE DEBUG] WoveResult _set_result('{key}') complete. New keys: {list(self._results.keys())}")
