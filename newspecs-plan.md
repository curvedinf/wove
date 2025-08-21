1.  **Project Setup**:
    *   Create `newspecs.md` and `newspecs-plan.md` (this plan).
    *   Create `precommit.sh` with `ruff check .` and make it executable. Run it and fix any initial linting issues.

2.  **Core Error Handling and Result Access**:
    *   Modify `wove/result.py`: Implement `__getattr__` to allow attribute-style access to results. This method will also be responsible for re-raising exceptions if the stored result is an exception object.
    *   Modify `wove/context.py`: Implement the "store exception" error handling model in `__aexit__`. When a task fails, its exception will be stored in the result object. The `weave` block will *not* raise an exception itself.
    *   Modify `WoveContextManager.do`: Add a check to prevent task names from colliding with built-in `WoveResult` attributes.
    *   Update all existing test files (`test_core.py`, `test_mapping.py`, etc.) to conform to the new "store exception" model. This means changing all `pytest.raises` blocks that wrap `async with weave()` to instead wrap result access (e.g., `w.result.failing_task`).

3.  **Implement Enhanced `@w.do` Parameters**:
    *   Modify `WoveContextManager.do` to accept `retries`, `timeout`, `workers`, and `limit_per_minute`.
    *   Implement the logic for these parameters in `__aexit__`, ensuring they work correctly with the new error handling model.
    *   Create `tests/test_parameters.py` with tests for each new parameter.

4.  **Implement Inheritable Weaves**:
    *   Create `wove/weave.py` with the `Weave` base class and `@Weave.do` decorator.
    *   Modify `WoveContextManager.__init__` to accept a `parent_weave` class, load its tasks, and handle parameter inheritance on override. Also, allow `**initial_values` to be passed to seed the dependency graph.
    *   Create `tests/test_inheritable_weaves.py` with tests for inheritance, overriding, and parameter management.

5.  **Implement Synchronous Usage**:
    *   Add `__enter__` and `__exit__` methods to `WoveContextManager` to allow it to be used as a synchronous context manager.
    *   Create `tests/test_sync.py` to verify this functionality.

6.  **Implement Data-Shaping Helper Functions**:
    *   Add the helper functions (`flatten`, `fold`, etc.) to `wove/helpers.py`.
    *   Create `tests/test_helpers.py` with unit tests for each function.
    *   Expose the functions in `wove/__init__.py`.

7.  **Final Documentation and Review**:
    *   Update `README.md` to document all the new features, including a new "More Spice" example that showcases them working together.
    *   Run the full test suite one last time.
    *   Request a final code review.
    *   Submit all changes in a single, comprehensive commit.
