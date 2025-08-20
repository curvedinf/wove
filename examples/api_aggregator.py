"""
Example: API Aggregator
This script demonstrates a common pattern where a list of item IDs is fetched,
and then details for each item are fetched concurrently from a real-world API
using Wove's task mapping feature.
This pattern is useful for:
- Batch processing database records.
- Calling a secondary API endpoint for each result from a primary list.
- Any situation requiring a "fan-out" of concurrent operations.
"""

import asyncio
import time
import requests
from wove import weave


def fetch_post_details(post_id: int):
    """
    Fetches post details from the JSONPlaceholder API.
    This is a synchronous, I/O-bound function. Wove will run it in a
    thread pool to avoid blocking the event loop.
    """
    url = f"https://jsonplaceholder.typicode.com/posts/{post_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching post {post_id}: {e}")
        return None


async def run_api_aggregator_example():
    """
    Runs the API aggregation example.
    """
    print("--- Running API Aggregator Example ---")
    # We will fetch posts with IDs from 1 to 20 from a public API.
    post_ids = list(range(1, 21))
    print(f"Found {len(post_ids)} post IDs to process.")
    start_time = time.time()
    async with weave() as w:
        # This is the mapped task. `wove` will run `processed_post`
        # concurrently for each ID in `post_ids`.
        # Because `fetch_post_details` is a regular (sync) function,
        # Wove automatically runs it in a thread pool.
        @w.do(post_ids)
        def processed_post(post_id):
            # The `post_id` parameter receives a value from the `post_ids` iterable.
            return fetch_post_details(post_id)

        # This final task depends on the mapped task. It receives a list
        # containing all the results from the `processed_post` executions.
        @w.do
        def summary(processed_post):
            print("All post details fetched.")
            # `processed_post` is a list of dictionaries here.
            # Filter out any `None` results from failed requests.
            successful_posts = [p for p in processed_post if p is not None]
            item_count = len(successful_posts)
            return f"Successfully aggregated data for {item_count} posts."

    duration = time.time() - start_time
    # The result of a mapped task is a list, in the same order as the input.
    # It will contain `None` for any requests that failed.
    all_results = w.result["processed_post"]
    assert len(all_results) == len(post_ids)

    # Check a successful result
    first_successful_post = next((p for p in all_results if p is not None), None)
    if first_successful_post:
        assert "id" in first_successful_post
        assert "title" in first_successful_post
    print(f"\nTotal execution time: {duration:.2f} seconds")
    print(f"Final summary: {w.result.final}")
    print("--- API Aggregator Example Finished ---")


if __name__ == "__main__":
    asyncio.run(run_api_aggregator_example())
