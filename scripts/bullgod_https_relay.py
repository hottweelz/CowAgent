"""Fixed-destination loopback TCP relay for the isolated BullGod instance.

The caller owns the process and must terminate it with the instance. The
loopback listener shares the local user's trust boundary; TLS remains end to end.
"""

import argparse
import ipaddress
import select
import signal
import socket
import sys
import threading
import time

CONNECT_TIMEOUT = 5.0
CONNECTION_DEADLINE = 25.0
BYTE_LIMIT = 2 * 1024 * 1024
MAX_WORKERS = 4
BUFFER_SIZE = 65536


def _public_ip(value):
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a public numeric IP address") from exc
    if not address.is_global or address.is_multicast or address.is_unspecified or address.is_reserved:
        raise argparse.ArgumentTypeError("expected a public numeric IP address")
    # IPv4-mapped IPv6 addresses must not evade IPv4 checks.
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        raise argparse.ArgumentTypeError("expected a public numeric IP address")
    return str(address)


def _port(value):
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a port from 1024 to 65535") from exc
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("expected a port from 1024 to 65535")
    return port


class Relay:
    def __init__(self, listen_port, upstream_ip, *, upstream_port=443,
                 deadline=CONNECTION_DEADLINE, byte_limit=BYTE_LIMIT):
        # upstream_port and limits are injection points for local tests only.
        self.listen_port = listen_port
        self.upstream_ip = upstream_ip
        self.upstream_port = upstream_port
        self.deadline = deadline
        self.byte_limit = byte_limit
        self.stopping = threading.Event()
        self.lock = threading.Lock()
        self.sockets = set()
        self.workers = set()
        self.slots = threading.BoundedSemaphore(MAX_WORKERS)
        self.listener = None

    def start(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(("127.0.0.1", self.listen_port))
            listener.listen(MAX_WORKERS)
            listener.settimeout(0.2)
        except BaseException:
            listener.close()
            raise
        self.listener = listener

    def serve(self):
        while not self.stopping.is_set():
            try:
                client, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            if self.stopping.is_set() or not self.slots.acquire(blocking=False):
                client.close()
                continue
            worker = threading.Thread(target=self._handle, args=(client,), daemon=True)
            with self.lock:
                self.sockets.add(client)
                self.workers.add(worker)
                worker.start()

    def _handle(self, client):
        upstream = None
        try:
            end = time.monotonic() + self.deadline
            family = socket.AF_INET6 if ":" in self.upstream_ip else socket.AF_INET
            upstream = socket.socket(family, socket.SOCK_STREAM)
            with self.lock:
                if self.stopping.is_set():
                    return
                self.sockets.add(upstream)
            upstream.settimeout(min(CONNECT_TIMEOUT, max(0.001, end - time.monotonic())))
            upstream.connect((self.upstream_ip, self.upstream_port))
            client.setblocking(False)
            upstream.setblocking(False)
            self._transfer(client, upstream, end)
        except (OSError, ValueError):
            pass
        finally:
            for sock in (client, upstream):
                if sock is not None:
                    with self.lock:
                        self.sockets.discard(sock)
                    sock.close()
            with self.lock:
                self.workers.discard(threading.current_thread())
            self.slots.release()

    def _transfer(self, client, upstream, end):
        peers = {client: upstream, upstream: client}
        pending = {client: bytearray(), upstream: bytearray()}
        received = {client: 0, upstream: 0}
        reading = {client, upstream}
        shutdown_sent = set()
        while not self.stopping.is_set() and time.monotonic() < end:
            for source, target in peers.items():
                if source not in reading and not pending[target] and target not in shutdown_sent:
                    try:
                        target.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass
                    shutdown_sent.add(target)
            if not reading and not any(pending.values()):
                return
            readers = [sock for sock in reading if len(pending[peers[sock]]) < BUFFER_SIZE]
            writers = [sock for sock in peers if pending[sock]]
            ready_read, ready_write, _ = select.select(readers, writers, [], min(0.2, max(0, end - time.monotonic())))
            for sock in ready_read:
                chunk = sock.recv(min(BUFFER_SIZE - len(pending[peers[sock]]),
                                      self.byte_limit - received[sock] + 1))
                if not chunk:
                    reading.discard(sock)
                else:
                    received[sock] += len(chunk)
                    if received[sock] > self.byte_limit:
                        return
                    pending[peers[sock]].extend(chunk)
            for sock in ready_write:
                sent = sock.send(pending[sock])
                del pending[sock][:sent]

    def stop(self):
        self.stopping.set()
        if self.listener:
            self.listener.close()
        with self.lock:
            sockets = list(self.sockets)
            workers = list(self.workers)
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        for worker in workers:
            worker.join(CONNECT_TIMEOUT + 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fixed-destination loopback HTTPS relay")
    parser.add_argument("--listen-port", required=True, type=_port)
    parser.add_argument("--upstream-ip", required=True, type=_public_ip)
    args = parser.parse_args(argv)
    relay = Relay(args.listen_port, args.upstream_ip)
    signal.signal(signal.SIGTERM, lambda *_: relay.stopping.set())
    signal.signal(signal.SIGINT, lambda *_: relay.stopping.set())
    try:
        relay.start()
        print("relay ready", flush=True)
        relay.serve()
    except OSError:
        print("relay failed", file=sys.stderr, flush=True)
        return 1
    finally:
        relay.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
