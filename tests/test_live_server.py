import socket
import threading
import time

import httpx
import uvicorn

from backend.api.main import create_app
from tests.conftest import PASSWORD, good_sources


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_real_server_handles_sign_in_and_parallel_requests(settings):
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(settings, good_sources(), dist=settings.db_path.parent / "no-dist"), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    try:
        with httpx.Client(base_url=base, timeout=30) as client:
            assert client.post("/api/auth/setup", json={"email": "admin@example.com", "password": PASSWORD}).status_code == 200
            results = []

            def call(path: str) -> None:
                results.append(client.get(path).status_code)

            workers = [threading.Thread(target=call, args=(p,)) for p in ["/api/status", "/api/auth/me", "/api/users", "/api/audit"] * 5]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()
            assert results and all(code == 200 for code in results), results
            assert client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong-pass-1"}).status_code == 401
            failures = client.get("/api/audit", params={"action": "auth.login_failed"}).json()["total"]
            assert failures == 1
    finally:
        server.should_exit = True
        thread.join(timeout=10)
