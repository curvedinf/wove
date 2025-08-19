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

# A simple CPU-bound function to simulate work
def cpu_intensive_task(iterations):
    """Performs a meaningless but CPU-intensive calculation."""
    result = 0
    for i in range(iterations):
        result += (i * i) % 1000
    return result

async def run_etl_pipeline_example():
    """
    Runs the ETL pipeline example.
    """
    print("--- Running ETL Pipeline Example ---")
    start_time = time.time()
    num_records = 50000

    async with weave() as w:
        # 1. EXTRACT: Fetch the raw data source.
        @w.do
        async def extract_source_data():
            print("-> [E] Extracting source data...")
            await asyncio.sleep(0.05)  # Simulate quick I/O
            print(f"<- [E] Source data extracted ({num_records} records).")
            return [
                {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
                for i in range(num_records)
            ]

        # 2. TRANSFORM (Fan-out): These two tasks depend on `extract_source_data`
        # and will run concurrently. These are now SYNC, CPU-bound functions.
        # Wove will run them in a thread pool.
        @w.do
        def transform_user_profiles(extract_source_data):
            print("-> [T1] Transforming user profiles (CPU-bound)...")
            # Simulate heavy computation instead of I/O wait
            cpu_intensive_task(20_000_000)
            transformed = [
                {**user, "name": user["name"].upper()}
                for user in extract_source_data
            ]
            print("<- [T1] User profiles transformed.")
            return transformed

        @w.do
        def transform_add_metadata(extract_source_data):
            print("-> [T2] Adding metadata (CPU-bound)...")
            # Simulate a longer CPU task
            cpu_intensive_task(30_000_000)
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
    assert len(final_result) == num_records
    assert final_result[0]["name"] == "USER 0"
    assert final_result[0]["metadata"]["status"] == "active"
    assert final_result[1]["name"] == "USER 1"
    
    print(f"\nTotal execution time: {duration:.2f} seconds")
    # Because T1 and T2 are CPU-bound and run in separate threads, the total time
    # will be dictated by the GIL and thread scheduling. The goal is to be
    # significantly longer than the original example.
    print(f"Final loaded data summary: {len(w.result.final)} records processed.")
    print("--- ETL Pipeline Example Finished ---")

if __name__ == "__main__":
    asyncio.run(run_etl_pipeline_example())
