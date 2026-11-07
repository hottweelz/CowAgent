"""Run the retained regression selection with private state and fixture-only HTTP."""


def main():
    import contextlib
    import http.server
    import json
    import os
    from pathlib import Path
    import socket
    import sys
    import tempfile


    REPO = Path(__file__).resolve().parents[2]
    os.chdir(REPO)
    sys.path.insert(0, str(REPO))
    root = Path(tempfile.mkdtemp(prefix="cowagent-verification-regression-")).resolve()
    keep = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL", "TMPDIR"}}
    os.environ.clear()
    os.environ.update(keep)
    os.environ["HOME"] = str(root / "home")
    os.environ["COW_DATA_DIR"] = str(root / "data")
    (root / "home").mkdir()

    import config
    config.config = config.Config({
        "agent_workspace": str(root / "state"), "agent_permission_mode": "workspace-write",
        "self_evolution_enabled": False, "knowledge": False, "cow_lang": "en",
    })

    # Permit only HTTP fixture servers bound by this test process. Active local
    # CowAgent services and all external endpoints remain unreachable by tests.
    ports = set()
    original_bind = http.server.HTTPServer.server_bind
    original_close = http.server.HTTPServer.server_close
    original_connect = socket.socket.connect


    def fixture_bind(server):
        original_bind(server)
        if server.server_address[0] == "127.0.0.1":
            ports.add(server.server_address[1])


    def fixture_close(server):
        ports.discard(server.server_address[1])
        original_close(server)


    def fixture_connect(sock, address):
        if not isinstance(address, tuple) or address[0] != "127.0.0.1" or address[1] not in ports:
            raise RuntimeError("Network access outside owned HTTP fixture denied")
        return original_connect(sock, address)


    http.server.HTTPServer.server_bind = fixture_bind
    http.server.HTTPServer.server_close = fixture_close
    socket.socket.connect = fixture_connect

    files = json.loads((REPO / "docs/efficiency-001/release-verification.json").read_text())["python_test_files"]
    files += json.loads((REPO / "docs/orchestration-001/tests.json").read_text())["test_files"]
    files += ["tests/test_isolation_authorization.py", "tests/test_isolation_delegation.py",
              "tests/test_isolation_filesystem.py"]
    files += sorted(str(p.relative_to(REPO)) for p in (REPO / "tests").glob("test_recovery_*.py"))
    files += sorted(str(p.relative_to(REPO)) for p in (REPO / "tests").glob("test_verification_*.py"))
    files = list(dict.fromkeys(files))
    (root / "selection.json").write_text(json.dumps(files, indent=2))
    print("Evidence:", root, flush=True)
    import pytest
    with (root / "pytest.txt").open("w") as output:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = pytest.main(["-q", "--tb=short", "--junitxml=" + str(root / "junit.xml"), *files])
    print((root / "pytest.txt").read_text()[-18000:])
    raise SystemExit(result)


if __name__ == "__main__":
    main()
