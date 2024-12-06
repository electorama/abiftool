import abiflib
import pytest
import re
from subprocess import run, PIPE
from abiftestfuncs import *

LOGOBJ = abiflib.LogfileSingleton()

@pytest.mark.parametrize(
    'cmd_args, inputfile, pattern',
    [
        # TEST 001:
        (['-t', 'jabmod', '--add-scores'],
         'testdata/tenn-example/tennessee-example-simple.abif',
         r"                    \"rating\": 3"),
        # TEST 002:
        (['-t', 'jabmod'],
         'testdata/tenn-example/tennessee-example-scores.abif',
         r"                    \"rating\": 133"),
        # TEST 003:
        (['-t', 'jabmod', '--add-scores'],
         'testdata/tenn-example/tennessee-example-scores.abif',
         r"                    \"rating\": 133"),
        # TEST 004;
        (['-t', 'text', '-m', 'score'],
         'testdata/tenn-example/tennessee-example-scores.abif',
         r"19370 points \(from 100 voters\) -- Knoxville, TN"),
        # TEST 005:
        (['-t', 'text', '-m', 'STAR'],
         'testdata/tenn-example/tennessee-example-STAR.abif',
         r"261 stars \(from 100 voters\) -- Nashville, TN"),
        # TEST 006:
        (['-t', 'text', '-m', 'STAR'],
         'testdata/tenn-example/tennessee-example-STAR.abif',
         r"Nashville, TN preferred by 68 of 100 voters"),
        # TEST 007:
        (['-t', 'text', '-m', 'STAR'],
         'testdata/tenn-example/tennessee-example-STAR.abif',
         r"Winner: Nashville, TN"),
        # TEST 008:
        (['-t', 'text', '-m', 'STAR'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"STAR Winner: Chattanooga, TN"),
        # TEST 009:
        (['-t', 'text', '-m', 'score'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"Score Winner: Knoxville, TN"),
        # TEST 010:
        (['-t', 'text', '-m', 'Copeland'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"Copeland Winner: Nashville, TN"),
        # TEST 011:
        (['-t', 'text'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"Nash \(3-0-0\)"),
        # TEST 012:
        (['-t', 'text', '-m', 'score'],
         'testdata/commasep/jman722-example.abif',
         r"88 points \(from 19 voters\) -- Allie"),
        # TEST 013:
        (['-t', 'text', '-m', 'score'],
         'testdata/commasep/tn-example-missing-scores.abif',
         r"17480 points \(from 58 voters\) -- Knoxville"),
        # TEST 014:
        (['-t', 'text', '-m', 'score'],
         'testdata/commasep/tn-example-scores-and-commas.abif',
         r"19370 points \(from 100 voters\) -- Knoxville"),
    ]
)

def test_grep_output_for_regexp(cmd_args, inputfile, pattern):
    """Testing text output from abiftool.py for regexp"""
    # TODO: merge this with the version in debtally_test.py
    try:
        fh = open(inputfile, 'rb')
    except:
        msg = f'Missing file: {inputfile}'
        msg += "Please run './fetchmgr.py *.fetchspec.json' "
        msg += "if you haven't already"
        pytest.skip(msg)
    # 2024-08-06 - I'm not sure what the get_abiftool_output_as_array
    # call is doing in this context, and I'm pretty sure I can/should
    # eliminate it:
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    LOGOBJ.log("LOGOBJ test_grep_for_regexp/scorestar" +
               f"{inputfile=} {pattern=}\n")
    assert check_regex_in_output(cmd_args, inputfile, pattern)
    return None
