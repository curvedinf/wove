"""
Example: ETL Pipeline
This script demonstrates a simple ETL (Extract, Transform, Load) pipeline
using Wove to manage a "fan-out, fan-in" dependency graph.
- Extract: A single task fetches the initial raw data.
- Transform: Multiple independent tasks process the raw data concurrently (fan-out).
- Load: A final task waits for all transformations to complete and then
  combines their results to load into a destination (fan-in).
This pattern is useful for parallel data processing workflows.
"""
import asyncio
import time
from wove import weave

async def run_etl_pipeline_example():
    """
    Runs the ETL pipeline example.
    """
    print("--- Running ETL Pipeline Example ---")
    start_time = time.time()

    async with weave() as w:
        # 1. EXTRACT: Fetch the raw data source.
        @w.do
        async def extract_source_data():
            print("-> [E] Extracting source data...")
            await asyncio.sleep(0.05)
            print("<- [E] Source data extracted.")
            return [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
            ]

        # 2. TRANSFORM (Fan-out): These two tasks depend on `extract_source_data`
        # and will run concurrently after it completes.
        @w.do
        async def transform_user_profiles(extract_source_data):
            print("-> [T1] Transforming user profiles...")
            await asyncio.sleep(0.1)
            transformed = [
                {**user, "name": user["name"].upper()}
                for user in extract_source_data
            ]
            print("<- [T1] User profiles transformed.")
            return transformed

        @w.do
        async def transform_add_metadata(extract_source_data):
            print("-> [T2] Adding metadata...")
            await asyncio.sleep(0.15) # Simulate a longer I/O task
            metadata = {user["id"]: {"status": "active"} for user in extract_source_data}
            print("<- [T2] Metadata added.")
            return metadata

        # 3. LOAD (Fan-in): This task depends on both transformation tasks.
        # It will only run after both are complete, combining their results.
        @w.do
        def load_destination(transform_user_profiles, transform_add_metadata):
            print("-> [L] Loading data into destination...")
            combined_data = []
            for user_profile in transform_user_profiles:
                user_id = user_profile["id"]
                if user_id in transform_add_metadata:
                    combined_data.append(
                        {**user_profile, "metadata": transform_add_metadata[user_id]}
                    )
            
            # In a real ETL, this would write to a database, file, or API.
            print(f"<- [L] Loaded {len(combined_data)} records.")
            return combined_data

    duration = time.time() - start_time
    
    # Verification
    final_result = w.result.final
    assert len(final_result) == 2
    assert final_result[0]["name"] == "ALICE"
    assert final_result[0]["metadata"]["status"] == "active"
    assert final_result[1]["name"] == "BOB"

    print(f"\nTotal execution time: {duration:.2f} seconds")
    # Because T1 and T2 run in parallel, total time is ~ sleep(E) + max(sleep(T1), sleep(T2))
    # Expected: ~0.05s + ~0.15s = ~0.20s
    assert duration < 0.25 
    print(f"Final loaded data: {w.result.final}")
    print("--- ETL Pipeline Example Finished ---")

if __name__ == "__main__":
    asyncio.run(run_etl_pipeline_example())
