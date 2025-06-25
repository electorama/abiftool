import pytest
import re
from subprocess import run, PIPE
from abiftestfuncs import *

@pytest.mark.parametrize(
    'cmd_args, inputfile, pattern',
    [
        pytest.param(
            ['-t', 'jabmod'],
            'testdata/questionable/empty.abif',
            r"ballotcount[^\d]*0",
            id='q_001'
        ),
        pytest.param(
            ['-t', 'jabmod'],
            'testdata/questionable/novotelines-tenn.abif',
            r"ballotcount[^\d]*0",
            id='q_002'
        ),
        pytest.param(
            ['-t', 'jabmod', '--cleanws'],
            'testdata/questionable/leadingspace-tenn.abif',
            r".ballotcount.: 100",
            id='q_003'
        ),
    ]
)
def test_questionable_output(cmd_args, inputfile, pattern):
    assert check_regex_in_output(cmd_args, inputfile, pattern)
