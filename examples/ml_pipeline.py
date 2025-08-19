"""
Example: Machine Learning Pipeline
This script demonstrates a common ML workflow using Wove to manage a
"diamond" dependency graph.
- Load Data: A single task fetches the initial raw dataset.
- Feature Engineering (Parallel): Multiple independent tasks process the
  raw data to create different feature sets concurrently. These are now
  CPU-bound to simulate heavy computation.
- Train Model: A final task waits for all feature engineering to complete,
  then combines the feature sets to train a model.
This pattern is useful for parallelizing data preparation steps.
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

async def run_ml_pipeline_example():
    """
    Runs the ML pipeline example.
    """
    print("--- Running ML Pipeline Example ---")
    start_time = time.time()
    num_records = 200_000

    async with weave() as w:
        # 1. LOAD: Fetch the raw dataset.
        @w.do
        async def load_raw_data():
            print("-> [1] Loading raw data...")
            await asyncio.sleep(0.05)
            print(f"<- [1] Raw data loaded ({num_records} records).")
            return {
                "features": list(range(num_records)),
                "labels": [i % 2 for i in range(num_records)]
            }

        # 2. FEATURE ENGINEERING (Parallel): These two tasks depend on
        # `load_raw_data` and will run concurrently. They are now SYNC, CPU-bound.
        @w.do
        def engineer_polynomial_features(load_raw_data):
            print("-> [2a] Engineering polynomial features (CPU-bound)...")
            # Simulate heavy computation instead of I/O wait
            cpu_intensive_task(20_000_000)
            features = load_raw_data["features"]
            poly_features = [(x, x**2) for x in features]
            print("<- [2a] Polynomial features engineered.")
            return poly_features

        @w.do
        def engineer_statistical_features(load_raw_data):
            print("-> [2b] Engineering statistical features (CPU-bound)...")
            # Simulate a longer CPU task
            cpu_intensive_task(30_000_000)
            features = load_raw_data["features"]
            mean = sum(features) / len(features)
            stat_features = [(x - mean) for x in features]
            print("<- [2b] Statistical features engineered.")
            return stat_features

        # 3. TRAIN (Combine): This task depends on both feature engineering
        # tasks. It will only run after both are complete.
        @w.do
        def train_model(engineer_polynomial_features, engineer_statistical_features):
            print("-> [3] Training model with combined features...")
            # In a real scenario, you'd combine these features into a single matrix.
            # Here, we just confirm we have both sets of data.
            num_poly_features = len(engineer_polynomial_features)
            num_stat_features = len(engineer_statistical_features)
            
            print(f"<- [3] Model trained with {num_poly_features} poly features and {num_stat_features} stat features.")
            return {"status": "trained", "poly_feature_count": num_poly_features, "stat_feature_count": num_stat_features}

    duration = time.time() - start_time
    
    # Verification
    final_result = w.result.final
    assert final_result["status"] == "trained"
    assert final_result["poly_feature_count"] == num_records
    assert final_result["stat_feature_count"] == num_records
    
    print(f"\nTotal execution time: {duration:.2f} seconds")
    # Because the feature engineering tasks are CPU-bound and run in separate
    # threads, the total time will be significantly longer than the original
    # I/O-bound example.
    print(f"Final model status: {w.result.final}")
    print("--- ML Pipeline Example Finished ---")

if __name__ == "__main__":
    asyncio.run(run_ml_pipeline_example())
