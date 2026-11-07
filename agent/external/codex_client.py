"""Owned, bounded Codex app-server stdio transport for trusted host code.

The caller owns argv, cwd, environment and higher-level policy. No RPC is retried.
"""
import io
import json
import os
import queue
import select
import signal
import subprocess
import threading
import time

MAX_FRAME = 1024 * 1024
ALLOWED_METHODS = frozenset({
    "initialize", "permissionProfile/list", "experimentalFeature/list", "config/read",
    "mcpServerStatus/list", "hooks/list", "thread/start", "turn/start",
    "turn/interrupt", "thread/read", "thread/turns/list", "thread/items/list",
})


class ClientError(Exception):
    """Base class for transport failures."""


class RequestTimeout(ClientError):
    pass


class ServerEOF(ClientError):
    pass


class ProtocolFailure(ClientError):
    pass


class RemoteError(ClientError):
    def __init__(self, error):
        super().__init__("app-server returned an RPC error")
        self.error = error


class CodexClient:
    """One process and one reader; request calls may run on separate threads."""

    def __init__(self, argv, cwd, env):
        self._process = subprocess.Popen(
            argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, start_new_session=True, bufsize=0,
        )
        self._process.stdout = io.BufferedReader(self._process.stdout)
        os.set_blocking(self._process.stdin.fileno(), False)
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._closed = False
        self._pending = {}
        self._next_id = 0
        self._failure = None
        self.events = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    @property
    def pid(self):
        return self._process.pid

    @property
    def returncode(self):
        return self._process.poll()

    def is_alive(self):
        return self._process.poll() is None

    def _send(self, message, deadline):
        try:
            raw = json.dumps(message, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as exc:
            raise ProtocolFailure("invalid outgoing JSON") from exc
        if len(raw) > MAX_FRAME:
            raise ProtocolFailure("outgoing frame exceeds limit")
        if not self._write_lock.acquire(timeout=max(0, deadline - time.monotonic())):
            raise RequestTimeout("app-server write timed out")
        sent = 0
        try:
            fd = self._process.stdin.fileno()
            while sent < len(raw):
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
                    raise RequestTimeout("app-server write timed out")
                try:
                    sent += os.write(fd, raw[sent:])
                except BlockingIOError:
                    continue
        except RequestTimeout as exc:
            if sent:
                self._fail(ProtocolFailure("partial app-server frame"))
            raise exc
        except (BrokenPipeError, OSError, ValueError) as exc:
            raise ServerEOF("app-server stdin closed") from exc
        finally:
            self._write_lock.release()

    def request(self, method, params, timeout):
        if method not in ALLOWED_METHODS:
            raise ValueError("RPC method is not allowed")
        if timeout is None or timeout <= 0:
            raise ValueError("request timeout must be positive")
        deadline = time.monotonic() + timeout
        response = queue.Queue(maxsize=1)
        with self._lock:
            if self._failure:
                raise self._failure
            self._next_id += 1
            request_id = self._next_id
            self._pending[request_id] = response
        try:
            self._send({"method": method, "id": request_id, "params": params}, deadline)
            try:
                item = response.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise RequestTimeout("app-server request timed out") from exc
            if isinstance(item, Exception):
                raise item
            if "error" in item:
                raise RemoteError(item["error"])
            if method == "initialize":
                self._send({"method": "initialized"}, deadline)
            return item["result"]
        finally:
            with self._lock:
                self._pending.pop(request_id, None)

    def next_event(self, timeout=None):
        return self.events.get(timeout=timeout)

    def _fail(self, error):
        with self._lock:
            if self._failure is not None:
                return
            self._failure = error
            pending = list(self._pending.values())
        for waiter in pending:
            try:
                waiter.put_nowait(error)
            except queue.Full:
                pass
        self.events.put({"type": "transport_error", "error": error})

    def _read_loop(self):
        try:
            while True:
                raw = self._process.stdout.readline(MAX_FRAME + 1)
                if not raw:
                    raise ServerEOF("app-server stdout closed")
                if len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
                    raise ProtocolFailure("invalid or oversized app-server frame")
                try:
                    msg = json.loads(raw.decode("utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                except (UnicodeDecodeError, ValueError) as exc:
                    raise ProtocolFailure("invalid app-server JSON") from exc
                if not isinstance(msg, dict):
                    raise ProtocolFailure("app-server frame must be an object")
                if "method" in msg:
                    if not isinstance(msg["method"], str):
                        raise ProtocolFailure("invalid app-server method")
                    if "id" in msg:
                        self._deny(msg)
                    else:
                        self.events.put(msg)
                elif "id" in msg and (("result" in msg) != ("error" in msg)):
                    rid = msg["id"]
                    if not isinstance(rid, int) or isinstance(rid, bool):
                        raise ProtocolFailure("invalid response id")
                    with self._lock:
                        waiter = self._pending.get(rid)
                        if waiter is not None:
                            try:
                                waiter.put_nowait(msg)
                            except queue.Full:
                                raise ProtocolFailure("duplicate response")
                    # Late responses after timeouts are deliberately ignored.
                else:
                    raise ProtocolFailure("invalid app-server message")
        except ClientError as exc:
            self._fail(exc)
        except (OSError, ValueError):
            self._fail(ServerEOF("app-server stream closed"))

    def _deny(self, msg):
        method, request_id = msg["method"], msg["id"]
        if not isinstance(request_id, (int, str)) or isinstance(request_id, bool):
            raise ProtocolFailure("invalid server request id")
        if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
            response = {"id": request_id, "result": {"decision": "decline"}}
        elif method == "item/permissions/requestApproval":
            response = {"id": request_id, "result": {"permissions": {}, "scope": "turn"}}
        else:
            response = {"id": request_id, "error": {"code": -32601, "message": "Method not supported"}}
        self._send(response, time.monotonic() + 1.0)
        self.events.put({"type": "server_request_denied", "method": method, "id": request_id})

    def close(self, grace=1.0):
        """Close stdin and clean up the owned process group within bounded waits.

        Descendants that leave the group are outside this cleanup guarantee.
        """
        if grace <= 0:
            raise ValueError("grace must be positive")
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
            try:
                self._process.stdin.close()
            except (OSError, ValueError):
                pass
            try:
                self._process.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                pass
            # The leader can exit while a same-group child still holds stdout.
            try:
                os.killpg(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + grace
            group_exists = True
            while time.monotonic() < deadline:
                try:
                    os.killpg(self.pid, 0)
                except ProcessLookupError:
                    group_exists = False
                    break
                time.sleep(min(.01, max(0, deadline - time.monotonic())))
            if group_exists:
                try:
                    os.killpg(self.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                self._process.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                pass
            self._reader.join(timeout=grace)
            if not self._reader.is_alive():
                self._process.stdout.close()
            self._fail(ServerEOF("app-server closed"))
