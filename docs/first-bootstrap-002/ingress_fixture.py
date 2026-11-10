"""Disposable ingress-gateway fixture; binds only ports 19888 and 19889."""

from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


SERVICE_PORT = 19888
GATEWAY_PORT = 19889
ADMISSION_PATHS = {"/message", "/stream", "/api/scheduler/run"}
closed = threading.Event()
slow_started = threading.Event()
slow_release = threading.Event()


class Service(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/health":
            self.reply(200, b'{"status":"ok"}')
        elif self.path == "/stream":
            self.reply(200, b"event: done\ndata: fixture\n\n")
        else:
            self.reply(404, b"not found")

    def do_POST(self):
        if self.path == "/slow":
            slow_started.set()
            slow_release.wait(3)
        if self.path in ADMISSION_PATHS or self.path == "/slow":
            self.reply(202, b"accepted")
        else:
            self.reply(404, b"not found")

    def reply(self, status, body):
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class Gateway(BaseHTTPRequestHandler):
    def _forward(self, method):
        if closed.is_set() and self.path in ADMISSION_PATHS:
            self.send_response(503)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", "0"))) if method == "POST" else None
        connection = http.client.HTTPConnection("127.0.0.1", SERVICE_PORT, timeout=5)
        connection.request(method, self.path, body=body, headers={"Content-Length": str(len(body or b""))})
        response = connection.getresponse()
        payload = response.read()
        self.send_response(response.status)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        connection.close()

    do_GET = lambda self: self._forward("GET")
    do_POST = lambda self: self._forward("POST")

    def log_message(self, *_args):
        pass


def request(port, method, path):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path, body=b"{}" if method == "POST" else None)
    response = connection.getresponse()
    result = (response.status, response.read())
    connection.close()
    return result


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    service = ThreadingHTTPServer(("127.0.0.1", SERVICE_PORT), Service)
    gateway = ThreadingHTTPServer(("127.0.0.1", GATEWAY_PORT), Gateway)
    workers = [threading.Thread(target=s.serve_forever, daemon=True) for s in (service, gateway)]
    for worker in workers:
        worker.start()
    try:
        # Open state: normal requests pass through the gateway.
        for method, path in (("POST", "/message"), ("GET", "/stream"), ("POST", "/api/scheduler/run")):
            require(request(GATEWAY_PORT, method, path)[0] == (200 if method == "GET" else 202), f"open gateway {path}")

        # An in-flight request starts while open. Closing admission does not cancel it.
        inflight_result = []
        inflight = threading.Thread(target=lambda: inflight_result.append(request(GATEWAY_PORT, "POST", "/slow")))
        inflight.start()
        require(slow_started.wait(2), "in-flight request did not start")
        closed.set()
        slow_release.set()
        inflight.join(3)
        require(inflight_result and inflight_result[0][0] == 202, "in-flight request was not completed")

        # Closed gateway rejects all three ingress families and retains health.
        for method, path in (("POST", "/message"), ("GET", "/stream"), ("POST", "/api/scheduler/run")):
            require(request(GATEWAY_PORT, method, path)[0] == 503, f"closed gateway admitted {path}")
        require(request(GATEWAY_PORT, "GET", "/api/health")[0] == 200, "health observation blocked")

        # The gateway cannot fence the still-reachable direct service listener.
        require(request(SERVICE_PORT, "POST", "/message")[0] == 202, "direct-listener bypass was not demonstrated")
        closed.clear()
        require(request(GATEWAY_PORT, "POST", "/message")[0] == 202, "restored gateway did not admit")
        print(json.dumps({
            "fixture": "pass",
            "ports": {"service": SERVICE_PORT, "gateway": GATEWAY_PORT},
            "gateway_closed_rejects": ["/message", "/stream", "/api/scheduler/run"],
            "health_during_exclusion": "200",
            "inflight_during_close": "completed 202",
            "direct_service_bypass": "accepted 202; gateway is not an enforced legacy boundary",
            "restore": "accepted 202",
            "persistent_config": "none",
        }, sort_keys=True))
    finally:
        slow_release.set()
        for server in (gateway, service):
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
