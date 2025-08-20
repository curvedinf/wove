"""
Example: File-based ETL Pipeline with Dynamic Dispatch
This script demonstrates an ETL (Extract, Transform, Load) pipeline that
processes a local CSV file and uses `wove.merge` to dynamically dispatch
tasks based on data content.
- Extract: A task reads raw data from a dynamically created `source_data.csv`.
- Transform (Dispatch): A central dispatcher task inspects each record,
  groups records by type, and uses `merge` to concurrently apply different
  transformation functions to each group.
- Load: A final task waits for all transformations to complete and then
  loads the combined, processed data into `transformed_data.json`.
This pattern is useful for file-based workflows where processing logic varies
depending on the input data, allowing for flexible and parallel execution.
"""

import asyncio
import time
import json
import hashlib
import csv
import os
from wove import weave, merge

# --- File Paths ---
CURRENT_DIR = os.path.dirname(__file__) or "."
SOURCE_CSV_PATH = os.path.join(CURRENT_DIR, "source_data.csv")
DESTINATION_JSON_PATH = os.path.join(CURRENT_DIR, "transformed_data.json")


# --- Transformation functions (not Wove tasks) ---
def transform_standard_user(user_data: dict):
    """Processes a standard user record."""
    print(f"  [T] Transforming standard user {user_data['id']}...")
    user_data["name"] = user_data["name"].title()
    user_data["access_level"] = "standard"
    time.sleep(0.01)
    return user_data


def transform_premium_user(user_data: dict):
    """Processes a premium user record with a more 'expensive' operation."""
    print(f"  [T] Transforming PREMIUM user {user_data['id']}...")
    user_data["name"] = user_data["name"].upper()
    user_data["access_level"] = "premium"
    payload = json.dumps(user_data, sort_keys=True).encode("utf-8")
    user_data["data_hash"] = hashlib.sha256(payload).hexdigest()
    time.sleep(0.02)
    return user_data


async def run_etl_pipeline_example():
    """
    Runs the file-based ETL pipeline example.
    """
    print("--- Running File-Based ETL Pipeline Example ---")
    start_time = time.time()

    async with weave() as w:
        # 1. EXTRACT: Read the source CSV file.
        @w.do
        async def extract_source_data():
            print(f"-> [E] Extracting source data from {SOURCE_CSV_PATH}...")
            await asyncio.sleep(0.01)  # Simulate I/O latency
            with open(SOURCE_CSV_PATH, mode="r", encoding="utf-8") as infile:
                reader = csv.DictReader(infile)
                data = list(reader)
            print(f"<- [E] Source data extracted ({len(data)} records).")
            return data

        # 2. TRANSFORM (Dispatch): Groups data and uses `merge` to call
        # the correct transformation function for each group.
        @w.do
        async def dispatcher_task(extract_source_data):
            print("-> [T] Dispatcher started. Grouping data by type...")
            premium_users = [u for u in extract_source_data if u["type"] == "premium"]
            standard_users = [u for u in extract_source_data if u["type"] == "standard"]
            print(
                f"   - Found {len(premium_users)} premium users and {len(standard_users)} standard users."
            )

            # Use merge to run transformations concurrently in thread pools.
            premium_transform_task = asyncio.create_task(
                merge(transform_premium_user, premium_users)
            )
            standard_transform_task = asyncio.create_task(
                merge(transform_standard_user, standard_users)
            )
            processed_premium = await premium_transform_task
            processed_standard = await standard_transform_task

            print("<- [T] All transformations complete.")
            return processed_premium + processed_standard

        # 3. LOAD: Receives transformed data and writes it to a JSON file.
        @w.do
        def load_destination_data(dispatcher_task):
            print(f"-> [L] Loading data into destination: {DESTINATION_JSON_PATH}...")
            with open(DESTINATION_JSON_PATH, mode="w", encoding="utf-8") as outfile:
                json.dump(dispatcher_task, outfile, indent=2)

            num_loaded = len(dispatcher_task)
            print(f"<- [L] Loaded {num_loaded} records.")
            return {
                "status": "complete",
                "records_loaded": num_loaded,
                "output_path": DESTINATION_JSON_PATH,
            }

    duration = time.time() - start_time

    # --- Verification ---
    final_result = w.result.final
    assert final_result["status"] == "complete"
    output_path = final_result["output_path"]

    with open(output_path, "r", encoding="utf-8") as f:
        transformed_data = json.load(f)

    num_records_in_source = len(w.result["extract_source_data"])
    assert len(transformed_data) == num_records_in_source
    assert final_result["records_loaded"] == num_records_in_source

    premium_user_example = next((u for u in transformed_data if u["id"] == "0"), None)
    standard_user_example = next((u for u in transformed_data if u["id"] == "1"), None)

    assert premium_user_example is not None
    assert standard_user_example is not None

    assert premium_user_example["name"] == "USER 0"
    assert premium_user_example["access_level"] == "premium"
    assert "data_hash" in premium_user_example

    assert standard_user_example["name"] == "User 1"
    assert standard_user_example["access_level"] == "standard"
    assert "data_hash" not in standard_user_example

    print(f"\nTotal execution time: {duration:.2f} seconds")
    print(f"Final status: {w.result.final['status']}")
    print(f"Output written to: {output_path}")
    print("--- File-Based ETL Pipeline Example Finished ---")


def setup_source_file():
    """Creates a dummy CSV for the example to run."""
    print(f"Creating dummy source file: {SOURCE_CSV_PATH}")
    with open(SOURCE_CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "email", "type"])
        for i in range(50):
            user_type = "premium" if i % 5 == 0 else "standard"
            writer.writerow([i, f"User {i}", f"user{i}@example.com", user_type])


def cleanup_files():
    """Removes the generated source and destination files."""
    if os.path.exists(SOURCE_CSV_PATH):
        os.remove(SOURCE_CSV_PATH)
        print(f"Cleaned up {SOURCE_CSV_PATH}.")
    if os.path.exists(DESTINATION_JSON_PATH):
        os.remove(DESTINATION_JSON_PATH)
        print(f"Cleaned up {DESTINATION_JSON_PATH}.")


if __name__ == "__main__":
    setup_source_file()
    try:
        asyncio.run(run_etl_pipeline_example())
    finally:
        cleanup_files()
