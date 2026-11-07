"""Restricted text-file broker. No shell, plugins, rich parsers or shared state.

Only trusted host code calls this module. Model arguments never choose a root
grant. POSIX directory descriptors and O_NOFOLLOW keep every opened component
inside a granted directory. This is not a sandbox for arbitrary Python code.
"""

from __future__ import annotations

from contextlib import contextmanager
import fnmatch
import os
from pathlib import Path
import stat
import threading
import time
import unicodedata
import uuid

from agent.tools.base_tool import ToolResult


# Same text/search bounds as the existing native search tool. Rich formats and
# executable state are intentionally outside this restricted broker's contract.
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 50 * 1024
_SOURCE_ROOT = str(Path(__file__).resolve().parents[2])
_PRIVATE_DIRS = frozenset({
    ".cow", ".git", ".ssh", ".aws", ".azure", ".config", "agents",
    "memory", "skills", "knowledge", "plugins", "__pycache__",
    "scheduler", "runs", "subagents", "system", "users", "backups", "logs",
    "output", "tmp", "websites",
})
_PRIVATE_FILES = frozenset({
    ".env", "config.json", "mcp.json", "team.json", "session_prefs.json",
    "sessions.json", "agent.md", "agents.md", "user.md", "rule.md",
    "memory.md", "bootstrap.md", "identity.md", "soul.md",
})
_RICH_SUFFIXES = frozenset({
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx",
})
_LOCKS = tuple(threading.RLock() for _ in range(256))


class FileDenied(Exception):
    """A stable code, never a secret-bearing path or exception message."""


def _inside(path, root):
    return os.path.commonpath((path, root)) == root


def private_inside(path, root):
    """Conservatively match denied paths on case/normalization-insensitive disks.

    This may over-deny a distinct case variant on a case-sensitive volume. It
    must never grant access based on folded paths: root walking remains exact.
    """
    path, root = (unicodedata.normalize("NFD", value).casefold() for value in (path, root))
    return _inside(path, root)


def _cancel(event):
    if event is not None and event.is_set():
        raise FileDenied("cancelled")


def _reserved(parts):
    for part in parts:
        low = part.casefold()
        if (low in _PRIVATE_DIRS or low in _PRIVATE_FILES
                or low.startswith(".env.") or low.endswith((".db-wal", ".db-shm"))
                or Path(low).suffix in _RICH_SUFFIXES):
            return True
    return False


class FileBroker:
    def __init__(self, authority, cwd, cancel_event=None):
        if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
            raise FileDenied("unsupported_filesystem_backend")
        self.authority = authority
        self.cwd = os.path.abspath(cwd)
        self.cancel_event = cancel_event

    def locate(self, path, write=False):
        _cancel(self.cancel_event)
        if not isinstance(path, str) or not path or "\0" in path:
            raise FileDenied("invalid_path")
        if ".." in Path(path).parts:
            raise FileDenied("parent_traversal")
        path = os.path.expanduser(path)
        absolute = os.path.abspath(os.path.join(self.cwd, path))
        roots = self.authority.write_roots if write else self.authority.read_roots
        if write and self.authority.mode == "read-only":
            raise FileDenied("read_only")
        if write and private_inside(absolute, _SOURCE_ROOT):
            raise FileDenied("host_source_protected")
        for denied in self.authority.denied_paths:
            if private_inside(absolute, os.path.abspath(denied)):
                raise FileDenied("private_state")
        for root in sorted(roots, key=len, reverse=True):
            # Authority roots are canonical host-selected grants. Reject a
            # changed root symlink instead of silently changing its target.
            if root != os.path.realpath(root) or not _inside(absolute, root):
                continue
            relative = os.path.relpath(absolute, root)
            parts = () if relative == "." else Path(relative).parts
            if _reserved(parts):
                raise FileDenied("private_or_unsupported_file")
            return root, parts, absolute
        raise FileDenied("outside_grant")

    @contextmanager
    def parent(self, path, *, write=False, create=False):
        root, parts, absolute = self.locate(path, write)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fd = os.open(root, flags)
        try:
            for part in parts[:-1]:
                _cancel(self.cancel_event)
                try:
                    child = os.open(part, flags, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                    child = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = child
            yield fd, parts[-1] if parts else ".", absolute
        finally:
            os.close(fd)

    def read(self, path):
        with self.parent(path) as (parent, name, _):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise FileDenied("nonregular_or_linked_file")
                if info.st_size > MAX_FILE_BYTES:
                    raise FileDenied("text_file_too_large")
                chunks, remaining = [], MAX_FILE_BYTES + 1
                while remaining:
                    _cancel(self.cancel_event)
                    block = os.read(fd, min(65536, remaining))
                    if not block:
                        break
                    chunks.append(block)
                    remaining -= len(block)
                raw = b"".join(chunks)
                if len(raw) > MAX_FILE_BYTES or b"\0" in raw:
                    raise FileDenied("unsupported_text_file")
                return raw.decode("utf-8")
            finally:
                os.close(fd)

    def write(self, path, content):
        if not isinstance(content, str):
            raise FileDenied("invalid_content")
        raw = content.encode("utf-8")
        if len(raw) > MAX_FILE_BYTES or b"\0" in raw:
            raise FileDenied("unsupported_text_file")
        with self.parent(path, write=True, create=True) as (parent, name, _):
            if name == ".":
                raise FileDenied("not_a_file")
            try:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                current = None
            if current and (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1):
                raise FileDenied("nonregular_or_linked_file")
            temporary = ".cow-task-" + uuid.uuid4().hex
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                _cancel(self.cancel_event)
                # Replacing a directory entry never follows a final symlink or
                # mutates a pre-existing hard-linked inode.
                os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
        return len(raw)

    def entries(self, path):
        with self.parent(path) as (parent, name, absolute):
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                entries = []
                for entry in sorted(os.listdir(fd), key=str.casefold):
                    _cancel(self.cancel_event)
                    child = os.path.join(absolute, entry)
                    try:
                        self.locate(child)
                        info = os.stat(entry, dir_fd=fd, follow_symlinks=False)
                    except (FileDenied, OSError):
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        entries.append((entry, True))
                    elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                        entries.append((entry, False))
                return absolute, entries
            finally:
                os.close(fd)


def _search(broker, args):
    # regex is an existing dependency with per-match timeouts. Never pass a
    # model pattern to a subprocess or use unbounded stdlib backtracking.
    import regex

    pattern = args.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise FileDenied("missing_pattern")
    target = args.get("target", "content")
    output_mode = args.get("output_mode", "content")
    if target not in ("content", "files") or output_mode not in ("content", "files", "count"):
        raise FileDenied("unsupported_search_mode")
    matcher = regex.compile(pattern, regex.IGNORECASE if args.get("ignore_case") else 0) if target == "content" else None
    limit = min(500, max(1, int(args.get("max_results", 50))))
    glob = args.get("file_glob", "*") or "*"
    stack = [args.get("path") or "."]
    matches = []
    total_matches = 0
    deadline = time.monotonic() + 30
    while stack and len(matches) < limit:
        _cancel(broker.cancel_event)
        if time.monotonic() > deadline:
            raise FileDenied("search_timeout")
        path = stack.pop()
        try:
            absolute, entries = broker.entries(path)
        except NotADirectoryError:
            absolute = os.path.abspath(os.path.join(broker.cwd, path))
            entries = [(os.path.basename(absolute), False)]
            absolute = os.path.dirname(absolute)
        for name, is_dir in entries:
            _cancel(broker.cancel_event)
            child = os.path.join(absolute, name)
            if is_dir:
                stack.append(child)
                continue
            relative = os.path.relpath(child, broker.cwd)
            if not (fnmatch.fnmatch(name, glob) or fnmatch.fnmatch(relative, glob)):
                continue
            if target == "files":
                needle, candidate = pattern, name
                if args.get("ignore_case"):
                    needle, candidate = needle.casefold(), candidate.casefold()
                if not any(c in needle for c in "*?["):
                    needle = "*" + needle + "*"
                if fnmatch.fnmatchcase(candidate, needle):
                    matches.append(relative)
                    total_matches += 1
                if len(matches) >= limit:
                    break
                continue
            try:
                content = broker.read(child)
            except (FileDenied, OSError, UnicodeError):
                continue
            count = 0
            for number, line in enumerate(content.splitlines(), 1):
                _cancel(broker.cancel_event)
                if time.monotonic() > deadline:
                    raise FileDenied("search_timeout")
                if matcher.search(line, timeout=0.1):
                    total_matches += 1
                    count += 1
                    if output_mode == "files":
                        matches.append(relative)
                        break
                    if output_mode == "content":
                        matches.append(f"{relative}:{number}:{line[:1000]}")
                    if len(matches) >= limit:
                        break
            if output_mode == "count" and count:
                matches.append(f"{relative}:{count}")
            if len(matches) >= limit:
                break
    return {"output": "\n".join(matches)[:MAX_OUTPUT_BYTES], "match_count": total_matches,
            "backend": "restricted-native"}


def execute_file(tool_name, args, authority, cwd, cancel_event=None):
    """Execute an already authorized operation with descriptor-scoped I/O."""
    try:
        broker = FileBroker(authority, cwd, cancel_event)
        path = args.get("path") or "."
        if tool_name in ("write", "edit"):
            # Serialize the whole read/replace cycle for native concurrent edits.
            _, _, absolute = broker.locate(path, write=True)
            with _LOCKS[hash(absolute) % len(_LOCKS)]:
                if tool_name == "write":
                    content = args["content"]
                else:
                    content = broker.read(path)
                    old, new = args["oldText"], args["newText"]
                    if not isinstance(old, str) or not isinstance(new, str):
                        raise FileDenied("invalid_edit")
                    if not old:
                        content += ("\n" if content and not content.endswith("\n") else "") + new
                    elif old not in content or (content.count(old) != 1 and not args.get("replaceAll")):
                        raise FileDenied("edit_not_unique")
                    else:
                        content = content.replace(old, new, -1 if args.get("replaceAll") else 1)
                from agent.tools.utils.syntax_check import review
                blocking, warning = review(absolute, None, content)
                if blocking:
                    raise FileDenied("invalid_structured_text")
                written = broker.write(path, content)
            result = {"message": "File saved through restricted broker", "bytes_written": written}
            if warning:
                result["warning"] = warning
        elif tool_name == "read":
            content = broker.read(path)
            lines = content.splitlines()
            offset = int(args.get("offset", 1))
            start = max(0, offset - 1 if offset > 0 else len(lines) + offset)
            limit = min(2000, max(1, int(args.get("limit", 2000))))
            result = {"output": "\n".join(f"{n + 1}|{line}" for n, line in
                      enumerate(lines[start:start + limit], start))[:MAX_OUTPUT_BYTES]}
        elif tool_name == "ls":
            _, entries = broker.entries(path)
            limit = min(2000, max(1, int(args.get("limit", 500))))
            result = {"output": "\n".join(name + ("/" if directory else "")
                      for name, directory in entries[:limit])[:MAX_OUTPUT_BYTES],
                      "entry_count": min(len(entries), limit)}
        elif tool_name == "search_files":
            result = _search(broker, args)
        else:
            raise FileDenied("unsupported_file_operation")
        return ToolResult.success(result)
    except FileDenied as exc:
        return ToolResult.fail(f"Permission denied: {exc}. Operation did not complete.",
                               ext_data={"permission_denied": True, "code": str(exc)})
    except Exception:
        # Filesystem and parser exceptions can include paths or supplied text.
        # Keep these out of returned errors and diagnostic logs.
        return ToolResult.fail("Restricted filesystem operation failed.",
                               ext_data={"code": "filesystem_error"})
