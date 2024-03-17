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
def test_abiftool_linecount(cmd_args, inputfile, pattern):
    command = ['python3', 'abiftool.py', *cmd_args, inputfile]
    completed_process = run(command, stdout=PIPE, text=True)

    # Get the captured output and count the lines
    output_lines = completed_process.stdout.splitlines()

    assert check_regex_in_textarray(pattern, output_lines)
