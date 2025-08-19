#!/bin/bash

echo "--- Timing API Aggregator Example ---"
time python examples/api_aggregator.py
echo "\n"

echo "--- Timing ETL Pipeline Example ---"
time python examples/etl_pipeline.py
echo "\n"

echo "--- Timing ML Pipeline Example ---"
time python examples/ml_pipeline.py
