import os
import queue
import signal
import sys
import threading

import pytest

from agent.external.codex_client import (
    CodexClient, ProtocolFailure, RequestTimeout, ServerEOF,
)


def client(script):
    env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TMPDIR") if key in os.environ}
    return CodexClient([sys.executable, "-I", "-u", "-c", script], os.getcwd(), env)


def test_interleaving_concurrent_and_denials():
    c = client('''
import json, sys
out = lambda x: print(json.dumps(x), flush=True)
a=json.loads(input()); b=json.loads(input())
out({"method":"progress", "params":{"step":1}})
for i, method in enumerate(["item/commandExecution/requestApproval", "item/fileChange/requestApproval", "item/permissions/requestApproval", "unknown/request"]):
 out({"id":"s"+str(i), "method":method, "params":{}})
 response=json.loads(input())
 out({"method":"denialReceipt", "params":response})
out({"id":b["id"],"result":b["method"]}); out({"id":a["id"],"result":a["method"]})
for line in sys.stdin: pass
''')
    try:
        results = {}
        def call(method):
            results[method] = c.request(method, {}, 3)
        threads = [threading.Thread(target=call, args=(m,)) for m in ("config/read", "hooks/list")]
        for t in threads: t.start()
        for t in threads: t.join(4)
        assert results == {"config/read": "config/read", "hooks/list": "hooks/list"}
        events = [c.next_event(timeout=2) for _ in range(9)]
        assert events[0]["method"] == "progress"
        denials = [e for e in events if e.get("type") == "server_request_denied"]
        receipts = [e["params"] for e in events if e.get("method") == "denialReceipt"]
        assert len(denials) == 4
        assert receipts[0]["result"] == {"decision": "decline"}
        assert receipts[1]["result"] == {"decision": "decline"}
        assert receipts[2]["result"] == {"permissions": {}, "scope": "turn"}
        assert receipts[3]["error"]["code"] == -32601
    finally:
        c.close()


def test_initialize_and_forbidden_method_no_io():
    c = client('''
import json,sys
for line in sys.stdin:
 m=json.loads(line)
 if "id" in m: print(json.dumps({"id":m["id"],"result":m["method"]}),flush=True)
 else: print(json.dumps({"method":"seen", "params":m}),flush=True)
''')
    try:
        with pytest.raises(ValueError): c.request("command/exec", {}, 1)
        with pytest.raises(queue.Empty): c.next_event(timeout=.1)
        assert c.request("initialize", {}, 2) == "initialize"
        assert c.next_event(timeout=2)["params"] == {"method": "initialized"}
    finally: c.close()


def test_timeout_no_retry_and_eof():
    c = client('''
import json,sys,time
m=json.loads(input()); print(json.dumps({"method":"seen","params":m}),flush=True)
time.sleep(.3)
print(json.dumps({"id":m["id"],"result":1}),flush=True)
for line in sys.stdin:
 m=json.loads(line); print(json.dumps({"id":m["id"],"result":2}),flush=True)
''')
    try:
        with pytest.raises(RequestTimeout): c.request("config/read", {}, .05)
        assert c.next_event(timeout=1)["method"] == "seen"
        assert c.request("hooks/list", {}, 2) == 2
        with pytest.raises(queue.Empty): c.next_event(timeout=.1)
    finally: c.close()
    c = client('import sys; sys.stdin.readline()')
    try:
        with pytest.raises(ServerEOF): c.request("config/read", {}, 2)
    finally: c.close()


@pytest.mark.parametrize("payload", [repr("not-json\n"), "'x' * (1024 * 1024 + 1)"])
def test_bad_frame(payload):
    c = client('import sys; sys.stdin.readline(); sys.stdout.write(' + payload + '); sys.stdout.flush()')
    try:
        with pytest.raises(ProtocolFailure): c.request("config/read", {}, 2)
    finally: c.close()


def test_close_terminates_owned_process():
    c = client('import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print("{\\"method\\":\\"ready\\"}",flush=True); time.sleep(30)')
    assert c.next_event(timeout=2)["method"] == "ready"
    pid = c.pid
    c.close(grace=.1)
    assert not c.is_alive()
    assert c.returncode == -signal.SIGKILL
    with pytest.raises(ProcessLookupError): os.kill(pid, 0)


def test_close_cleans_group_when_leader_already_exited():
    child_code = (
        "import json,os,signal,time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "print(json.dumps({'method':'ready','params':{'pid':os.getpid()}}),flush=True); "
        "time.sleep(30)"
    )
    c = client("import subprocess,sys,time; subprocess.Popen([sys.executable, '-I', '-u', '-c', " + repr(child_code) + "]); time.sleep(.2)")
    event = c.next_event(timeout=2)
    assert event["method"] == "ready"
    child_pid = event["params"]["pid"]
    c._process.wait(timeout=2)
    try:
        c.close(grace=.2)
        assert not c._reader.is_alive()
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
    finally:
        try:
            os.kill(child_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
