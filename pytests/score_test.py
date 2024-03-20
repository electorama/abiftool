import pytest
import re
from subprocess import run, PIPE
from abiftestfuncs import *

@pytest.mark.parametrize(
    'cmd_args, inputfile, pattern',
    [
        (['-t', 'jabmod'],
         'testdata/tenn-example/tennessee-example-simple.abif',
         r"                    \"rating\": null,"),
        (['-t', 'jabmod', '--add-scores'],
         'testdata/tenn-example/tennessee-example-simple.abif',
         r"                    \"rating\": 3,"),
        (['-t', 'jabmod'],
         'testdata/tenn-example/tennessee-example-scores.abif',
         r"                    \"rating\": \"133\","),
        (['-t', 'jabmod', '--add-scores'],
         'testdata/tenn-example/tennessee-example-scores.abif',
         r"                    \"rating\": \"133\",")
    ]
)
def test_score_extrapolation(cmd_args, inputfile, pattern):
    print(inputfile)
    from pathlib import Path
    print(Path(inputfile).read_text())
    assert check_regex_in_output(cmd_args, inputfile, pattern)
