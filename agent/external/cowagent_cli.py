"""Explicit, local-only launch of the named-agent experiment. Never installed."""
import argparse
import json
import os
from pathlib import Path
import stat
import signal
import threading
import time


def private_json(path):
    path = Path(path)
    info = path.lstat()
    if (path.resolve() != path or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1):
        raise ValueError('Private owner-controlled launch file required')
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    commands = parser.add_subparsers(dest='action', required=True)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--output', required=True)
    serve = commands.add_parser('serve')
    serve.add_argument('--launch', required=True)
    args = parser.parse_args()
    # Set the native data location before importing its config/log modules.
    config_path = Path(args.config).resolve(strict=True)
    os.environ['COW_DATA_DIR'] = str(config_path.parent)
    os.umask(0o077)
    from .cowagent_native import CowAgentNative
    if args.action == 'inspect':
        native = CowAgentNative(config_path)
        value = {'preflight': 'passed', 'snapshot': native.discover()}
        # New file only; never overwrite an accepted receipt.
        with Path(args.output).open('x') as out:
            json.dump(value, out, sort_keys=True, indent=2)
        return
    from .contract import Credential
    from .cowagent_adapter import CowAgentRuntime
    from .operator_control import OperatorControl
    from .approved_dispatch import ApprovalJournal
    launch = private_json(args.launch)
    cred = launch['credential']
    credential = Credential(cred['supervisor_id'], cred['runtime_id'], cred['key_id'],
                            bytes.fromhex(cred['secret_hex']), cred['expires_at'],
                            tuple(cred['operations']))
    native = CowAgentNative(config_path, launch['enrollment'])
    control = OperatorControl(launch['operator_dir'])
    runtime = CowAgentRuntime(launch['runtime_dir'], launch['socket'], credential,
                             native, approval_gate=ApprovalJournal(control))
    thread = threading.Thread(target=runtime.serve, daemon=True)
    thread.start()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    # This experimental service is bounded to its launch credential and at
    # most five minutes. It never becomes a recurring background integration.
    local = time.localtime()
    before_maintenance = ((23 * 60 + 45) - (local.tm_hour * 60 + local.tm_min)) * 60 - local.tm_sec
    deadline = min(credential.expires_at, time.time() + 300, time.time() + before_maintenance)
    try:
        while thread.is_alive() and not stop.is_set() and time.time() < deadline:
            thread.join(timeout=.5)
    finally:
        runtime.close()
        if native.bridge is not None and native.bridge.recovery_service is not None:
            native.bridge.recovery_service.close(wait=True)


if __name__ == '__main__':
    main()
