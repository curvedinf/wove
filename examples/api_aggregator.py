"""
Example: API Aggregator

This script demonstrates a common pattern where a list of item IDs is fetched
from one source, and then details for each item are fetched concurrently from
another source using Wove's task mapping feature.

This pattern is useful for:
- Batch processing database records.
- Calling a secondary API endpoint for each result from a primary list.
- Any situation requiring a "fan-out" of concurrent operations.
"""
import asyncio
import time

from wove import weave


async def fetch_item_details(item_id: int, api_key: str):
    """Simulates fetching detailed data for a single item from an API."""
    print(f"-> Fetching details for item {item_id}...")
    # Simulate network latency that varies slightly per item
    await asyncio.sleep(0.1 + (item_id % 3) * 0.05)
    print(f"<- Received details for item {item_id}")
    return {"id": item_id, "data": f"Details for item {item_id}", "key_used": api_key}


async def run_api_aggregator_example():
    """
    Runs the API aggregation example.
    """
    print("--- Running API Aggregator Example ---")

    # In a real application, these IDs would be fetched from a primary API call
    # or database query before the weave block begins.
    item_ids = [101, 102, 103, 104, 105]
    print(f"Found {len(item_ids)} item IDs to process: {item_ids}")

    start_time = time.time()

    async with weave() as w:
        # This task could represent fetching a shared resource, like an API key
        # or configuration, that all sub-tasks will need.
        @w.do
        def api_key():
            return "secret-api-key-12345"

        # This is the mapped task. `wove` will run `fetch_item_details`
        # concurrently for each ID in `item_ids`.
        @w.do(item_ids)
        async def processed_item(item_id, api_key):
            # The `item_id` parameter receives a value from the `item_ids` iterable.
            # The `api_key` parameter is injected from the result of the `api_key` task.
            return await fetch_item_details(item_id, api_key)

        # This final task depends on the mapped task. It receives a list
        # containing all the results from the `processed_item` executions.
        @w.do
        def summary(processed_item):
            print("All item details fetched.")
            # `processed_item` is a list of dictionaries here.
            item_count = len(processed_item)
            return f"Successfully aggregated data for {item_count} items."

    duration = time.time() - start_time

    # The result of a mapped task is a list, in the same order as the input.
    assert len(w.result['processed_item']) == len(item_ids)
    assert w.result['processed_item'][0]['id'] == 101

    print(f"\nTotal execution time: {duration:.2f} seconds")
    print(f"Final summary: {w.result.final}")
    print("--- API Aggregator Example Finished ---")


if __name__ == "__main__":
    asyncio.run(run_api_aggregator_example())
