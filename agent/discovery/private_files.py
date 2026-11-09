"""Existing guarded file reader, without runtime/config/logging imports.

Both runtime discovery and cold launch authentication use this one guard.
Importing it must not create a data directory or initialize file logging.
"""
import os
from pathlib import Path
import stat

from agent.external import contract
from agent.external.filesystem_trust import require_filesystem_ownership
from .contracts import DiscoveryError


def _owned_bytes(path, *, private=False):
    """Read an existing regular file without following replaceable symlinks."""
    path = Path(path)
    uid = os.getuid()
    if os.geteuid() != uid or not path.is_absolute() or path.resolve(strict=True) != path:
        raise DiscoveryError('untrusted_record_path')
    for parent in path.parents:
        require_filesystem_ownership(parent)
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, uid)
                or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
            raise DiscoveryError('untrusted_record_path')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require_filesystem_ownership(fd=fd)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1
                or info.st_mode & (0o077 if private else 0o022)
                or info.st_size > contract.MAX_MESSAGE_BYTES):
            raise DiscoveryError('untrusted_record_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(contract.MAX_MESSAGE_BYTES + 1)
        if len(data) > contract.MAX_MESSAGE_BYTES:
            raise DiscoveryError('untrusted_record_file')
        return data
    finally:
        os.close(fd)
