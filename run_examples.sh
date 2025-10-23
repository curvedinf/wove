#!/bin/bash
echo "--- Timing API Aggregator Example ---"
time python3.14t examples/api_aggregator.py
echo "\n"
echo "--- Timing Dynamic Workflow Example ---"
time python3.14t examples/dynamic_workflow.py
echo "\n"
echo "--- Timing Error Handling Example ---"
time python3.14t examples/error_handling.py
echo "\n"
echo "--- Timing ETL Pipeline Example ---"
time python3.14t examples/etl_pipeline.py
echo "\n"
echo "--- Timing Django-style (example.py) Example ---"
time python3.14t examples/example.py
echo "\n"
echo "--- Timing ML Pipeline Example ---"
time python3.14t examples/ml_pipeline.py
echo "\n"
echo "--- Timing File Processor Example ---"
time python3.14t examples/file_processor.py
echo "\n"
echo "--- Timing Debug Example ---"
time python3.14t examples/debug_example.py
echo "\n"
echo "--- Timing Chained Mapping Example ---"
time python3.14t examples/chained_mapping.py
