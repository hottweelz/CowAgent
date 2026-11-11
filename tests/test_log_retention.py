"""The persistent service opts in to bounded log retention."""
import os
from pathlib import Path
import subprocess
import sys


def test_opt_in_file_rotation_bounds_retention(tmp_path):
    env = {**os.environ, "COW_DATA_DIR": str(tmp_path),
           "COW_LOG_MAX_BYTES": "512", "COW_LOG_BACKUPS": "2"}
    subprocess.run(
        [sys.executable, "-c",
         "from common.log import logger; "
         "[logger.info('event-%03d %s', i, 'x' * 80) for i in range(40)]"],
        env=env, cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL, check=True, timeout=10,
    )
    logs = list(tmp_path.glob("run.log*"))
    assert {p.name for p in logs} == {"run.log", "run.log.1", "run.log.2"}
    assert all(p.stat().st_size <= 512 for p in logs)
    assert "event-039" in (tmp_path / "run.log").read_text()
