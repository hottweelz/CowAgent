"""Local JSON command-line interface for operator decisions.

This module does not expose a network service or enable task execution.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from . import contract
from .operator_control import OperatorControl

_SCOPE_FIELDS = frozenset({
    "supervisor_id", "owner_id", "source_id", "conversation_id", "runtime_id",
})
_ERROR = {"status": "error", "error": "operator_control_failed"}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("Invalid command")


def _parser():
    parser = _Parser(description="Local operator decision controls")
    parser.add_argument("--state-dir", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")

    apply_parser = commands.add_parser("apply")
    apply_parser.add_argument("--request", required=True, metavar="PATH_OR_-")

    for name in ("status", "audit"):
        command = commands.add_parser(name)
        command.add_argument("--scope", required=True, metavar="PATH_OR_-")
        if name == "status":
            command.add_argument("--task-id")
    return parser


def _state_path(value):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("State directory must be absolute")
    if path.resolve(strict=False) != path:
        raise ValueError("State directory must be canonical")
    return path


def _read_json(source):
    if source == "-":
        raw = sys.stdin.buffer.read(contract.MAX_MESSAGE_BYTES + 1)
    else:
        with Path(source).open("rb") as stream:
            raw = stream.read(contract.MAX_MESSAGE_BYTES + 1)
    if len(raw) > contract.MAX_MESSAGE_BYTES:
        raise ValueError("Input too large")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Input must be an object")
    return value


def _scope(source):
    value = _read_json(source)
    if (set(value) != _SCOPE_FIELDS
            or not all(contract.identifier(value.get(field)) for field in _SCOPE_FIELDS)):
        raise ValueError("Invalid scope")
    return value


def _emit(value, stream=None):
    print(json.dumps(value, sort_keys=True, separators=(",", ":")),
          file=sys.stdout if stream is None else stream)


def main(argv=None):
    """Run the local operator CLI and return a process exit code."""
    try:
        args = _parser().parse_args(argv)
        state_dir = _state_path(args.state_dir)
        if args.command == "init":
            control = OperatorControl(state_dir, initialize=True)
            result = {
                "status": "initialized",
                "execution_enabled": False,
                "external_actions_enabled": False,
            }
        else:
            if not state_dir.is_dir():
                raise ValueError("Operator state is not initialized")
            control = OperatorControl(state_dir)
            if args.command == "apply":
                result = control.apply(_read_json(args.request))
            else:
                scope = _scope(args.scope)
                if args.command == "status":
                    result = control.status(scope, task_id=args.task_id)
                else:
                    result = control.audit(scope)
        _emit(result)
        return 0
    except (ValueError, OSError, sqlite3.Error):
        _emit(_ERROR, stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
