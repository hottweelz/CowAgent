"""Authenticated local IPC transport. No retries, TCP listener or global install."""
import json
import os
from pathlib import Path
import socket
import stat

from .contract import MAX_MESSAGE_BYTES, ProtocolError, authenticate, canonical, envelope


class TransportUnavailable(OSError):
    pass


class RemoteRejected(ProtocolError):
    pass


class ExternalTransport:
    def __init__(self, socket_path, credential, *, timeout=5):
        self.socket_path = Path(socket_path)
        self.credential = credential
        self.timeout = timeout
        if not self.socket_path.is_absolute():
            raise ProtocolError('Socket path must be absolute')

    def _endpoint(self):
        parent = self.socket_path.parent
        directory = parent.stat()
        endpoint = self.socket_path.lstat()
        if (parent.resolve() != parent or directory.st_uid != os.getuid()
                or directory.st_mode & 0o077 or not stat.S_ISDIR(directory.st_mode)
                or endpoint.st_uid != os.getuid() or endpoint.st_mode & 0o077
                or not stat.S_ISSOCK(endpoint.st_mode)):
            raise ProtocolError('Endpoint is not private owned IPC')

    def exchange(self, action, payload):
        request = envelope(self.credential, action, payload)
        raw = canonical(request).encode('utf-8') + b'\n'
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ProtocolError('Request exceeds protocol limit')
        try:
            self._endpoint()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(self.timeout)
                client.connect(str(self.socket_path))
                client.sendall(raw)
                response = bytearray()
                while b'\n' not in response:
                    chunk = client.recv(min(4096, MAX_MESSAGE_BYTES + 1 - len(response)))
                    if not chunk:
                        raise TransportUnavailable('Runtime disconnected before authenticated response')
                    response.extend(chunk)
                    if len(response) > MAX_MESSAGE_BYTES:
                        raise ProtocolError('Response exceeds protocol limit')
                value = json.loads(bytes(response).decode('utf-8'))
        except OSError as exc:
            raise TransportUnavailable('External runtime unavailable') from exc
        data = authenticate(value, self.credential, kind='response',
                            request_id=request['request_id'], action=action)
        if data.get('ok') is not True:
            raise RemoteRejected(str(data.get('error', 'invalid_response')))
        if set(data) != {'ok', 'data'} or not isinstance(data['data'], dict):
            raise ProtocolError('Invalid response payload')
        return data['data']

    def discover(self):
        return self.exchange('discover', {})

    def submit(self, spec, approval=None):
        return self.exchange('submit', {'spec': spec, 'approval': approval})

    def status(self, spec):
        from .contract import digest
        return self.exchange('status', {'task_id': spec['task_id'], 'task_hash': digest(spec)})

    def cancel(self, spec):
        from .contract import digest
        return self.exchange('cancel', {'task_id': spec['task_id'], 'task_hash': digest(spec)})

    def result(self, spec):
        from .contract import digest
        return self.exchange('result', {'task_id': spec['task_id'], 'task_hash': digest(spec)})
