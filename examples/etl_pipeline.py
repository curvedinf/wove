"""
Example: ETL Pipeline with Dynamic Dispatch
This script demonstrates an ETL (Extract, Transform, Load) pipeline that uses
`wove.merge` to dynamically dispatch tasks based on data content.

- Extract: A task fetches the initial raw data, which includes different
  types of records (e.g., 'standard' and 'premium' users).
- Transform (Dispatch): A central dispatcher task inspects each data record.
  It groups records by type and uses `merge` to concurrently apply different
  transformation functions to each group.
- Load: A final task waits for all transformations to complete and then
  loads the combined, processed data into a destination.

This pattern is useful for workflows where processing logic varies depending on
the input data, allowing for flexible and parallel execution.
"""
import asyncio
import time
import json
import hashlib
from wove import weave, merge

# --- Transformation functions (not Wove tasks) ---
# These functions will be called dynamically by the dispatcher using `merge`.
# They are synchronous to demonstrate how Wove runs them in a thread pool.

def transform_standard_user(user_data: dict):
    """Processes a standard user record."""
    print(f"  [T] Transforming standard user {user_data['id']}...")
    # Simple transformation
    user_data["name"] = user_data["name"].title()
    user_data["access_level"] = "standard"
    # Simulate some work
    time.sleep(0.01)
    return user_data

def transform_premium_user(user_data: dict):
    """Processes a premium user record with a more 'expensive' operation."""
    print(f"  [T] Transforming PREMIUM user {user_data['id']}...")
    # More complex transformation
    user_data["name"] = user_data["name"].upper()
    user_data["access_level"] = "premium"
    # Simulate a more complex, CPU-bound operation like hashing
    payload = json.dumps(user_data, sort_keys=True).encode('utf-8')
    user_data["data_hash"] = hashlib.sha256(payload).hexdigest()
    # Simulate more work
    time.sleep(0.02)
    return user_data

async def run_dynamic_etl_pipeline_example():
    """
    Runs the dynamic ETL pipeline example.
    """
    print("--- Running Dynamic ETL Pipeline Example ---")
    start_time = time.time()
    num_records = 50

    async with weave() as w:
        # 1. EXTRACT: Fetch the raw data source.
        @w.do
        async def extract_source_data():
            print("-> [E] Extracting source data...")
            await asyncio.sleep(0.05)
            # Create a mix of 'standard' and 'premium' users.
            data = []
            for i in range(num_records):
                user_type = "premium" if i % 5 == 0 else "standard"
                data.append({
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "type": user_type,
                })
            print(f"<- [E] Source data extracted ({len(data)} records).")
            return data

        # 2. TRANSFORM (Dispatch): This task groups the data and uses `merge`
        # to dynamically call the correct transformation function for each group.
        @w.do
        async def dispatcher_task(extract_source_data):
            print("-> [T] Dispatcher started. Grouping data by type...")
            premium_users = [u for u in extract_source_data if u['type'] == 'premium']
            standard_users = [u for u in extract_source_data if u['type'] == 'standard']
            print(f"   - Found {len(premium_users)} premium users and {len(standard_users)} standard users.")

            # Create asyncio Tasks to run both merge operations concurrently.
            # `merge` will run the synchronous transform functions in thread pools.
            premium_transform_task = asyncio.create_task(
                merge(transform_premium_user, premium_users)
            )
            standard_transform_task = asyncio.create_task(
                merge(transform_standard_user, standard_users)
            )

            # Wait for both sets of transformations to complete.
            processed_premium = await premium_transform_task
            processed_standard = await standard_transform_task

            print("<- [T] All transformations complete.")
            # Combine the results.
            return processed_premium + processed_standard

        # 3. LOAD: This task depends on the dispatcher. It receives the
        # fully transformed data and loads it.
        @w.do
        def load_destination_data(dispatcher_task):
            print("-> [L] Loading data into destination...")
            # `dispatcher_task` is the combined list of processed users.
            # Here, we just simulate loading by verifying the count.
            num_loaded = len(dispatcher_task)
            print(f"<- [L] Loaded {num_loaded} records.")
            return {"status": "complete", "records_loaded": num_loaded}

    duration = time.time() - start_time

    # Verification
    final_result = w.result.final
    assert final_result["status"] == "complete"
    assert final_result["records_loaded"] == num_records
    
    transformed_data = w.result['dispatcher_task']
    premium_user_example = next(u for u in transformed_data if u['id'] == 0) # User 0 is premium
    standard_user_example = next(u for u in transformed_data if u['id'] == 1) # User 1 is standard
    
    assert premium_user_example['name'] == "USER 0"
    assert premium_user_example['access_level'] == "premium"
    assert 'data_hash' in premium_user_example
    
    assert standard_user_example['name'] == "User 1"
    assert standard_user_example['access_level'] == "standard"
    assert 'data_hash' not in standard_user_example

    print(f"\nTotal execution time: {duration:.2f} seconds")
    print(f"Final status: {w.result.final}")
    print("--- Dynamic ETL Pipeline Example Finished ---")

if __name__ == "__main__":
    asyncio.run(run_dynamic_etl_pipeline_example())
