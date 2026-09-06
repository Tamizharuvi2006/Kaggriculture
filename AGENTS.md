# Agent Guidelines & Configuration: Kaggriculture

## Parallel Evaluation Directive (MANDATORY)
* **Parallel Execution with 10 Workers**: Hereafter, every evaluation run, mechanism suite, candidate sweep, and batch simulation MUST execute in parallel across **10 worker processes** (`max_workers=10`).
* Never run batch simulation episodes serially in a single-threaded loop.
* Always use `concurrent.futures.ProcessPoolExecutor(max_workers=10)` or `multiprocessing.Pool(processes=10)` to parallelize match evaluations.
* Ensure all multiprocessing scripts use standard `__main__` entrypoints (`if __name__ == '__main__':`) for full Windows multiprocessing compatibility.
