"""Send 100 overlapping public requests for CN11 and report actual timings.

Usage: python tools/load_test.py http://127.0.0.1:5000/api/v1/products
Run only on a disposable local test database; record build and hardware in report.
"""

import concurrent.futures
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request


url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000/api/v1/products"
workers = 100
gate = threading.Barrier(workers)


def hit(_number):
    gate.wait()
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            response.read()
            return response.status, (time.perf_counter() - start) * 1000
    except (urllib.error.URLError, TimeoutError) as error:
        return str(error), (time.perf_counter() - start) * 1000


with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
    start = time.perf_counter()
    results = list(pool.map(hit, range(workers)))
wall_ms = (time.perf_counter() - start) * 1000
times = sorted(ms for _status, ms in results)
ok = sum(status == 200 for status, _ms in results)
print(f"URL: {url}")
print(f"Concurrent users: {workers}; HTTP 200: {ok}/{workers}")
print(f"Wall time: {wall_ms:.0f} ms; median: {statistics.median(times):.0f} ms; "
      f"p95: {times[94]:.0f} ms; max: {times[-1]:.0f} ms")
print("CN11 target (<3000 ms each, 100/100 success):", "MET" if ok == workers and times[-1] < 3000 else "NOT MET")
