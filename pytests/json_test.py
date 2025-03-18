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
    # FIXME: add test id and description of test
    (
        ['-f', 'abif', '-t', 'winlosstiejson'],
        'testdata/tenn-example/tennessee-example-simple.abif',
         'is_equal',
        ["Chat", "wins"],
        2
    ),
    # TEST 002:
    # FIXME: add test id and description of test
    (
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/tenn-example/tennessee-example-simple.abif',
         'is_equal',
        ["votelines", 0, "qty"],
        42
    ),
    # TEST 003:
    # FIXME: add test id and description of test
    (
        ['-f', 'jabmod', '-t', 'jabmod'],
        'testdata/california/simple001-example.jabmod.json',
         'is_equal',
        ["votelines", 0, "qty"],
        1
    ),
    # TEST 004:
    # FIXME: add test id and description of test
    (
        ['-f', 'jabmod', '-t', 'jabmod', '-m', 'consolidate'],
        'testdata/california/simple001-example.jabmod.json',
         'is_equal',
        ["votelines", 0, "qty"],
        5
    ),
    # TEST 005:
    # FIXME: add test id and description of test
    (
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
         'is_equal',
        ["roundmeta", -1, "winner"],
        ["LONDON_BREED"]
    ),
    # TEST 006:
    # FIXME: add test id and description of test
    (
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
         'is_equal',
        ["roundmeta", -1, "eliminated"],
        ["MARK_LENO"]
    ),
    # TEST 007:
    # FIXME: add test id and description of test
    (
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
         'is_equal',
        ["roundmeta", -1, "startingqty"],
        254016
    ),
    # TEST 008:
    # FIXME: add test id and description of test
    # FIXME - the report from the city says Breed won with 115977, but my
    # count shows 116020
    # 
    # SF Report:
    #  https://www.sfelections.org/results/20180605/data/20180627/mayor/20180627_mayor.pdf
    (
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
         'is_equal',
        ["rounds", -1, "LONDON_BREED"],
        116020
    ),
    # TEST 009:
    # FIXME: add test id and description of test
    (
        (['-f', 'abif', '-t', 'irvjson'],
         'testdata/california/sf2018special-results.abif',
         'is_equal',
         ["roundmeta", 0, "eliminated", 3],
         r'WRITE_IN')
    ),
    # TEST 010:
    # FIXME: add test id and description of test
    (
        (['-f', 'abif', '-t', 'irvjson'],
         'testdata/mock-elections/mock-twotie.abif',
         'contains',
         ["roundmeta", 13, "all_eliminated"],
         r'F')
    ),
    # TEST 011:
    # FIXME: add test id and description of test
    (
        (['-f', 'abif', '-t', 'jabmod'],
         'localabif/bolson-nameq/votedata-2024-01-27/2022-08-16_Alaska-U.S._Representative_(Special_General).abif',
         'length',
         ["candidates"],
         4)
    ),
    # TEST 012:
    # FIXME: add test id and description of test
    (
        (['-f', 'abif', '-t', 'paircountjson'],
         'testdata/commasep/commasquare.abif',
         'is_equal',
         ["A,X", "B,Y"],
         12)
    ),
    # TEST 013:
    # FIXME: add test id and description of test
    (
        (['-f', 'abif', '-t', 'jabmod'],
         'testdata/commasep/commasquare.abif',
         'is_equal',
         ["votelines", 0, "prefs", "C,Z", "rank"],
         3)
    ),
    # TEST 014:
    # Test the deprecated '-t paircountjson' parameter, which will be
    # replaced by the "-t json -m pairwise" combo
    pytest.param(['-f', 'abif', '-t', 'paircountjson'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["Chat", "Knox"],
                 83,
                 id='test014'),
    # TEST 015:
    # Test the "-t json -m pairwise" combo
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'pairwise'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["Chat", "Knox"],
                 83,
                 id='test015'),
    # TEST 016:
    # Test the deprecated '-t irvjson' parameter, which will be
    # replaced by "-t json -m IRV" combo
    pytest.param(['-f', 'abif', '-t', 'irvjson'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["winner", 0],
                 "Knox",
                 id='test016'),
    # TEST 017:
    # Test the "-t json -m IRV" combo
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'IRV'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["winner", 0],
                 "Knox",
                 id='test017'),
]

@pytest.mark.parametrize(
    'cmd_args, inputfile, testtype, keylist, value', testlist
)
def test_json_key_subkey_val(cmd_args, inputfile, testtype, keylist, value):
    """Test equality of subkey to a value"""
    # TODO: work out what I had planned with commit 56c3432e on
    # 2023-10-08, since I'd like to use a generalized approach to
    # skipping tests based on files that haven't been fetched with
    # fetchmgr.py
    try:
        fh = open(inputfile, 'rb')
        fh.close()
    except:
        msg = f'Missing file: {inputfile}'
        msg += "Please run './fetchmgr.py *.fetchspec.json' "
        msg += "if you haven't already"
        pytest.skip(msg)

    cmd_args.append(inputfile)
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    outputdict = json.loads("\n".join(abiftool_output))

    if testtype == 'is_equal':
        assert get_value_from_obj(outputdict, keylist) == value
    elif testtype == 'contains':
        assert value in get_value_from_obj(outputdict, keylist)
    elif testtype == 'length':
        assert len(get_value_from_obj(outputdict, keylist)) == value
    else:
        assert testtype in ['is_equal', 'contains', 'length']
