#!/bin/bash
# This script verifies the state of the last run.
# It checks if installation was successful, tests passed, and logs were generated.
# Check install_exit_code.txt
if [ ! -f install_exit_code.txt ] || [ "$(<install_exit_code.txt)" != "0" ]; then
    echo "Verification failed: Installation did not succeed (install_exit_code.txt is not '0')."
    exit 1
fi
# Check test_exit_code.txt
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
