"""
Example: Machine Learning Pipeline
This script demonstrates a common ML workflow using Wove to manage a
"diamond" dependency graph.
- Load Data: A single task fetches the initial raw dataset.
- Feature Engineering (Parallel): Multiple independent tasks process the
  raw data to create different feature sets concurrently.
- Train Model: A final task waits for all feature engineering to complete,
  then combines the feature sets to train a model.
This pattern is useful for parallelizing data preparation steps.
"""
import asyncio
import time
from wove import weave

async def run_ml_pipeline_example():
    """
    Runs the ML pipeline example.
    """
    print("--- Running ML Pipeline Example ---")
    start_time = time.time()

    async with weave() as w:
        # 1. LOAD: Fetch the raw dataset.
        @w.do
        async def load_raw_data():
            print("-> [1] Loading raw data...")
            await asyncio.sleep(0.05)
            print("<- [1] Raw data loaded.")
            return {"features": [1, 2, 3, 4, 5], "labels": [0, 1, 0, 1, 1]}

        # 2. FEATURE ENGINEERING (Parallel): These two tasks depend on
        # `load_raw_data` and will run concurrently.
        @w.do
        async def engineer_polynomial_features(load_raw_data):
            print("-> [2a] Engineering polynomial features...")
            await asyncio.sleep(0.1)
            features = load_raw_data["features"]
            poly_features = [(x, x**2) for x in features]
            print("<- [2a] Polynomial features engineered.")
            return poly_features

        @w.do
        async def engineer_statistical_features(load_raw_data):
            print("-> [2b] Engineering statistical features...")
            await asyncio.sleep(0.15)  # Simulate a longer task
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
    assert final_result["poly_feature_count"] == 5
    assert final_result["stat_feature_count"] == 5
    
    print(f"\nTotal execution time: {duration:.2f} seconds")
    # Because 2a and 2b run in parallel, total time is ~ sleep(1) + max(sleep(2a), sleep(2b))
    # Expected: ~0.05s + ~0.15s = ~0.20s
    assert duration < 0.25
    print(f"Final model status: {w.result.final}")
    print("--- ML Pipeline Example Finished ---")

if __name__ == "__main__":
    asyncio.run(run_ml_pipeline_example())
