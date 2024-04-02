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
         r"                    \"rating\": \"133\","),
        (['-t', 'text', '-m', 'score'],
         'testdata/tenn-example/tennessee-example-scores.abif',
         r"19370 points \(from 100 voters\) -- Knoxville, TN"),
        (['-t', 'text', '-m', 'STAR'],
         'testdata/tenn-example/tennessee-example-STAR.abif',
         r"261 stars \(from 100 voters\) -- Nashville, TN"),
        (['-t', 'text', '-m', 'STAR'],
         'testdata/tenn-example/tennessee-example-STAR.abif',
         r"Nashville, TN preferred by 68 of 100 voters"),
        (['-t', 'text', '-m', 'STAR'],
         'testdata/tenn-example/tennessee-example-STAR.abif',
         r"Winner: Nashville, TN"),
        (['-t', 'text', '-m', 'STAR'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"STAR Winner: Chattanooga, TN"),
        (['-t', 'text', '-m', 'score'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"Score Winner: Knoxville, TN"),
        (['-t', 'text', '-m', 'Copeland'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"Copeland Winner: Nashville, TN"),
        (['-t', 'text'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"Nash \(3-0-0\)"),
    ]
)

def test_score_extrapolation(cmd_args, inputfile, pattern):
    print(inputfile)
    from pathlib import Path
    print(Path(inputfile).read_text())
    assert check_regex_in_output(cmd_args, inputfile, pattern)
