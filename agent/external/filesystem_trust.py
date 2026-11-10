"""Reject Darwin mounts that cannot enforce the existing POSIX owner boundary.

Apple's statvfs conversion exports only read-only/nosuid flags. Use the explicit
64-bit statfs ABI, not statvfs, for MNT_IGNORE_OWNERSHIP. No subprocess, mount
change, filesystem write, or cached mount observation is used here.
"""
import ctypes
import os
import sys

from .contract import ProtocolError

# Apple XNU bsd/sys/mount.h: __DARWIN_STRUCT_STATFS64, MNT_IGNORE_OWNERSHIP.
# https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/mount.h
# Apple Libc emulated/statvfs.c: cvt_statfs_to_statvfs masks the other flags.
# https://github.com/apple-oss-distributions/Libc/blob/main/emulated/statvfs.c
MNT_IGNORE_OWNERSHIP = 0x00200000


class _DarwinStatFS64(ctypes.Structure):
    _fields_ = [
        ('f_bsize', ctypes.c_uint32), ('f_iosize', ctypes.c_int32),
        ('f_blocks', ctypes.c_uint64), ('f_bfree', ctypes.c_uint64),
        ('f_bavail', ctypes.c_uint64), ('f_files', ctypes.c_uint64),
        ('f_ffree', ctypes.c_uint64), ('f_fsid', ctypes.c_int32 * 2),
        ('f_owner', ctypes.c_uint32), ('f_type', ctypes.c_uint32),
        ('f_flags', ctypes.c_uint32), ('f_fssubtype', ctypes.c_uint32),
        ('f_fstypename', ctypes.c_char * 16), ('f_mntonname', ctypes.c_char * 1024),
        ('f_mntfromname', ctypes.c_char * 1024), ('f_flags_ext', ctypes.c_uint32),
        ('f_reserved', ctypes.c_uint32 * 7),
    ]


def _darwin_mount_flags(path=None, *, fd=None):
    # Explicit statfs64 symbols avoid the architecture-dependent statfs versus
    # statfs$INODE64 redirection. Unsupported/missing ABI must not imply trust.
    if (ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(_DarwinStatFS64) != 2168
            or _DarwinStatFS64.f_flags.offset != 64 or (path is None) == (fd is None)):
        raise OSError('Filesystem ownership ABI unavailable')
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    function = getattr(library, 'statfs64' if fd is None else 'fstatfs64')
    function.argtypes = [ctypes.c_char_p if fd is None else ctypes.c_int,
                         ctypes.POINTER(_DarwinStatFS64)]
    function.restype = ctypes.c_int
    result = _DarwinStatFS64()
    if function(os.fsencode(path) if fd is None else fd, ctypes.byref(result)) != 0:
        raise OSError(ctypes.get_errno(), 'Filesystem ownership status unavailable')
    return result.f_flags


def require_filesystem_ownership(path=None, *, fd=None):
    """Supplement existing owner/mode/ancestor checks; do not replace them.

    Linux retains its existing checks. Darwin without readable authoritative
    flags fails closed, as does an ownership-ignored mount with mode 0755/0600.
    """
    if sys.platform != 'darwin':
        return
    try:
        flags = _darwin_mount_flags(path, fd=fd)
    except (AttributeError, OSError, TypeError, ValueError):
        raise ProtocolError('Filesystem ownership status unavailable') from None
    if flags & MNT_IGNORE_OWNERSHIP:
        raise ProtocolError('Filesystem ignores ownership')
