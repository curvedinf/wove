#!/bin/bash
pytest --cov=wove --cov-report=term-missing --cov-report=json > test_debug_logs.txt 2>&1
echo $? > test_exit_code.txt
