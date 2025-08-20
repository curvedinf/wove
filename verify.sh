#!/bin/bash
if [ ! -f test_exit_code.txt ] || [ "$(<test_exit_code.txt)" != "0" ]; then
    echo "Verification failed: Tests did not pass (test_exit_code.txt is not '0')."
    exit 1
fi
# Check test_debug_logs.txt
if [ ! -s test_debug_logs.txt ]; then
    echo "Verification failed: Test debug log is empty."
    exit 1
fi
echo "Success: All conditions met."
exit 0
