# Core ABIF Parser and Format Tests
#
# This test file focuses on core parsing functionality and data format handling.
# Method-specific tests have been moved to specialized files:
#   - IRV tests: irv_test.py
#   - FPTP tests: fptp_test.py  
#   - Pairwise tests: pairwise_test.py
#   - STAR tests: scorestar_test.py
#
# Tests in this file cover:
#   - ABIF format parsing edge cases
#   - JABMOD format roundtripping
#   - SF CVR format support
#   - Candidate name parsing (including whitespace handling)
#   - Ballot counting accuracy
#   - Error conditions and malformed input

from abiftestfuncs import *
import subprocess
import json
import os
import re
import glob
import sys
import pytest

testlist = [
    # TEST 001:
    # Test the '-t jabmod' parameter with the simplified TN example
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/tenn-example/tennessee-example-simple.abif',
        'is_equal',
        ["votelines", 0, "qty"],
        42,
        id='core_001'
    ),
    # TEST 002:
    # Test roundtripping jabmod with a mock election example
    pytest.param(
        ['-f', 'jabmod', '-t', 'jabmod'],
        'testdata/california/simple001-example.jabmod.json',
        'is_equal',
        ["votelines", 0, "qty"],
        1,
        id='core_002'
    ),
    # TEST 003:
    # Test roundtripping jabmod with a mock election example,
    # consolidating the results
    pytest.param(
        ['-f', 'jabmod', '-t', 'jabmod', '-m', 'consolidate'],
        'testdata/california/simple001-example.jabmod.json',
        'is_equal',
        ["votelines", 0, "qty"],
        5,
        id='core_003'
    ),
    # TEST 004:
    # Testing whether an Alaska election has 4 candidates
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'localabif/bolson-nameq/votedata-2024-01-27/2022-08-16_Alaska-U.S._Representative_(Special_General).abif',
        'length',
        ["candidates"],
        4,
        id='core_004'
    ),
    # TEST 005:
    # FIXME: figure out what this test is supposed to be checking
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/commasep/commasquare.abif',
        'is_equal',
        ["votelines", 0, "prefs", "C,Z", "rank"],
        3,
        id='core_005'
    ),
    # TEST 006:
    # Test that whitespace in quoted tokens is handled properly
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'localabif/bolson-nameq/votedata-2024-01-27/2022-08-16_Alaska-U.S._Representative_(Special_General).abif',
                 'is_equal',
                 ["candidates", "Begich, Nick"],
                 "Begich, Nick",
                 id='core_006'),
    # TEST 007:
    # Test that blank abif prefstrs are parsed and reported
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/mock-elections/tennessee-example-blank-prefstr.abif',
                 'is_equal',
                 ["votelines", 0, "prefstr"],
                 "",
                 id='core_007'),
    # TEST 008:
    # Test that embedded quotes are allowed within square brackets
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/mock-elections/tennessee-example-nested-quote.abif',
                 'is_equal',
                 ["votelines", 0, "prefs", "\"Memph\" Memphis", "rating"],
                 5,
                 id='core_008'),
    # TEST 009:
    # Test the way that ABIF files with nothing but blanks still counts the ballots
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/mock-elections/mock-all-blank.abif',
                 'is_equal',
                 ["metadata", "ballotcount"],
                 100,
                 id='core_009'),
    # TEST 010:
    # Test empty ABIF input string
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/empty.abif',
                 'is_equal',
                 ['metadata', 'ballotcount'],
                 0,
                 id='core_010'),
    # TEST 011:
    # Test ABIF with one voteline and one cand no newline
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/one-A.abif',
                 'is_equal',
                 ['metadata', 'ballotcount'],
                 1,
                 id='core_011'),
    # TEST 012:
    # Test ABIF with one voteline and one cand with newline
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/one-A-LF.abif',
                 'is_equal',
                 ['metadata', 'ballotcount'],
                 1,
                 id='core_012'),
    # TEST 013:
    # Test parsing of the Tennessee example in SF CVR format
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '1',
         '-t', 'jabmod'
        ],
        None,
        'is_equal',
        ["metadata", "ballotcount"],
        100,
        id='core_013'
    ),
    # TEST 014:
    # Test parsing of the Tennessee example in SF CVR format - specific voteline rank
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '1',
         '-t', 'jabmod'
        ],
        None,
        'is_equal',
        ["votelines", 0, "prefs", "Memph", "rank"],
        1,
        id='core_014'
    ),
    # TEST 015:
    # Make sure that we have 100 ballots on race #2 of the sample zipfile
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '2',
         '-t', 'jabmod'
        ],
        None,
        'is_equal',
        ["metadata", "ballotcount"],
        100,
        id='core_015'
    ),
    # TEST 016:
    # Make sure that Jackson shows up in race #2 in the sample zipfile
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '2',
         '-t', 'jabmod'
        ],
        None,
        'is_equal',
        ["votelines", 0, "prefs", "Jackson", "rank"],
        1,
        id='core_016'
    ),
    # TEST 017:
    # Make sure Memph has 42 first-place votes in race #1 in the sample zipfile
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '1',
         '-t', 'jabmod',
         '-m', 'consolidate'
        ],
        None,
        'is_equal',
        ["votelines", 0, "qty"],
        42,
        id='core_017'
    ),
    # TEST 018:
    # Ensure Murfreesboro has 26 first-place votes in race #1 in the sample zipfile
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '2',
         '-t', 'jabmod',
         '-m', 'consolidate'
        ],
        None,
        'is_equal',
        ["votelines", 1, "qty"],
        26,
        id='core_018'
    ),
    # TEST 019:
    # Test that trailing spaces in candidate definitions don't truncate names
    # FIXME: ABIF parser currently fails to handle trailing spaces correctly 
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/trailingspace-tenn.abif',
                 'is_equal',
                 ["candidates", "Memph"],
                 "Memphis, TN",
                 id='core_019',
                 marks=pytest.mark.xfail(reason="TDD: ABIF parser should handle trailing spaces in candidate definitions")),
    # TEST 020:
    # Test that trailing spaces don't affect Nashville either
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/trailingspace-tenn.abif',
                 'is_equal',
                 ["candidates", "Nash"],
                 "Nashville, TN",
                 id='core_020',
                 marks=pytest.mark.xfail(reason="TDD: ABIF parser should handle trailing spaces in candidate definitions")),
    # TEST 021:
    # Test that STAR voting shows correct candidate names despite trailing spaces
    pytest.param(['-t', 'json', '-m', 'STAR'],
                 'testdata/questionable/trailingspace-tenn.abif',
                 'is_equal',
                 ['winner_names', 0],
                 'Nashville, TN',
                 id='core_021',
                 marks=pytest.mark.xfail(reason="TDD: STAR output should show full names even with trailing space bug")),
    # TEST 022:
    # Test that score voting text output shows correct names (will fail due to trailing space bug)
    pytest.param(['-t', 'text', '-m', 'score'],
                 'testdata/questionable/trailingspace-tenn.abif',
                 'contains',
                 ['text_output'],
                 'Memphis, TN',
                 id='core_022',
                 marks=pytest.mark.xfail(reason="TDD: Score voting should show full candidate names")),
    # TEST 023:
    # Test ballot count is still correct despite trailing spaces
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/trailingspace-tenn.abif',
                 'is_equal',
                 ["metadata", "ballotcount"],
                 100,
                 id='core_023'),
    # TEST 024:
    # Test that vote quantities are parsed correctly despite trailing spaces
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/trailingspace-tenn.abif',
                 'is_equal',
                 ["votelines", 0, "qty"],
                 42,
                 id='core_024'),
]

@pytest.mark.parametrize(
    'cmd_args, inputfile, testtype, keylist, value', testlist
)
def test_json_key_subkey_val(cmd_args, inputfile, testtype, keylist, value):
    """Test equality of subkey to a value"""
    run_json_output_test_from_abif(cmd_args, inputfile, testtype, keylist, value)
