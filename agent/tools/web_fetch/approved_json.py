"""Host-created, exact-endpoint HTTPS JSON reads through the native gateway.

This module is deliberately absent from the model tool registry. Trusted owner
services construct the tool and a short-lived context after checking their
durable read grant. Remote JSON is data; it never grants another tool action.
"""
from dataclasses import dataclass
from email.utils import format_datetime, parsedate_to_datetime
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import threading
import time
from types import MappingProxyType
from urllib.parse import urljoin, urlsplit
import zlib

import certifi

from agent.tools.base_tool import BaseTool, ToolResult


MAX_BODY = 512 * 1024
TOTAL_SECONDS = 20.0
CONNECT_SECONDS = 5.0
READ_SECONDS = 5.0
MAX_REDIRECTS = 2
USER_AGENT = 'CowAgent/1.0 (approved JSON reader)'
_REDIRECTS = frozenset({301, 302, 303, 307, 308})
_HOST = re.compile(r'(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z')
_ETAG = re.compile(r'(?:W/)?"[\x21\x23-\x7e]*"\Z')


class ReadError(ValueError):
    """Stable public error code; never carries URL, headers or response text."""


def _endpoint(url):
    if not isinstance(url, str) or len(url) > 2048 or not url.isascii():
        raise ReadError('invalid_endpoint')
    if any(ord(c) <= 32 or ord(c) == 127 for c in url) or '\\' in url:
        raise ReadError('invalid_endpoint')
    try:
        part = urlsplit(url)
        host = part.hostname
        if (part.scheme != 'https' or not host or not _HOST.fullmatch(host)
                or '.' not in host or any(not x or len(x) > 63 or x.startswith('-')
                                         or x.endswith('-') for x in host.split('.'))
                or part.username is not None or part.password is not None
                or part.port not in (None, 443) or part.query or part.fragment
                or not part.path.startswith('/')):
            raise ReadError('invalid_endpoint')
        # Reject alternate spellings, empty query/fragment markers and URL parser
        # normalization. Exact configured strings are the endpoint identities.
        netloc = host + (':443' if part.port is not None else '')
        if url != 'https://' + netloc + part.path:
            raise ReadError('invalid_endpoint')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ReadError('invalid_endpoint')
        return host, part.path
    except (ValueError, UnicodeError):
        raise ReadError('invalid_endpoint') from None


def _public_ip(value):
    try:
        addr = ipaddress.ip_address(value)
        if (not isinstance(value, str) or not addr.is_global or addr.is_multicast
                or addr.is_unspecified or addr.is_reserved
                or getattr(addr, 'ipv4_mapped', None) is not None):
            raise ValueError()
        return str(addr)
    except (TypeError, ValueError):
        raise ReadError('invalid_public_address') from None


def _safe_header(value, limit=1024):
    return (value if isinstance(value, str) and len(value) <= limit
            and all(32 <= ord(c) < 127 for c in value) else None)


def _date(value):
    if _safe_header(value, 64) is None:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return value if parsed.tzinfo is not None and format_datetime(parsed, usegmt=True) == value else None
    except (ValueError, TypeError, OverflowError):
        return None


def _etag(value):
    return value if _safe_header(value) is not None and _ETAG.fullmatch(value) else None


def _metadata(response):
    retry = response.getheader('Retry-After')
    retry = (retry if _safe_header(retry, 64) is not None and retry.isascii()
             and retry.isdigit() and len(retry) <= 10 else _date(retry))
    return {'etag': _etag(response.getheader('ETag')),
            'last_modified': _date(response.getheader('Last-Modified')),
            'cache_control': _safe_header(response.getheader('Cache-Control')),
            'retry_after': retry}


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ReadError('deadline_exceeded')
    return remaining


class _PinnedHTTPSConnection(http.client.HTTPConnection):
    """Numeric connect only; hostname remains the TLS/HTTP identity."""

    def __init__(self, host, address, deadline, relay_port=None):
        super().__init__(host, 443, timeout=min(CONNECT_SECONDS, _remaining(deadline)))
        self.address = address
        self.deadline = deadline
        self.relay_port = relay_port
        self.transport_socket = None

    def connect(self):
        addr = ipaddress.ip_address(self.address)
        raw = socket.socket(socket.AF_INET6 if addr.version == 6 and self.relay_port is None else socket.AF_INET,
                            socket.SOCK_STREAM)
        self.sock = raw
        self.transport_socket = raw
        try:
            raw.settimeout(min(CONNECT_SECONDS, _remaining(self.deadline)))
            # A host-owned relay forwards only to this endpoint's public pin.
            # It is a byte pipe, without CONNECT, URL selection or TLS removal.
            destination = ((self.address, 443) if self.relay_port is None
                           else ('127.0.0.1', self.relay_port))
            raw.connect(destination)  # no DNS lookup or proxy/environment use
            raw.settimeout(min(CONNECT_SECONDS, _remaining(self.deadline)))
            self.sock = ssl.create_default_context(cafile=certifi.where()).wrap_socket(
                raw, server_hostname=self.host)
            self.transport_socket = self.sock
            self.sock.settimeout(min(READ_SECONDS, _remaining(self.deadline)))
        except BaseException:
            raw.close()
            raise

    def abort(self):
        # shutdown wakes a blocked header/body read even when a peer sends a slow
        # trickle that would keep resetting the ordinary socket read timeout.
        sock = self.transport_socket
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def _read_body(response, connection, deadline):
    encoding = (response.getheader('Content-Encoding') or 'identity').strip().lower()
    if encoding not in ('identity', 'gzip', 'deflate'):
        raise ReadError('unsupported_encoding')
    decoder = (zlib.decompressobj(16 + zlib.MAX_WBITS if encoding == 'gzip' else zlib.MAX_WBITS)
               if encoding != 'identity' else None)
    body = bytearray()
    wire_size = 0
    # A Connection: close response can release the last socket reference when
    # read1 consumes Content-Length. Do not touch that closed fd on the next pass.
    while response.length != 0:
        connection.transport_socket.settimeout(min(READ_SECONDS, _remaining(deadline)))
        # read1 returns available data rather than waiting to fill the chunk.
        chunk = response.read1(16 * 1024)
        _remaining(deadline)
        if not chunk:
            break
        wire_size += len(chunk)
        if wire_size > MAX_BODY:
            raise ReadError('body_too_large')
        decoded = decoder.decompress(chunk, MAX_BODY - len(body) + 1) if decoder else chunk
        body.extend(decoded)
        if len(body) > MAX_BODY or (decoder and decoder.unconsumed_tail):
            raise ReadError('body_too_large')
    if decoder and (not decoder.eof or decoder.unused_data):
        raise ReadError('invalid_encoding')
    if response.length is not None and response.length != 0:
        raise ReadError('incomplete_body')
    return bytes(body)


@dataclass(frozen=True, eq=False)
class _HostReadContext:
    tool: object
    profile: object
    endpoints: object
    relays: object
    read_grant: bool

    @property
    def _current_agent_id(self):
        return self.profile.id

    @property
    def workspace_dir(self):
        return self.profile.workspace

    def effective_permission_mode(self):
        return 'read-only'

    def effective_cwd(self):
        return self.profile.workspace

    def protected_paths(self):
        return ()


def create_read_context(tool, profile, *, read_grant):
    """Called by the owner host only after validating a current standing grant.

    Do not attach this context/tool to a model, guest, delegated worker or an
    unrelated commitment. The caller must recheck pause/cancel before invoking.
    """
    from agent.registry import AgentProfile
    if (type(tool) is not ApprovedJsonRead or type(profile) is not AgentProfile
            or profile.enabled is not True or read_grant is not True
            or not os.path.isabs(profile.workspace)):
        raise ReadError('invalid_read_grant')
    context = _HostReadContext(tool, profile, tool.endpoints, tool.relays, True)
    tool._contexts.add(context)
    return context


def has_host_read_grant(tool, arguments, context):
    """Exact native binding, called after ordinary authority resolution."""
    from agent.permission.authority import _registry_profiles
    if (type(tool) is not ApprovedJsonRead or type(context) is not _HostReadContext
            or context not in tool._contexts or context.tool is not tool
            or context.endpoints is not tool.endpoints or context.read_grant is not True
            or context.relays is not tool.relays
            or context.effective_permission_mode() != 'read-only'
            or not any(profile == context.profile and profile.enabled is True
                       for profile in _registry_profiles())):
        return False
    tool._arguments(arguments)
    return True


class ApprovedJsonRead(BaseTool):
    name = 'approved_json_read'
    description = 'Read JSON data from an exact owner-approved public HTTPS endpoint.'
    params = {'type': 'object', 'additionalProperties': False,
              'properties': {'url': {'type': 'string'}, 'etag': {'type': 'string'},
                             'last_modified': {'type': 'string'}}, 'required': ['url']}

    def __init__(self, endpoints, relays=None):
        import weakref
        if not isinstance(endpoints, dict) or not endpoints:
            raise ReadError('invalid_endpoint_policy')
        policy = {}
        for url, addresses in endpoints.items():
            _endpoint(url)
            if not isinstance(addresses, (list, tuple)) or not addresses:
                raise ReadError('invalid_public_address')
            policy[url] = tuple(dict.fromkeys(_public_ip(addr) for addr in addresses))
        self._endpoints = MappingProxyType(policy)
        if relays is None:
            relays = {}
        if (not isinstance(relays, dict) or set(relays) - set(policy)
                or any(type(port) is not int or not 1024 <= port <= 65535 or port == 9899
                       for port in relays.values())):
            raise ReadError('invalid_relay_policy')
        self._relays = MappingProxyType(dict(relays))
        self._contexts = weakref.WeakSet()

    @property
    def endpoints(self):
        return self._endpoints

    @property
    def relays(self):
        return self._relays

    def _arguments(self, args):
        if (not isinstance(args, dict) or set(args) - {'url', 'etag', 'last_modified'}
                or args.get('url') not in self.endpoints):
            raise ReadError('endpoint_not_approved')
        _endpoint(args['url'])
        for key, validator in (('etag', _etag), ('last_modified', _date)):
            if key in args and validator(args[key]) is None:
                raise ReadError('invalid_cache_validator')
        return args

    def execute(self, params):
        # Raw execute follows the same convention as all native tools: host code
        # must enter via permission.invoke/execute_tool, never execute directly.
        try:
            args = self._arguments(params)
            return self._fetch(args)
        except ReadError as error:
            return ToolResult.fail('Approved JSON read failed: ' + str(error) + '.',
                                   ext_data={'code': str(error)})
        except (TimeoutError, socket.timeout):
            return ToolResult.fail('Approved JSON read failed: timeout.', ext_data={'code': 'timeout'})
        except Exception:
            return ToolResult.fail('Approved JSON read failed: network_or_json_error.',
                                   ext_data={'code': 'network_or_json_error'})

    def _fetch(self, args):
        deadline = time.monotonic() + TOTAL_SECONDS
        url = args['url']
        headers = {'Accept': 'application/json', 'User-Agent': USER_AGENT,
                   'Accept-Encoding': 'identity'}
        if 'etag' in args:
            headers['If-None-Match'] = args['etag']
        if 'last_modified' in args:
            headers['If-Modified-Since'] = args['last_modified']
        for redirect in range(MAX_REDIRECTS + 1):
            host, path = _endpoint(url)
            relay_port = self.relays.get(url)
            connection = (_PinnedHTTPSConnection(host, self.endpoints[url][0], deadline)
                          if relay_port is None else
                          _PinnedHTTPSConnection(host, self.endpoints[url][0], deadline,
                                                 relay_port=relay_port))
            timer = threading.Timer(_remaining(deadline), connection.abort)
            timer.daemon = True
            timer.start()
            response = None
            try:
                connection.request('GET', path, headers={**headers, 'Host': host})
                response = connection.getresponse()
                _remaining(deadline)
                metadata = _metadata(response)
                if response.status in _REDIRECTS:
                    if redirect == MAX_REDIRECTS:
                        raise ReadError('too_many_redirects')
                    location = response.getheader('Location')
                    if _safe_header(location, 2048) is None:
                        raise ReadError('redirect_not_approved')
                    destination = urljoin(url, location)
                    _endpoint(destination)
                    if destination not in self.endpoints:
                        raise ReadError('redirect_not_approved')
                    # Validators describe the original representation, not a
                    # different approved endpoint reached through a redirect.
                    if destination != url:
                        headers.pop('If-None-Match', None)
                        headers.pop('If-Modified-Since', None)
                    url = destination
                    continue
                if response.status == 304:
                    return ToolResult.success({'status': 'not_modified', 'data': None,
                                               'http_status': 304, **metadata})
                if response.status == 429:
                    return ToolResult.fail('Approved JSON read failed: rate_limited.',
                                           ext_data={'code': 'rate_limited', 'http_status': 429,
                                                     **metadata})
                if response.status != 200:
                    return ToolResult.fail('Approved JSON read failed: http_error.',
                                           ext_data={'code': 'http_error', 'http_status': response.status})
                media = (response.getheader('Content-Type') or '').split(';', 1)[0].strip().lower()
                if media != 'application/json' and not (media.startswith('application/') and media.endswith('+json')):
                    raise ReadError('invalid_content_type')
                body = _read_body(response, connection, deadline)
                if not body.strip():
                    raise ReadError('empty_body')
                try:
                    data = json.loads(body.decode('utf-8-sig'),
                                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                except (ValueError, UnicodeError, RecursionError):
                    raise ReadError('invalid_json') from None
                _remaining(deadline)
                return ToolResult.success({'status': 'ok', 'data': data, 'http_status': 200, **metadata})
            finally:
                timer.cancel()
                if response is not None:
                    response.close()
                connection.close()
