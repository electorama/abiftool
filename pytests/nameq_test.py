from abiftestfuncs import *
from abiflib import (
    convert_abif_to_jabmod,
    get_IRV_report,
    IRV_dict_from_jabmod
)
import glob
import json
import os
import pathlib
import pytest
import re
import subprocess
import sys

########################################
# 1. nameq_json tests

@pytest.mark.parametrize(
    'cmd_args, inputfile, testtype, keylist, value',
    [
        (
            ['-f', 'nameq', '-t', 'jabmod', '-m', 'consolidate'],
            'testdata/bolson-nameq/letters.nameq',
            'is_equal',
            ["votelines", 0, "qty"],
            2
        ),
        (
            ['-f', 'nameq', '-t', 'paircountjson'],
            'testdata/bolson-nameq/tennessee-example-simple.nameq',
            'is_equal',
            ['Knox', 'Chat'],
            17
        ),
        (
            ['-f', 'nameq', '-t', 'paircountjson'],
            'testdata/bolson-nameq/numbercand.nameq',
            'is_equal',
            ['00002', '00001'],
            4
        ),
        (
            ['-f', 'nameq', '-t', 'jabmod'],
            'testdata/bolson-nameq/nullcand.nameq',
            'is_equal',
            ['candidates', 'null'],
            'null'
        ),
    ],
    ids=['nameq_json_001', 'nameq_json_002', 'nameq_json_003', 'name_json_004']

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

########################################
# 2. nameq_text tests
texttestlist = [
    (['-f', 'nameq', '-t', 'text', '-m', 'IRV'],
     'testdata/bolson-nameq/letters.nameq',
     r"Total counted votes: 10"),
    (['-f', 'nameq', '-t', 'text', '-m', 'IRV'],
     'testdata/bolson-nameq/letters.nameq',
     r"The IRV winner is AAAA AAA"),
    (['-f', 'nameq', '-t', 'text', '-m', 'IRV'],
     'testdata/bolson-nameq/tennessee-example-simple.nameq',
     r"The IRV winner is Knox"),
    (['-f', 'nameq', '-t', 'text', '-m', 'IRV'],
     'testdata/bolson-nameq/tennessee-example-simple.nameq',
     r"The IRV winner is Knox"),
    (['-f', 'abif', '-t', 'nameq'],
     'testdata/mock-elections/tennessee-example-simple.abif',
     r'Memph=1&Nash=2&Chat=3&Knox=4'),
    (['-f', 'nameq', '-t', 'abif'],
     'testdata/bolson-nameq/numbercand.nameq',
     r'1:\[00005\]>\[00008\]>\[00003\]'),
    (['-f', 'nameq', '-t', 'abif'],
     'testdata/bolson-nameq/nullcand.nameq',
     r'1:null'),
]

@pytest.mark.parametrize(
    'cmd_args, inputfile, pattern', texttestlist,
    ids=['nameq_text_001', 'nameq_text_002', 'nameq_text_003', 'nameq_text_004',
         'nameq_text_005', 'nameq_text_006', 'nameq_text_007']
)
def test_IRV_text_output(cmd_args, inputfile, pattern):
    print(inputfile)
    from pathlib import Path
    print(Path(inputfile).read_text())
    assert check_regex_in_output(cmd_args, inputfile, pattern)
