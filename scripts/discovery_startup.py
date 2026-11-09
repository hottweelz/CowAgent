"""Launch the ordinary source app with one authenticated startup observation.

This helper never stops/restarts another process, creates a request, changes
configuration or contacts an adapter. Running it is a service launch and needs
separate operational authorization; --help is safe for preparation.
"""
import argparse
from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, help='Existing private one-use request JSON')
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    try:
        from agent.discovery.startup_observer import prepare_launch
        prepare_launch(args.request)
    except Exception:
        raise SystemExit('Authenticated startup observation rejected') from None
    # Same PID and interpreter prefix: do not resolve a venv symlink and exec
    # the framework Python, or preserve only VIRTUAL_ENV while losing its deps.
    sys.argv = [str(ROOT / 'app.py')]
    runpy.run_path(str(ROOT / 'app.py'), run_name='__main__')


if __name__ == '__main__':
    main()
