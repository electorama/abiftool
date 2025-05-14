import abiflib
from abiftestfuncs import *
import json
import subprocess
from subprocess import run, PIPE
import os
import re
import glob
import sys
import pytest


testdicts=[
    {
        "fetchspec":"debian-elections.fetchspec.json",
        'outformat':"jabmod",
        'filename':"downloads/debian-elections/2022/vote_002_tally.txt",
        'key1':"metadata",
        'subkey1':"ballotcount",
        'val1':354,
        'id':'debvote_json_001'
    },
    {
        "fetchspec":"debian-elections.fetchspec.json",
        'outformat':"paircountjson",
        'filename':"downloads/debian-elections/2003/leader2003_tally.txt",
        'key1':"MartinMichlmayr",
        'subkey1':"BdaleGarbee",
        'val1':228,
        'id':'debvote_json_002'
    },
    {
        "fetchspec":"debian-elections.fetchspec.json",
        'outformat':"paircountjson",
        'filename':"downloads/debian-elections/2003/leader2003_tally.txt",
        'key1':"BdaleGarbee",
        'subkey1':"MartinMichlmayr",
        'val1':224,
        'id':'debvote_json_003'
    },
    {
        "fetchspec":"debian-elections.fetchspec.json",
        'outformat':"jabmod",
        'filename':"downloads/debian-elections/2021/vote_002_tally.txt",
        'key1':"metadata",
        'subkey1':"ballotcount",
        'val1':420,
        'id':'debvote_json_004'
    },
    {
        "fetchspec":"debian-elections.fetchspec.json",
        'outformat':"paircountjson",
        'filename':"downloads/debian-elections/2006/vote_002_tally.txt",
        'key1':"JeroenvanWolffelaar",
        'subkey1':"AriPollak",
        'val1':310,
        'id':'debvote_json_005'
    }
]

mycols = ('outformat', 'filename', 'key1', 'subkey1', 'val1', 'id')

pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey(testdict, cols=mycols)
    pytestlist.append(myparam)

LOGOBJ = abiflib.LogfileSingleton()

@pytest.mark.parametrize(mycols, pytestlist)
def test_debtally_cli_json(outformat, filename, key1, subkey1, val1, id):
    """Testing debtally using json output from abiftool.py"""
    # TODO: turn this into a generic test function for testing JSON
    #    output
    try:
        fh = open(filename, 'rb')
    except:
        print(f'Missing file: {filename}')
        print(
            "Please run './fetchmgr.py *.fetchspec.json' " +
            "if you haven't already")
        sys.exit()

    cmd_args = ["-f", "debtally", "-t", outformat, filename]
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    outputdict = json.loads("\n".join(abiftool_output))

    testcond = (outputdict[key1][subkey1] == val1)
    assert testcond
    return None


@pytest.mark.parametrize(
    'cmd_args, inputfile, pattern',
    [
        pytest.param(
            ["-f", "debtally", "-t", "csvrank"],
            "downloads/debian-elections/2006/vote_002_tally.txt",
            r"1ccb15e79dc5734b217fb8e3fb296b9d,1,4,2,1,2,6,3,5",
            id='debvote_grepout_001')
    ]
)
def test_grep_output_for_regexp(cmd_args, inputfile, pattern):
    """Testing debtally using text output from abiftool.py"""
    # TODO: turn this into a generic test function for testing text
    #    output
    try:
        fh = open(inputfile, 'rb')
    except:
        msg = f'Missing file: {inputfile}'
        msg += "Please run './fetchmgr.py *.fetchspec.json' "
        msg += "if you haven't already"
        pytest.skip(msg)
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    LOGOBJ.log(f"LOGOBJ test_grep_... {inputfile=} {pattern=}\n")
    assert check_regex_in_output(cmd_args, inputfile, pattern)
    return None
