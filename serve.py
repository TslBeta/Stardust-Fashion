"""Windows-friendly production WSGI server for local test runs."""

import os

from waitress import serve

from app import app


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "5000"))
    print(f"Stardust Fashion: http://{host}:{port}", flush=True)
    serve(app, host=host, port=port, threads=16, connection_limit=200, backlog=200)
