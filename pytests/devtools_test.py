import json
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize('log_path', ['missing/debug.log', '.', 'relative.log'])
def test_unusable_log_path_does_not_interrupt_cli(tmp_path, log_path):
    path = log_path if log_path == 'relative.log' else str(tmp_path / log_path)
    result = subprocess.run(
        [sys.executable, 'abiftool.py', '-t', 'jabmod', 'testdata/burl2009/burl2009.abif'],
        env={**os.environ, 'ABIFLIB_LOG': path},
        capture_output=True, text=True, check=True,
    )

    assert json.loads(result.stdout)['metadata']['ballotcount'] > 0
    assert result.stderr.count('Warning: ABIFLIB_LOG disabled:') == 1
    assert path in result.stderr
    assert not (tmp_path / 'missing').exists()
