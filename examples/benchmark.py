import asyncio
import threading
import time
import wove
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger()

# Parameters for the benchmark
NUM_TASKS = 200
CPU_LOAD_ITERATIONS = 100000  # Number of iterations for CPU-bound work
IO_SLEEP_DURATION = 0.1  # Seconds for I/O-bound work

def cpu_bound_task():
    """A simple CPU-bound task."""
    for i in range(CPU_LOAD_ITERATIONS):
        _ = i * i

def io_bound_task():
    """A simple I/O-bound task."""
    time.sleep(IO_SLEEP_DURATION)

def combined_task(dummy_param: int):
    """A task that combines CPU and I/O work."""
    # The dummy_param is used by the mapping call, but not in the function body.
    cpu_bound_task()
    io_bound_task()

# --- Threading Implementation ---
def run_threading_benchmark():
    log.info("--- Running Threading Benchmark ---")
    start_time = time.perf_counter()

    threads = []
    for i in range(NUM_TASKS):
        thread = threading.Thread(target=combined_task, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    end_time = time.perf_counter()
    log.info(f"Threading total time: {end_time - start_time:.4f} seconds")
    log.info("-" * 35)

# --- Asyncio Implementation ---
async def async_combined_task(dummy_param: int):
    """Async version of the combined task."""
    await asyncio.to_thread(cpu_bound_task)
    await asyncio.sleep(IO_SLEEP_DURATION)

async def run_asyncio_benchmark_async():
    log.info("--- Running Asyncio Benchmark ---")
    start_time = time.perf_counter()

    tasks = [async_combined_task(i) for i in range(NUM_TASKS)]
    await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    log.info(f"Asyncio total time: {end_time - start_time:.4f} seconds")
    log.info("-" * 35)

def run_asyncio_benchmark():
    asyncio.run(run_asyncio_benchmark_async())

# --- Wove Implementation ---
def run_wove_benchmark():
    log.info("--- Running Wove Benchmark ---")

    # With the new API, task creation and execution happen when the `with` block closes.
    # We cannot time them separately in the same way.
    # We will time the entire operation.

    start_time = time.perf_counter()

    with wove.weave() as w:
        @w.do(range(NUM_TASKS))
        def wove_task(item):
            # The item from the range is the dummy parameter.
            combined_task(item)

    end_time = time.perf_counter()

    log.info("Wove timing details:")
    for key, value in sorted(w.result.timings.items()):
        log.info(f"  - {key}: {value:.4f}s")

    log.info(f"Wove total time: {end_time - start_time:.4f} seconds")
    log.info("-" * 35)


def main():
    """Main function to run all benchmarks."""
    log.info("Starting performance benchmarks...")
    log.info(f"Number of tasks: {NUM_TASKS}")
    log.info(f"CPU load iterations per task: {CPU_LOAD_ITERATIONS}")
    log.info(f"I/O sleep duration per task: {IO_SLEEP_DURATION}s")
    log.info("=" * 35)

    run_threading_benchmark()
    run_asyncio_benchmark()
    run_wove_benchmark()

    log.info("Benchmarks finished.")

if __name__ == "__main__":
    # When running with `python -m examples.benchmark` from the root,
    # the CWD is the root, so we can just write to "benchmark.log".
    log_path = "benchmark.log"

    with open(log_path, "w") as log_file:
        handler = logging.StreamHandler(log_file)
        handler.setFormatter(logging.Formatter('%(message)s'))
        log.addHandler(handler)

        main()

    # Also print to console
    with open(log_path, "r") as log_file:
        print(log_file.read())
