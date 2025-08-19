import asyncio

class WoveResult:
    """
    A container for the results of a weave block.
    Supports dictionary-style access by task name, unpacking in definition order,
    and a `.final` shortcut to the last-defined task's result.
    """
    def __init__(self, definition_order):
        self._results = {}
        self._definition_order = definition_order
        self._is_complete = asyncio.Event()

    def __getitem__(self, key):
        return self._results[key]

    def __iter__(self):
        return (self._results[key] for key in self._definition_order)

    def __len__(self):
        return len(self._results)
    
    @property
    def final(self):
        """Returns the result of the last task defined in the weave block."""
        if not self._definition_order:
            return None
        return self._results[self._definition_order[-1]]

    def _set_result(self, key, value):
        self._results[key] = value

    def _mark_complete(self):
        self._is_complete.set()

    async def _wait_for_key(self, key):
        """Waits until a specific result is available."""
        while key not in self._results:
            await self._is_complete.wait()
            self._is_complete.clear()
