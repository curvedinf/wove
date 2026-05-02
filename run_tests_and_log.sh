#!/bin/bash
set -o pipefail

pytest --cov=wove --cov-report=term-missing --cov-report=json 2>&1 | tee test_debug_logs.txt
status=${PIPESTATUS[0]}
echo "$status" > test_exit_code.txt
exit "$status"
