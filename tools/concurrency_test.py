"""Two real overlapping checkout requests competing for one item (disposable DB)."""

import concurrent.futures
import json
import sys
import threading
import urllib.error
import urllib.request


base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:5000/api/v1"


def call(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(base + path, json.dumps(data).encode() if data is not None else None,
                                     headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        body = error.read()
        return error.code, json.loads(body) if body else None


def login(email, password):
    status, data = call("POST", "/auth/login", {"email": email, "password": password})
    if status != 200:
        raise RuntimeError(f"Login failed for {email}: {data}")
    return data["token"]


admin = login("admin@stardust.test", "Admin12345")
a = login("an@stardust.test", "Customer123")
b = login("binh@stardust.test", "Customer123")
status, result = call("PATCH", "/admin/variants/1", {"stock": 1}, admin)
if status != 200:
    raise RuntimeError(f"Cannot prepare stock: {result}")
for name, token in (("A", a), ("B", b)):
    status, result = call("POST", "/cart/items", {"variant_id": 1, "quantity": 1}, token)
    if status != 201:
        raise RuntimeError(f"Prepare {name} cart on a fresh seed DB first: {status} {result}")

gate = threading.Barrier(2)


def checkout(token):
    gate.wait()
    return call("POST", "/orders", {"recipient_name": "Nguyễn An", "recipient_phone": "0900000002",
                                    "address": "12 Nguyễn Huệ, Quận 1, TP.HCM", "payment_method": "COD"}, token)


with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures = [pool.submit(checkout, token) for token in (a, b)]
    results = [future.result() for future in futures]
codes = sorted(status for status, _body in results)
print("Overlapping checkout HTTP statuses:", codes)
print("Expected exactly one 201 and one 409:", "MET" if codes == [201, 409] else "NOT MET")
print("Read order and variant stock in Postman/MySQL to confirm no duplicate or negative stock.")
