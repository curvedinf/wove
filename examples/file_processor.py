"""
Example: Concurrent File Processor with Nested Parallelism
This script demonstrates a file processing pipeline that uses Wove for
two levels of concurrency:
1.  Top-Level Mapping (`@w.do(file_list)`): The script discovers a list of
    text files and uses Wove's task mapping to process each file concurrently.
2.  Nested Mapping (`merge(callable, iterable)`): Within each file-processing
    task, the script reads all words and uses `merge` to apply a transformation
    function (e.g., counting vowels) to each word in parallel.
This "fan-out, fan-in" pattern at multiple levels is highly effective for
I/O- and CPU-bound tasks that can be broken down into smaller, independent
units of work, such as data preprocessing, log analysis, or batch processing
of any kind.
"""

import asyncio
import time
import os
import re
from wove import weave, merge

# --- File Paths ---
CURRENT_DIR = os.path.dirname(__file__) or "."
DATA_DIR = os.path.join(CURRENT_DIR, "sample_data")


# --- Sub-processing function (not a Wove task) ---
def count_vowels(word: str) -> dict:
    """A simple, synchronous function to process a single word."""
    time.sleep(0.001)  # Simulate a small amount of CPU work
    vowel_count = len(re.findall(r"[aeiou]", word.lower()))
    return {"word": word, "vowels": vowel_count}


async def run_file_processor_example():
    """
    Runs the concurrent file processing example.
    """
    print("--- Running Concurrent File Processor Example ---")
    start_time = time.time()

    # Discover the files to process.
    file_paths = [
        os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith(".txt")
    ]
    print(f"Found {len(file_paths)} files to process concurrently.")

    async with weave() as w:
        # 1. TOP-LEVEL MAPPING: Process each file concurrently.
        # This task is mapped over the list of file paths.
        @w.do(file_paths)
        async def process_file(file_path):
            print(f"-> [File] Started processing: {os.path.basename(file_path)}")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            words = content.split()

            # 2. NESTED MAPPING: Process words from the file concurrently.
            # `merge` is used here to run `count_vowels` for each word.
            # Since `count_vowels` is sync, Wove runs it in a thread pool.
            word_results = await merge(count_vowels, words)

            total_vowels = sum(r["vowels"] for r in word_results)
            print(
                f"<- [File] Finished processing: {os.path.basename(file_path)}. Found {total_vowels} vowels."
            )

            return {
                "file": os.path.basename(file_path),
                "word_count": len(words),
                "total_vowels": total_vowels,
            }

        # 3. SUMMARY: This final task runs after all files are processed.
        # It receives a list of results from the `process_file` task.
        @w.do
        def summarize_results(process_file):
            print("-> [Summary] All files processed. Aggregating results...")
            total_files = len(process_file)
            total_words = sum(r["word_count"] for r in process_file)
            total_vowels = sum(r["total_vowels"] for r in process_file)

            summary = {
                "total_files_processed": total_files,
                "total_words_analyzed": total_words,
                "grand_total_vowels": total_vowels,
            }
            print("<- [Summary] Aggregation complete.")
            return summary

    duration = time.time() - start_time

    # --- Verification ---
    final_summary = w.result.final
    print("\n--- Verification ---")
    print(f"Final Summary: {final_summary}")

    assert final_summary["total_files_processed"] == 3
    assert final_summary["total_words_analyzed"] == 26
    assert final_summary["grand_total_vowels"] == 50

    print(f"\nTotal execution time: {duration:.2f} seconds")
    print("--- Concurrent File Processor Example Finished ---")


def setup_sample_files():
    """Creates dummy files for the example to run."""
    print("Creating sample data files...")
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(os.path.join(DATA_DIR, "file_1.txt"), "w") as f:
        f.write("apple banana orange grapefruit strawberry melon blueberry raspberry")

    with open(os.path.join(DATA_DIR, "file_2.txt"), "w") as f:
        f.write("python java c++ javascript typescript rust go kotlin swift")

    with open(os.path.join(DATA_DIR, "file_3.txt"), "w") as f:
        f.write("red green blue yellow purple orange black white gray")


def cleanup_files():
    """Removes the generated sample data directory."""
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            os.remove(os.path.join(DATA_DIR, f))
        os.rmdir(DATA_DIR)
        print(f"Cleaned up sample data directory: {DATA_DIR}")


if __name__ == "__main__":
    setup_sample_files()
    try:
        asyncio.run(run_file_processor_example())
    finally:
        cleanup_files()
