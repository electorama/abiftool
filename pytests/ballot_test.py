#!/usr/bin/env python3
"""Test ballot type detection for all mock election files."""

from abiftestfuncs import *
import pytest

# Expected ballot types for each .abif file in testdata/mock-elections/
# Based on file content analysis and naming conventions
ballot_type_testlist = [
    # Files with binary ratings (0/1) -> approval
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-approval.abif',
        'is_equal',
        ["ballot_type"],
        "choose_many",
        id='tennessee-example-approval'
    ),

    # Files with ranked ballots (>) -> ranked
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-simple.abif',
        'is_equal',
        ["ballot_type"],
        "ranked",
        id='tennessee-example-simple'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-overvote-01.abif',
        'is_equal',
        ["ballot_type"],
        "ranked",
        id='tennessee-example-overvote-01'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-overvote-02.abif',
        'is_equal',
        ["ballot_type"],
        "ranked",
        id='tennessee-example-overvote-02'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-overvote-03.abif',
        'is_equal',
        ["ballot_type"],
        "ranked",
        id='tennessee-example-overvote-03'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-irv-tie.abif',
        'is_equal',
        ["ballot_type"],
        "rated",
        id='tennessee-example-irv-tie'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-nested-quote.abif',
        'is_equal',
        ["ballot_type"],
        "rated",
        id='tennessee-example-nested-quote'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-vice-capital.abif',
        'is_equal',
        ["ballot_type"],
        "rated",
        id='tennessee-vice-capital'
    ),

    # Files with multi-level ratings (0-400, 0-5) -> rated
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-scores.abif',
        'is_equal',
        ["ballot_type"],
        "rated",
        id='tennessee-example-scores'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-STAR.abif',
        'is_equal',
        ["ballot_type"],
        "rated",
        id='tennessee-example-STAR'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-STAR-score-difference.abif',
        'is_equal',
        ["ballot_type"],
        "rated",
        id='tennessee-example-STAR-score-difference'
    ),

    # Basic mock files -> ranked or choose_one
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/mock-tie.abif',
        'is_equal',
        ["ballot_type"],
        "ranked",
        id='mock-tie'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/mock-twotie.abif',
        'is_equal',
        ["ballot_type"],
        "ranked",
        id='mock-twotie'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/mock-one-cand.abif',
        'is_equal',
        ["ballot_type"],
        "choose_one",
        id='mock-one-cand'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/mock-one-cand-with-blanks.abif',
        'is_equal',
        ["ballot_type"],
        "choose_one",
        id='mock-one-cand-with-blanks'
    ),
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/mock-all-blank.abif',
        'is_equal',
        ["ballot_type"],
        "unknown",
        id='mock-all-blank'
    ),

    # Special cases
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-blank-prefstr.abif',
        'is_equal',
        ["ballot_type"],
        "rated",
        id='tennessee-example-blank-prefstr'
    ),
]


@pytest.mark.parametrize("cmd_args, inputfile, testtype, keylist, value", ballot_type_testlist)
def test_ballot_type_detection(cmd_args, inputfile, testtype, keylist, value):
    """Test that ballot type detection works correctly for all mock election files."""
    run_json_output_test_from_abif(cmd_args, inputfile, testtype, keylist, value)
