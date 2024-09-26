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
    )
]

@pytest.mark.parametrize(
    'cmd_args, inputfile, testtype, keylist, value', testlist
)
def test_json_key_subkey_val(cmd_args, inputfile, testtype, keylist, value):
    """Test equality of subkey to a value"""
    fh = open(inputfile, 'rb')
    cmd_args.append(inputfile)
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    outputdict = json.loads("\n".join(abiftool_output))
    if testtype == 'is_equal':
        assert get_value_from_obj(outputdict, keylist) == value
    elif testtype == 'contains':
        assert value in get_value_from_obj(outputdict, keylist)
    else:
        assert testtype in ['is_equal', 'contains']
