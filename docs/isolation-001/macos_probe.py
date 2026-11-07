"""Bounded Seatbelt feasibility probe. Only fictional files, no network.

This prototype is deliberately NOT a production execution backend. Its broad
read grant demonstrates why a write-only sandbox does not isolate credentials.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def main():
    if sys.platform != "darwin":
        raise SystemExit("macOS required")
    root = Path(tempfile.mkdtemp(prefix="cowagent-seatbelt-")).resolve()
    task = root / "task"; task.mkdir()
    sibling = root / "sibling"; sibling.mkdir()
    (sibling / "secret.txt").write_text("FICTIONAL_ONLY")
    environment = {"PATH": "/usr/bin:/bin", "HOME": str(task), "TMPDIR": str(task)}
    broad = ('(version 1)(deny default)(allow process*)(allow sysctl-read)'
             '(allow file-read*)(allow file-write* (subpath ' + json.dumps(str(task)) + ')'
             ' (literal "/dev/null"))')
    narrow = ('(version 1)(deny default)(allow process-fork)(allow process-exec)'
              '(allow sysctl-read)(allow file-read-metadata)(allow file-read*'
              ' (subpath "/System") (subpath "/usr/lib") (subpath "/bin")'
              ' (subpath "/usr/bin") (literal "/dev/null") (literal "/dev/urandom")'
              ' (subpath ' + json.dumps(str(task)) + '))'
              '(allow file-write* (subpath ' + json.dumps(str(task)) + ')(literal "/dev/null"))')
    def run(profile, code):
        result = subprocess.run(["/usr/bin/sandbox-exec", "-p", profile,
                                 sys.executable, "-I", "-c", code],
                                env=environment, cwd=task, capture_output=True, text=True, timeout=5)
        return {"code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    results = {"platform": sys.platform, "root": str(root)}
    results["narrow_runtime"] = run(narrow, "print('runtime started')")
    results["broad_allowed_write"] = run(broad, "open('allowed.txt','w').write('ok')")
    results["broad_outside_write"] = run(broad, f"open({str(sibling / 'outside.txt')!r},'w').write('no')")
    results["broad_sibling_read"] = run(broad, f"print(open({str(sibling / 'secret.txt')!r}).read())")
    results["allowed_written"] = (task / "allowed.txt").exists()
    results["outside_written"] = (sibling / "outside.txt").exists()

    # Current Bash cleanup kills a process group. A detached descendant can
    # leave that group. Keep its PID and kill that exact fixture in finally.
    child_code = "import time; time.sleep(8)"
    parent_code = ("import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-I','-c',"
                   + repr(child_code) + "],start_new_session=True); "
                   "open('child.pid','w').write(str(p.pid)); time.sleep(8)")
    process = subprocess.Popen(["/usr/bin/sandbox-exec", "-p", broad,
                                sys.executable, "-I", "-c", parent_code],
                               env=environment, cwd=task, start_new_session=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    child_pid = None
    try:
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline and not (task / "child.pid").exists() and process.poll() is None:
            time.sleep(.02)
        if (task / "child.pid").exists():
            child_pid = int((task / "child.pid").read_text())
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
            os.kill(child_pid, 0)
            results["detached_child_survived_group_cleanup"] = True
        else:
            results["detached_child_survived_group_cleanup"] = None
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        results["fixture_cleanup_requested"] = True
    (root / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
