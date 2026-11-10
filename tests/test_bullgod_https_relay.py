import argparse
import socket
import threading

import pytest

from scripts.bullgod_https_relay import Relay, _port, _public_ip


def _fixture_server():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    sock.settimeout(2)
    return sock


def _start_relay(server, **kwargs):
    relay = Relay(0, "127.0.0.1", upstream_port=server.getsockname()[1], **kwargs)
    relay.start()
    thread = threading.Thread(target=relay.serve)
    thread.start()
    return relay, thread


def _stop(relay, thread):
    relay.stop()
    thread.join(2)
    assert not thread.is_alive()
    assert not relay.workers
    assert not relay.sockets


def test_fixed_destination_relays_both_directions_and_half_close():
    server = _fixture_server()
    relay, thread = _start_relay(server)
    client = socket.create_connection(relay.listener.getsockname(), timeout=2)
    upstream, _ = server.accept()
    upstream.settimeout(2)
    try:
        # Even a proxy-like request is opaque bytes to the fixed server.
        request = b"CONNECT elsewhere:443 HTTP/1.1\r\n\r\n"
        client.sendall(request)
        client.shutdown(socket.SHUT_WR)
        assert upstream.recv(4096) == request
        assert upstream.recv(1) == b""
        upstream.sendall(b"opaque reply")
        upstream.shutdown(socket.SHUT_WR)
        assert client.recv(4096) == b"opaque reply"
        assert client.recv(1) == b""
    finally:
        client.close()
        upstream.close()
        server.close()
        _stop(relay, thread)


def test_byte_limit_and_shutdown_close_connections():
    server = _fixture_server()
    relay, thread = _start_relay(server, byte_limit=8)
    client = socket.create_connection(relay.listener.getsockname(), timeout=2)
    upstream, _ = server.accept()
    client.settimeout(2)
    upstream.settimeout(2)
    try:
        client.sendall(b"123456789")
        assert upstream.recv(20) == b""
        assert client.recv(1) == b""
    finally:
        client.close()
        upstream.close()
        server.close()
        _stop(relay, thread)


def test_deadline_and_stop_close_idle_connections():
    server = _fixture_server()
    relay, thread = _start_relay(server, deadline=0.2)
    client = socket.create_connection(relay.listener.getsockname(), timeout=2)
    upstream, _ = server.accept()
    client.settimeout(2)
    try:
        assert client.recv(1) == b""
        client2 = socket.create_connection(relay.listener.getsockname(), timeout=2)
        upstream2, _ = server.accept()
        client2.settimeout(2)
        _stop(relay, thread)
        assert client2.recv(1) == b""
        client2.close()
        upstream2.close()
    finally:
        client.close()
        upstream.close()
        server.close()
        if thread.is_alive():
            _stop(relay, thread)


def test_cli_types_require_public_numeric_ip_and_unprivileged_port():
    assert _public_ip("8.8.8.8") == "8.8.8.8"
    assert _port("1024") == 1024
    for address in ("localhost", "127.0.0.1", "10.0.0.1", "224.0.0.1", "::ffff:8.8.8.8"):
        with pytest.raises(argparse.ArgumentTypeError):
            _public_ip(address)
    for port in ("0", "1023", "65536", "bad"):
        with pytest.raises(argparse.ArgumentTypeError):
            _port(port)


def test_cli_sigterm_stops_listener():
    import subprocess
    import sys
    from pathlib import Path

    probe = _fixture_server()
    port = probe.getsockname()[1]
    probe.close()
    script = Path(__file__).resolve().parents[1] / "scripts" / "bullgod_https_relay.py"
    proc = subprocess.Popen(
        [sys.executable, str(script), "--listen-port", str(port), "--upstream-ip", "8.8.8.8"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        assert proc.stdout.readline().strip() == "relay ready"
        proc.terminate()
        _, stderr = proc.communicate(timeout=3)
        assert proc.returncode == 0
        assert stderr == ""
        with socket.socket() as check:
            check.bind(("127.0.0.1", port))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
