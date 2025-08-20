"""
Example: Machine Learning Pipeline with NumPy
This script demonstrates a common ML workflow using Wove to manage a
"diamond" dependency graph with realistic CPU-bound tasks.
- Load Data: A single task fetches the initial raw dataset as NumPy arrays.
- Feature Engineering (Parallel): Multiple independent tasks process the
  raw data to create different feature sets concurrently. These are synchronous,
  CPU-bound functions using NumPy that Wove runs in a thread pool.
- Train Model: A final task waits for all feature engineering to complete,
  then combines the feature sets into a final design matrix.
This pattern is useful for parallelizing data preparation steps in ML workflows.
"""

import asyncio
import time
import numpy as np
from wove import weave


async def run_ml_pipeline_example():
    """
    Runs the ML pipeline example.
    """
    print("--- Running ML Pipeline Example ---")
    start_time = time.time()
    num_records = 500_000

    async with weave() as w:
        # 1. LOAD: Fetch the raw dataset.
        @w.do
        async def load_raw_data():
            print("-> [1] Loading raw data...")
            await asyncio.sleep(0.05)  # Simulate I/O
            print(f"<- [1] Raw data loaded ({num_records} records).")
            # In a real scenario, this might be loaded from a file or database.
            features = np.arange(num_records, dtype=np.float64)
            labels = features % 2
            return {"features": features, "labels": labels}

        # 2. FEATURE ENGINEERING (Parallel): These two tasks depend on
        # `load_raw_data` and will run concurrently. Because they are synchronous,
        # Wove runs them in a background thread pool.
        @w.do
        def engineer_polynomial_features(load_raw_data):
            print("-> [2a] Engineering polynomial features...")
            # This is a CPU-bound operation using numpy.
            features = load_raw_data["features"]
            # Create a 2nd degree polynomial: (x, x^2)
            poly_features = np.vstack([features, features**2]).T
            print(
                f"<- [2a] Polynomial features engineered. Shape: {poly_features.shape}"
            )
            return poly_features

        @w.do
        def engineer_statistical_features(load_raw_data):
            print("-> [2b] Engineering statistical features (standardization)...")
            # This is another CPU-bound numpy operation.
            features = load_raw_data["features"]
            # Standardize the features (z-score normalization)
            mean = np.mean(features)
            std = np.std(features)
            stat_features = (features - mean) / (std if std > 0 else 1)
            print(
                f"<- [2b] Statistical features engineered. Shape: {stat_features.shape}"
            )
            return stat_features

        # 3. TRAIN (Combine): This task depends on both feature engineering
        # tasks. It will only run after both are complete.
        @w.do
        def train_model(engineer_polynomial_features, engineer_statistical_features):
            print("-> [3] Training model with combined features...")
            # Combine the different feature sets into a single design matrix.
            # engineer_statistical_features is 1D, so we reshape it to 2D for hstack.
            stat_features_reshaped = engineer_statistical_features.reshape(-1, 1)

            design_matrix = np.hstack(
                [engineer_polynomial_features, stat_features_reshaped]
            )

            print(
                f"<- [3] Model trained with combined feature matrix. Shape: {design_matrix.shape}"
            )
            return {"status": "trained", "feature_matrix_shape": design_matrix.shape}

    duration = time.time() - start_time

    # Verification
    final_result = w.result.final
    final_shape = final_result["feature_matrix_shape"]

    assert final_result["status"] == "trained"
    assert final_shape[0] == num_records
    assert final_shape[1] == 3  # (x, x^2) + (z-score) = 3 columns

    print(f"\nTotal execution time: {duration:.2f} seconds")
    # Because the feature engineering tasks run in parallel in a thread pool,
    # the total time is less than the sum of their individual execution times.
    print(f"Final model status: {w.result.final}")
    print("--- ML Pipeline Example Finished ---")


if __name__ == "__main__":
    asyncio.run(run_ml_pipeline_example())
