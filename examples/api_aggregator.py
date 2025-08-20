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
import json
import hashlib
from wove import weave
def fetch_item_details(item_id: int, api_key: str):
    """
    Simulates fetching and processing data for a single item.
    This is a synchronous, CPU-bound function to demonstrate Wove's ability
    to run sync tasks in a thread pool without blocking the event loop.
    """
    # 1. Simulate generating a complex data payload.
    payload = {
        "item_id": item_id,
        "details": f"Some details for item {item_id}",
        "timestamp": time.time(),
        "api_key_used": api_key,
    }
    json_payload = json.dumps(payload, sort_keys=True).encode('utf-8')

    # 2. Simulate a CPU-intensive task, like validation or hashing.
    payload_hash = hashlib.sha256(json_payload).hexdigest()

    # A small sleep to simulate slight I/O or other blocking work.
    # Wove will handle this in a background thread.
    time.sleep(0.01)

    return {"id": item_id, "data": f"Details for item {item_id}", "hash": payload_hash}

async def run_api_aggregator_example():
    """
    Runs the API aggregation example.
    """
    print("--- Running API Aggregator Example ---")
    # In a real application, these IDs would be fetched from a primary API call
    # or database query before the weave block begins.
    # We use a smaller number of items for a clearer example output.
    item_ids = list(range(50))
    print(f"Found {len(item_ids)} item IDs to process.")

    start_time = time.time()
    async with weave() as w:
        # This task could represent fetching a shared resource, like an API key
        # or configuration, that all sub-tasks will need.
        @w.do
        def api_key():
            return "secret-api-key-12345"

        # This is the mapped task. `wove` will run `processed_item`
        # concurrently for each ID in `item_ids`.
        # Because `fetch_item_details` is a regular (sync) function,
        # Wove automatically runs it in a thread pool.
        @w.do(item_ids)
        def processed_item(item_id, api_key):
            # The `item_id` parameter receives a value from the `item_ids` iterable.
            # The `api_key` parameter is injected from the result of the `api_key` task.
            return fetch_item_details(item_id, api_key)

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
    assert w.result['processed_item'][0]['id'] == 0
    assert 'hash' in w.result['processed_item'][0]

    print(f"\nTotal execution time: {duration:.2f} seconds")
    print(f"Final summary: {w.result.final}")
    print("--- API Aggregator Example Finished ---")

if __name__ == "__main__":
    asyncio.run(run_api_aggregator_example())
