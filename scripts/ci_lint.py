"""Run the F-class gate on existing Python files changed from a valid base."""
import os
from pathlib import Path
import re
import subprocess
import sys


def main():
    base = os.environ.get('BASE_SHA', '')
    if not re.fullmatch(r'[0-9a-fA-F]{40}', base) or base == '0' * 40:
        raise SystemExit('BASE_SHA must be a nonzero 40-character commit SHA')
    subprocess.run(['git', 'cat-file', '-e', f'{base}^{{commit}}'], check=True)
    diff = subprocess.run(['git', 'diff', '--name-only', '-z', '--diff-filter=ACMRT', base,
                           'HEAD', '--', '*.py'], check=True, stdout=subprocess.PIPE).stdout
    files = [os.fsdecode(path) for path in diff.split(b'\0') if path and Path(os.fsdecode(path)).is_file()]
    if not files:
        print('No existing Python files changed.')
        return 0
    return subprocess.call([sys.executable, '-m', 'ruff', 'check', '--select', 'F', '--ignore',
                            'F403,F405', '--', *files])


if __name__ == '__main__':
    raise SystemExit(main())
