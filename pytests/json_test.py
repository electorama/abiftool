from abiftestfuncs import *
import subprocess
import json
import os
import re
import glob
import sys
import pytest

testdicts=[
    {
        "fetchspec":"tennessee-example.fetchspec.json",
        "filename":"testdata/tenn-example/tennessee-example-scores.abif",
        "outformat":"winlosstiejson",
        "key1":"Chat",
        "subkey1":"wins",
        "val1":2
    }
]

mycols = ('outformat', 'filename', 'key1', 'subkey1', 'val1')
pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey (testdict, cols=mycols)
    pytestlist.append(myparam)

print(f"{pytestlist=}")

@pytest.mark.parametrize(mycols, pytestlist)
def test_json_key_subkey_val(outformat, filename, key1, subkey1, val1):
    """Test equality of subkey to a value"""
    fh = open(filename, 'rb')
    cmd_args = ["-t", outformat, filename]
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    outputdict = json.loads("\n".join(abiftool_output))
    assert outputdict[key1][subkey1] == val1
