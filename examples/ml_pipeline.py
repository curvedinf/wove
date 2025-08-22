# Save as ml_pipeline.py and run `python ml_pipeline.py`
import time
import numpy as np
from wove import Weave, weave
from wove.helpers import fold

# Define the workflow as a reusable class inheriting from `wove.Weave`.
class MLPipeline(Weave):
    # Use the class-based decorator `@Weave.do`.
    # Add robustness: retry on failure and timeout if it takes too long.
    @Weave.do(retries=2, timeout=60.0)
    def load_raw_data(self, num_records: int):
        print(f"-> [1] Loading raw data ({num_records} records)...")
        time.sleep(0.05)  # Simulate I/O
        features = np.arange(num_records, dtype=np.float64)
        print("<- [1] Raw data loaded.")
        return features

    # This task creates batches from the raw data.
    @Weave.do
    def create_batches(self, load_raw_data, batch_size: int):
        print("-> [2] Creating batches...")
        # Use the fold helper to create a list of numpy arrays (batches)
        batches = fold(load_raw_data, batch_size)
        print(f"<- [2] Created {len(batches)} batches of size {batch_size}.")
        return batches

    # This mapped task processes data in chunks.
    # `workers=4` limits concurrency to 4 chunks at a time.
    # `limit_per_minute=600` throttles new tasks to 10/sec.
    @Weave.do("create_batches", workers=4, limit_per_minute=600)
    def process_batch(self, chunk):
        # `chunk` is now a list of numbers, so `len()` works.
        processed_chunk = np.vstack([chunk, np.square(chunk)]).T
        print(f"    -> Processed batch of size {len(chunk)}")
        return processed_chunk

    # This final task waits for all batches to be processed.
    @Weave.do
    def train_model(self, process_batch):
        print("-> [3] Training model...")
        # `process_batch` returns a list of arrays; `vstack` combines them.
        design_matrix = np.vstack(process_batch)
        print(f"<- [3] Model trained. Shape: {design_matrix.shape}")
        return {"status": "trained", "shape": design_matrix.shape}

# --- Synchronous Execution ---
# Pass the class and keyword arguments to the context manager.
with weave(MLPipeline, num_records=100_000, batch_size=1000) as w:
    # The pipeline runs here. You could override tasks inside this
    # block if needed.
    pass

print(f"\nFinal model status: {w.result.final}")
