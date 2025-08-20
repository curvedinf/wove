#!/bin/bash
echo "--- Timing API Aggregator Example ---"
time python examples/api_aggregator.py
echo "\n"
echo "--- Timing Dynamic Workflow Example ---"
time python examples/dynamic_workflow.py
echo "\n"
echo "--- Timing Error Handling Example ---"
time python examples/error_handling.py
echo "\n"
echo "--- Timing ETL Pipeline Example ---"
time python examples/etl_pipeline.py
echo "\n"
echo "--- Timing Django-style (example.py) Example ---"
time python examples/example.py
echo "\n"
echo "--- Timing ML Pipeline Example ---"
time python examples/ml_pipeline.py
echo "\n"
echo "--- Timing File Processor Example ---"
time python examples/file_processor.py
