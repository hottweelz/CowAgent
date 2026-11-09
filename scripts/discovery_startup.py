"""Launch the ordinary source app with one authenticated startup observation.

This helper never stops/restarts another process, creates a request, changes
configuration or contacts an adapter. Running it is a service launch and needs
separate operational authorization; --help is safe for preparation.
"""
import sys

# Suppress caches for imports controlled by this helper, without changing an
# importing caller's setting. Interpreter/site startup precedes our control.
_IMPORT_BYTECODE = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    import argparse
    from pathlib import Path
    import runpy
finally:
    sys.dont_write_bytecode = _IMPORT_BYTECODE


ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    previous_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--request', required=True, help='Existing private one-use request JSON')
        parser.add_argument('--control-dir', help='Existing empty private directory for operator drain control')
        args = parser.parse_args(argv)
        sys.path.insert(0, str(ROOT))
        from agent.discovery.startup_observer import prepare_launch
        launch = prepare_launch(args.request)
        if args.control_dir is not None:
            from common.maintenance_control import prepare
            launch.maintenance_control = prepare(args.control_dir)
    except Exception:
        raise SystemExit('Authenticated startup observation rejected') from None
    finally:
        sys.dont_write_bytecode = previous_bytecode
    # Same PID and interpreter prefix: do not resolve a venv symlink and exec
    # the framework Python, or preserve only VIRTUAL_ENV while losing its deps.
    sys.argv = [str(ROOT / 'app.py')]
    runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')


if __name__ == '__main__':
    main()
