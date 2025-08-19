#!/bin/bash

# Clear the log file before running tests
> /tmp/wove_debug.log

echo "Running tests..."
# Run tests and save the exit code.
pytest tests/test_core.py
PYTEST_EXIT_CODE=$?

echo ""
echo "--- wove_debug.log contents ---"
# Display the log file regardless of the test outcome
cat /tmp/wove_debug.log

# Exit with the original pytest exit code to signal success/failure
exit $PYTEST_EXIT_CODE
