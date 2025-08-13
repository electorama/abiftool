#!/usr/bin/env python3
"""Tests for approval voting functionality in abiflib"""

from abiftestfuncs import *
import subprocess
import json
import os
import re
import glob
import sys
import pytest

# Test data for approval voting tests
testlist = [
    # TEST 001:
    # Test native approval voting with Tennessee example - Nashville should win
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-approval.abif',
        'is_equal',
        ["winners", 0],
        "Nash",
        id='approval_001'
    ),
    # TEST 002:
    # Test native approval voting - check Nashville's approval count
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-approval.abif',
        'is_equal',
        ["approval_counts", "Nash"],
        50,
        id='approval_002'
    ),
    # TEST 003:
    # Verify ballot type detection for "choose_many" ballots
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-approval.abif',
        'is_equal',
        ["ballot_type"],
        "choose_many",
        id='approval_003'
    ),
    # TEST 004:
    # Test simulated approval voting with ranked Tennessee example (auto-detect)
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],
        'testdata/mock-elections/tennessee-example-simple.abif',
        'is_equal',
        ["ballot_type"],
        "ranked",
        id='approval_004'
    ),
]

@pytest.mark.parametrize(
    'cmd_args, inputfile, testtype, keylist, value', testlist
)
def test_approval_voting(cmd_args, inputfile, testtype, keylist, value):
    """Test approval voting functionality using the generic test framework"""
    run_json_output_test_from_abif(cmd_args, inputfile, testtype, keylist, value)
