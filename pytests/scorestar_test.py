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
        pytest.param(['-t', 'jabmod', '--add-scores'],
                     'testdata/tenn-example/tennessee-example-simple.abif',
                     r"                    \"rating\": 3",
                     id='scorestar_001'),
        # TEST 002:
        pytest.param(['-t', 'jabmod'],
                     'testdata/tenn-example/tennessee-example-scores.abif',
                     r"                    \"rating\": 133",
                     id='scorestar_002'),
        # TEST 003: 
        pytest.param(['-t', 'jabmod', '--add-scores'],
                     'testdata/tenn-example/tennessee-example-scores.abif',
                     r"                    \"rating\": 133",
                     id='scorestar_003'),
        # TEST 004; 
        pytest.param(['-t', 'text', '-m', 'score'],
                     'testdata/tenn-example/tennessee-example-scores.abif',
                     r"19370 points \(from 100 voters\) -- Knoxville, TN",
                     id='scorestar_004'),
        # TEST 005:
        pytest.param(['-t', 'text', '-m', 'STAR'],
                     'testdata/tenn-example/tennessee-example-STAR.abif',
                     r"261 stars \(from 100 voters\) -- Nashville, TN",
                     id='scorestar_005'),
        # TEST 006:
        pytest.param(['-t', 'text', '-m', 'STAR'],
                     'testdata/tenn-example/tennessee-example-STAR.abif',
                     r"Nashville, TN preferred by 68 of 100 voters",
                     id='scorestar_006'),
        # TEST 007:
        pytest.param(['-t', 'text', '-m', 'STAR'],
                     'testdata/tenn-example/tennessee-example-STAR.abif',
                     r"Winner: Nashville, TN",
                     id='scorestar_007'),
        # TEST 008:
        pytest.param(['-t', 'text', '-m', 'STAR'],
                     'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
                     r"STAR Winner: Chattanooga, TN",
                     id='scorestar_008'),
        # TEST 009:
        pytest.param(['-t', 'text', '-m', 'score'],
                     'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
                     r"Score Winner: Knoxville, TN",
                     id='scorestar_009'),
        # TEST 010:
        pytest.param(['-t', 'text', '-m', 'Copeland'],
                     'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
                     r"Copeland Winner: Nashville, TN",
                     id='scorestar_010'),
        # TEST 011:
        pytest.param(['-t', 'text'],
                     'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
                     r"Nash \(3-0-0\)",
                     id='scorestar_011'),
        # TEST 012:
        pytest.param(['-t', 'text', '-m', 'score'],
                     'testdata/commasep/jman722-example.abif',
                     r"88 points \(from 19 voters\) -- Allie",
                     id='scorestar_012'),
        # TEST 013:
        pytest.param(['-t', 'text', '-m', 'score'],
                     'testdata/commasep/tn-example-missing-scores.abif',
                     r"17480 points \(from 58 voters\) -- Knoxville",
                     id='scorestar_013'),
        # TEST 014:
        pytest.param(['-t', 'text', '-m', 'score'],
                     'testdata/commasep/tn-example-scores-and-commas.abif',
                     r"19370 points \(from 100 voters\) -- Knoxville",
                     id='scorestar_014'),
        # TEST 015:
        pytest.param(['-t', 'text', '-m', 'STAR', '--add-scores'],
                     'testdata/burl2009/burl2009.abif',
                     r"26167 stars \(from 6706 voters\) -- Andy Montroll",
                     #r"0 stars \(from 0 voters\) -- Andy Montroll",
                     id='scorestar_015'),
        # TEST 016:
        # Test whether a one-candidate election is handled by STAR
        pytest.param(['-t', 'text', '-m', 'STAR', '--add-scores'],
                     'testdata/mock-elections/mock-one-cand.abif',
                     r"A preferred by 100 of 100 voters",
                     id='scorestar_016'),
        # TEST 017:
        # Test whether a one-candidate election with abstentions is handled by STAR
        pytest.param(['-t', 'text', '-m', 'STAR', '--add-scores'],
                     'testdata/mock-elections/mock-one-cand-with-blanks.abif',
                     r"A preferred by 50 of 100 voters",
                     id='scorestar_017'),
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
    if len(cmd_args) == 2 and cmd_args[1] == 'text' and not has_lib("texttable"):
        pytest.skip("Skipping test because 'texttable' is not installed.")

    # 2024-08-06 - I'm not sure what the get_abiftool_output_as_array
    # call is doing in this context, and I'm pretty sure I can/should
    # eliminate it:
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    LOGOBJ.log("LOGOBJ test_grep_for_regexp/scorestar" +
               f"{inputfile=} {pattern=}\n")
    assert check_regex_in_output(cmd_args, inputfile, pattern)
    return None
