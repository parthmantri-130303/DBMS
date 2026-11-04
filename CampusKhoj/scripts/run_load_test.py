import concurrent.futures
import json
import random
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000"
CONCURRENCY = 100
DURATION_SECONDS = 30

def http_post(url, data, headers=None):
    if headers is None:
        headers = {}
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, str(e)

def http_get(url, headers=None):
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = (time.perf_counter() - start) * 1000.0
            return resp.status, elapsed
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        return e.code, elapsed
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        return 0, elapsed

def main():
    print(f"============================================================")
    print(f" CAMPUSKHOJ API LOAD TEST: 100 CONCURRENT USERS ({DURATION_SECONDS} SECONDS)")
    print(f" Target: {BASE_URL} (Live MySQL 8 `campuskhoj_demo`)")
    print(f"============================================================")

    # 1. Obtain student and admin JWT tokens
    student_pwd = os.environ.get("KHOJ_TEST_STUDENT_PASSWORD", "Student@123")
    staff_pwd = os.environ.get("KHOJ_TEST_STAFF_PASSWORD", "Staff@CampusKhoj2026!")

    status, res = http_post(f"{BASE_URL}/api/v1/auth/login", {
        "username": "1251150353",
        "password": student_pwd,
        "portal": "student"
    })
    if status != 200 or "token" not in res:
        print(f"Failed to log in as student: status={status}, response={res}")
        sys.exit(1)
    student_token = res["token"]

    status, res = http_post(f"{BASE_URL}/api/v1/auth/login", {
        "username": "admin",
        "password": staff_pwd,
        "portal": "admin"
    })
    if status != 200 or "token" not in res:
        print(f"Failed to log in as admin: status={status}, response={res}")
        sys.exit(1)
    admin_token = res["token"]

    student_headers = {"Authorization": f"Bearer {student_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    endpoints = [
        # (weight, method, path, headers)
        (40, "/api/v1/campuses/1/lost", student_headers),
        (40, "/api/v1/campuses/1/found", student_headers),
        (20, "/api/v1/campuses/2/lost", student_headers),
        (20, "/api/v1/campuses/2/found", student_headers),
        (15, "/api/v1/found/1", student_headers),
        (15, "/api/v1/timeline/FOUND/1", student_headers),
        (10, "/api/v1/notifications?limit=5", student_headers),
        (15, "/api/v1/admin/dashboard", admin_headers),
        (10, "/api/v1/admin/claims?status=PENDING", admin_headers),
        (5,  "/api/v1/admin/audit-logs", admin_headers)
    ]

    total_weight = sum(w for w, _, _ in endpoints)
    choices = []
    for w, path, h in endpoints:
        choices.extend([(path, h)] * w)

    latencies = []
    status_counts = {}
    stop_time = time.time() + DURATION_SECONDS
    total_requests = 0

    def worker_loop(worker_id):
        nonlocal total_requests
        worker_latencies = []
        worker_statuses = {}
        worker_ip = f"10.20.{worker_id // 250}.{worker_id % 250 + 1}"
        while time.time() < stop_time:
            path, base_h = random.choice(choices)
            h = dict(base_h)
            h["X-Forwarded-For"] = worker_ip
            url = f"{BASE_URL}{path}"
            status, latency = http_get(url, h)
            worker_latencies.append(latency)
            worker_statuses[status] = worker_statuses.get(status, 0) + 1
            # Realistic think time: 200-400 ms
            time.sleep(random.uniform(0.2, 0.4))
        return worker_latencies, worker_statuses

    start_bench = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(worker_loop, i) for i in range(CONCURRENCY)]
        for f in concurrent.futures.as_completed(futures):
            wl, ws = f.result()
            latencies.extend(wl)
            for s, c in ws.items():
                status_counts[s] = status_counts.get(s, 0) + c

    total_time = time.perf_counter() - start_bench
    total_reqs = len(latencies)
    throughput = total_reqs / total_time if total_time > 0 else 0

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0
    p90 = latencies[int(len(latencies) * 0.90)] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    min_latency = latencies[0] if latencies else 0
    max_latency = latencies[-1] if latencies else 0

    success_reqs = status_counts.get(200, 0)
    error_reqs = sum(c for s, c in status_counts.items() if s != 200)
    error_rate = (error_reqs / total_reqs * 100.0) if total_reqs > 0 else 0

    report = {
        "concurrency": CONCURRENCY,
        "duration_seconds": round(total_time, 2),
        "total_requests": total_reqs,
        "throughput_rps": round(throughput, 2),
        "status_distribution": status_counts,
        "success_rate_pct": round((success_reqs / total_reqs * 100.0) if total_reqs else 0, 2),
        "error_rate_pct": round(error_rate, 2),
        "latencies_ms": {
            "min": round(min_latency, 2),
            "avg": round(avg_latency, 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "max": round(max_latency, 2)
        }
    }

    print("\n--- LOAD TEST RESULTS ---")
    print(f"Total Completed Requests: {total_reqs}")
    print(f"Duration:                 {report['duration_seconds']}s")
    print(f"Throughput:               {report['throughput_rps']} req/s")
    print(f"Status Codes:             {status_counts}")
    print(f"Error Rate:               {report['error_rate_pct']}%")
    print(f"Latency p50 (Median):     {report['latencies_ms']['p50']} ms")
    print(f"Latency p95:              {report['latencies_ms']['p95']} ms")
    print(f"Latency p99:              {report['latencies_ms']['p99']} ms")
    print(f"Latency Max:              {report['latencies_ms']['max']} ms")
    print("-------------------------\n")

    with open("docs/load_test_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
