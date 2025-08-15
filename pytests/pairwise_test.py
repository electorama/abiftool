from abiftestfuncs import *
import subprocess
import json
import os
import re
import glob
import sys
import pytest

# Tests for pairwise comparison logic (Copeland, Condorcet, etc.)
# These tests focus on the counting method logic, not ballot parsing.
# Moved from core_test.py to separate pairwise-specific functionality.

testlist = [
    # TEST 001:
    # Test the '-t winlosstiejson' parameter with the simplified TN example
    # Tests Copeland winner calculation logic
    pytest.param(
        ['-f', 'abif', '-t', 'winlosstiejson'],
        'testdata/tenn-example/tennessee-example-simple.abif',
        'is_equal',
        ["Chat", "wins"],
        2,
        id='pairwise_001'
    ),
    # TEST 002:
    # Test pairwise count matrix generation with comma-separated candidates
    pytest.param(
        ['-f', 'abif', '-t', 'paircountjson'],
        'testdata/commasep/commasquare.abif',
        'is_equal',
        ["A,X", "B,Y"],
        12,
        id='pairwise_002'
    ),
    # TEST 003:
    # Test the deprecated '-t paircountjson' parameter
    # TODO: Eventually remove when deprecated format is no longer supported
    pytest.param(['-f', 'abif', '-t', 'paircountjson'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["Chat", "Knox"],
                 83,
                 id='pairwise_003'),
    # TEST 004:
    # Test the modern "-t json -m pairwise" combo
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'pairwise'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["Chat", "Knox"],
                 83,
                 id='pairwise_004'),
    # TEST 005:
    # Test "-t json -m pairlist" with default winning-votes method
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'pairlist'],
                 'testdata/mock-elections/mock-wv-margins.abif',
                 'is_equal',
                 ["pairwise_matchups", 0, "victory_size"],
                 56,
                 id='pairwise_005'),
    # TEST 006:
    # Test "-t json -m pairlist -m margins" modifier combination
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'pairlist', '-m', 'margins'],
                 'testdata/mock-elections/mock-wv-margins.abif',
                 'is_equal',
                 ["pairwise_matchups", 0, "victory_size"],
                 39,
                 id='pairwise_006'),
]

@pytest.mark.parametrize(
    'cmd_args, inputfile, testtype, keylist, value', testlist
)
def test_pairwise_logic(cmd_args, inputfile, testtype, keylist, value):
    """Test pairwise comparison and counting logic"""
    run_json_output_test_from_abif(cmd_args, inputfile, testtype, keylist, value)
