#!/bin/bash
pytest > test_debug_logs.txt 2>&1
echo $? > test_exit_code.txt
