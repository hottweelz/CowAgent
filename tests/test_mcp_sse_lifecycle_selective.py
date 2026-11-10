"""Legacy SSE lifecycle and credential boundaries."""
import io
import json
import threading
import time
from unittest.mock import patch

import pytest

from agent.tools.mcp import mcp_client as mcp


def client():
    return mcp.McpClient({'name': 'legacy', 'type': 'sse', 'url': 'https://example.test/sse', 'timeout': 1})


def test_endpoint_cannot_redirect_credentials_to_another_origin():
    c = client()
    c._sse_url = c.config['url']
    stream = io.BytesIO(b'data: https://other.test/messages\n')
    with patch.object(mcp, '_sse_urlopen', return_value=stream):
        with pytest.raises(ValueError, match='same origin'):
            c._sse_discover_endpoint()
    assert stream.closed


def test_reader_delivers_response_and_timeout_removes_waiter(monkeypatch):
    c = client()
    c._sse_alive = True
    def post(message, deadline):
        c._sse_deliver(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': {}}))
        return None
    monkeypatch.setattr(c, '_sse_post', post)
    assert c._sse_send({'id': 7, 'method': 'tools/list'})['id'] == 7
    monkeypatch.setattr(c, '_sse_post', lambda message, deadline: None)
    c._timeout = 0.01
    with pytest.raises(TimeoutError):
        c._sse_send({'id': 8, 'method': 'tools/list'})
    assert c._sse_pending == {}


def test_shutdown_during_reconnect_does_not_reactivate(monkeypatch):
    c = client()
    c._initialized = True
    entered, resume = threading.Event(), threading.Event()
    def connect():
        entered.set()
        assert resume.wait(2)
        return False
    monkeypatch.setattr(c, '_sse_connect', connect)
    errors = []
    def reconnect():
        try:
            c._sse_reconnect()
        except Exception as exc:
            errors.append(exc)
    worker = threading.Thread(target=reconnect)
    worker.start()
    assert entered.wait(2)
    c.shutdown()
    resume.set()
    worker.join(2)
    assert not worker.is_alive()
    assert errors and not c._initialized
    with pytest.raises(RuntimeError, match='shut down'):
        c._sse_reconnect()


def test_post_connect_timeout_uses_request_budget(monkeypatch):
    c = client()
    c._post_url = 'https://example.test/messages'
    captured = []
    def open_request(req, timeout, has_headers):
        captured.append(timeout)
        return io.BytesIO(b'{"id":1,"result":{}}')
    monkeypatch.setattr(mcp, '_sse_urlopen', open_request)
    assert c._sse_post({'id': 1}, time.monotonic() + 0.5)['id'] == 1
    assert 0 < captured[0] <= 0.5


def test_real_legacy_stream_headers_fallback_and_reconnect():
    import http.server
    import queue
    from urllib.parse import urlsplit

    sessions, requests = {}, []
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def log_message(self, *args):
            pass
        def do_GET(self):
            requests.append(('GET', self.headers.get('Authorization')))
            sid = str(len(sessions) + 1)
            events = sessions[sid] = queue.Queue()
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            try:
                self.wfile.write(f'event: endpoint\ndata: /messages?sid={sid}\n\n'.encode())
                self.wfile.flush()
                while True:
                    item = events.get(timeout=3)
                    if item is None:
                        break
                    self.wfile.write(b'data: ' + json.dumps(item).encode() + b'\n\n')
                    self.wfile.flush()
            except (OSError, queue.Empty):
                pass
            self.close_connection = True
        def do_POST(self):
            requests.append(('POST', self.headers.get('Authorization')))
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if urlsplit(self.path).path == '/sse':
                self.send_response(405)
            else:
                sid = urlsplit(self.path).query.split('=', 1)[1]
                if 'id' in data:
                    sessions[sid].put({'jsonrpc': '2.0', 'id': data['id'], 'result': {'tools': []}})
                self.send_response(202)
            self.send_header('Content-Length', '0')
            self.end_headers()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    c = mcp.McpClient({'name': 'local', 'type': 'streamable-http',
                       'url': f'http://127.0.0.1:{server.server_port}/sse',
                       'headers': {'Authorization': 'Bearer fixture'}, 'timeout': 2})
    try:
        assert c.initialize(), c.last_error
        assert c.transport == 'sse'
        assert c.list_tools() == []
        sessions['1'].put(None)
        deadline = time.monotonic() + 2
        while c._sse_alive and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not c._sse_alive
        assert c.list_tools() == []
        assert len(sessions) == 2
        assert all(value == 'Bearer fixture' for _, value in requests)
    finally:
        c.shutdown()
        for events in sessions.values():
            events.put(None)
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_authenticated_sse_redirect_is_refused():
    handler = mcp._NoSseRedirect()
    assert handler.redirect_request(None, None, 302, 'redirect', {}, 'https://other.test/') is None


def test_oversized_stream_event_closes_waiter(monkeypatch):
    import queue
    c = client()
    stream = object()
    c._sse_stream = stream
    c._sse_alive = True
    waiter = queue.Queue()
    c._sse_pending[1] = waiter
    monkeypatch.setattr(mcp, '_SSE_RESPONSE_MAX_BYTES', 4)
    c._sse_read_loop(stream, iter([b'data: oversized\n']))
    assert not c._sse_alive
    assert waiter.get_nowait() is mcp._SSE_CLOSED


def test_concurrent_request_waits_for_reconnect_handshake(monkeypatch):
    c = client()
    c._initialized = True
    handshake_started, finish_handshake = threading.Event(), threading.Event()
    calls, errors = [], []
    def connect():
        c._sse_alive = True
        calls.append('initialize started')
        handshake_started.set()
        assert finish_handshake.wait(2)
        calls.append('initialize finished')
        return True
    def post(message, deadline):
        calls.append(message['method'])
        return {'id': message['id'], 'result': {}}
    monkeypatch.setattr(c, '_sse_connect', connect)
    monkeypatch.setattr(c, '_sse_post', post)
    def send(request):
        try:
            c._sse_send(request)
        except Exception as exc:
            errors.append(exc)
    first = threading.Thread(target=send, args=({'id': 1, 'method': 'tools/list'},))
    second = threading.Thread(target=send, args=({'id': 2, 'method': 'tools/call'},))
    first.start()
    assert handshake_started.wait(2)
    second.start()
    second.join(0.1)
    assert second.is_alive()
    assert calls == ['initialize started']
    finish_handshake.set()
    first.join(2)
    second.join(2)
    assert not first.is_alive() and not second.is_alive()
    assert not errors
    assert calls.index('initialize finished') < calls.index('tools/call')
    assert calls.index('initialize finished') < calls.index('tools/list')


def test_http_error_body_is_not_read_and_is_closed(monkeypatch):
    import urllib.error
    c = client()
    c._post_url = 'https://example.test/messages'
    class ErrorBody(io.BytesIO):
        def read(self, *args):
            pytest.fail('HTTP error body must not be read')
    body = ErrorBody(b'server detail')
    error = urllib.error.HTTPError(c._post_url, 503, 'unavailable', {}, body)
    def reject(*args, **kwargs):
        raise error
    monkeypatch.setattr(mcp, '_sse_urlopen', reject)
    with pytest.raises(mcp.McpHttpStatusError, match='HTTP 503'):
        c._sse_post({'id': 1}, time.monotonic() + 0.01)
    assert body.closed
