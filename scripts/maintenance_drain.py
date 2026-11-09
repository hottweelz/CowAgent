"""Close admission and observe only an explicitly enabled private service."""
import argparse
import json
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-dir', required=True, help='Existing private service control directory')
    parser.add_argument('--grant', required=True, choices=['close-admission-and-observe'])
    parser.add_argument('--timeout', type=float, default=30, help='Observation seconds, from 0 to 60')
    args = parser.parse_args(argv)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from common.maintenance_control import submit_drain
        receipt = submit_drain(args.control_dir, grant=args.grant, timeout=args.timeout)
    except Exception:
        print(json.dumps({'status': 'unavailable', 'drained': False, 'reason': 'maintenance_control_unavailable'}))
        return 2
    finally:
        sys.dont_write_bytecode = previous
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt['drained'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
