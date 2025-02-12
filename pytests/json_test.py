from abiftestfuncs import *
import subprocess
import json
import os
import re
import glob
import sys
import pytest


testlist = [
    (
        ['-f', 'abif', '-t', 'winlosstiejson'],
        'testdata/tenn-example/tennessee-example-simple.abif',
         'is_equal',
        ["Chat", "wins"],
        2
    ),
    (
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/tenn-example/tennessee-example-simple.abif',
         'is_equal',
        ["votelines", 0, "qty"],
        42
    ),
    (
        ['-f', 'jabmod', '-t', 'jabmod'],
        'testdata/california/simple001-example.jabmod.json',
         'is_equal',
        ["votelines", 0, "qty"],
        1
    ),
    (
        ['-f', 'jabmod', '-t', 'jabmod', '-m', 'consolidate'],
        'testdata/california/simple001-example.jabmod.json',
         'is_equal',
        ["votelines", 0, "qty"],
        5
    ),
    (
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
         'is_equal',
        ["roundmeta", -1, "winner"],
        ["LONDON_BREED"]
    ),
    (
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
         'is_equal',
        ["roundmeta", -1, "eliminated"],
        ["MARK_LENO"]
    ),
    (
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
         'is_equal',
        ["roundmeta", -1, "startingqty"],
        254016
    ),
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
    (
        (['-f', 'abif', '-t', 'irvjson'],
         'testdata/california/sf2018special-results.abif',
         'is_equal',
         ["roundmeta", 0, "eliminated", 3],
         r'WRITE_IN')
    ),
    (
        (['-f', 'abif', '-t', 'irvjson'],
         'testdata/mock-elections/mock-twotie.abif',
         'contains',
         ["roundmeta", 13, "all_eliminated"],
         r'F')
    ),
    (
        (['-f', 'abif', '-t', 'jabmod'],
         'testdata/AlaskaSpecial2022.abif',
         'length',
         ["candidates"],
         4)
    ),
    (
        (['-f', 'abif', '-t', 'paircountjson'],
         'testdata/commasep/commasquare.abif',
         'is_equal',
         ["A,X", "B,Y"],
         12)
    ),
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
