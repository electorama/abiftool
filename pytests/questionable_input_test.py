import pytest
import re
from subprocess import run, PIPE
from abiftestfuncs import *

@pytest.mark.parametrize(
    'cmd_args, inputfile, pattern',
    [
        (['-t', 'jabmod'],
         'testdata/questionable/empty.abif',
         r"ERROR: Empty ABIF string"),
        (['-t', 'jabmod'],
         'testdata/questionable/novotelines-tenn.abif',
         "ERROR: No votelines in "),
        (['-t', 'jabmod', '--cleanws'],
         'testdata/questionable/leadingspace-tenn.abif',
         r".ballotcount.: 100")
    ]
)
def test_questionable_output(cmd_args, inputfile, pattern):
    assert check_regex_in_output(cmd_args, inputfile, pattern)
