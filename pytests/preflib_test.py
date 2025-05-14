from abiftestfuncs import *
import json
import os
import pytest
import re
import glob
import subprocess
import sys

testdicts = [
        {
            "fetchspec": "vt-burl-2009.preflib.fetchspec.json",
            "outformat": "jabmod",
            "testdir": "downloads/preflib/",
            "filename": "burl2009-00005-00000002.toc",
            "key1": "metadata",
            "subkey1": "ballotcount",
            "val1": 8980,
            "id": "preflib_001"
        },
        {
            "fetchspec": "vt-burl-2009.preflib.fetchspec.json",
            "outformat":"paircountjson",
            "testdir": "downloads/preflib/",
            "filename": "burl2009-00005-00000002.toc",
            "key1": "AndyMontroll",
            "subkey1": "BobKiss",
            "val1": 4067,
            "id": "preflib_002"
        },
        {
            "fetchspec": "vt-burl-2009.preflib.fetchspec.json",
            "outformat": "jabmod",
            "testdir": "downloads/preflib/",
            "filename": "burl2009-00005-00000002.toi",
            "key1": "metadata",
            "subkey1": "ballotcount",
            "val1": 8980,
            "id": "preflib_003"
        },
        {
            "fetchspec": "vt-burl-2009.preflib.fetchspec.json",
            "outformat": "paircountjson",
            "testdir": "downloads/preflib/",
            "filename": "burl2009-00005-00000002.toi",
            "key1": "AndyMontroll",
            "subkey1": "BobKiss",
            "val1": 4067,
            "id": "preflib_004"
        },
        {
            "fetchspec": "debian-elections.preflib.fetchspec.json",
            "outformat": "jabmod",
            "testdir": "downloads/preflib/",
            "filename": "dpl-00002-00000002.toc",
            "key1": "metadata",
            "subkey1": "ballotcount",
            "val1": 488,
            "id": "preflib_005"
        },
        {
            "fetchspec": "debian-elections.preflib.fetchspec.json",
            "outformat": "paircountjson",
            "testdir": "downloads/preflib/",
            "filename": "dpl-00002-00000002.toc",
            "key1": "MartinMichlmayr",
            "subkey1": "BdaleGarbee",
            "val1": 228,
            "id": "preflib_006"
        },
        {
            "fetchspec": "debian-elections.preflib.fetchspec.json",
            "outformat": "jabmod",
            "testdir": "downloads/preflib/",
            "filename": "dpl-00002-00000002.soi",
            "key1": "metadata",
            "subkey1": "ballotcount",
            "val1": 488,
            "id": "preflib_007"
        },
        {
            "fetchspec": "debian-elections.preflib.fetchspec.json",
            "outformat": "paircountjson",
            "testdir": "downloads/preflib/",
            "filename": "dpl-00002-00000002.soi",
            "key1": "MartinMichlmayr",
            "subkey1": "BdaleGarbee",
            "val1": 228,
            "id": "preflib_008"
        }
    ]


mycols = ['outformat', 'testdir', 'filename', 'key1', 'subkey1', 'val1']
pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey(testdict, cols=mycols)
    pytestlist.append(myparam)

@pytest.mark.parametrize(mycols, pytestlist, ids=lambda x: x["id"])
def test_preflib_file(outformat,
                      testdir,
                      filename,
                      key1, subkey1, val1):
    """Testing preflib"""
    thisfilename=os.path.join(testdir, filename)
    try:
        fh = open(thisfilename, 'rb')
    except:
        print(f"{thisfilename=}")
        print(f"{testdir=}")
        print(f"{filename=}")
        print(f'Missing file: {filename}')
        print(
            "Please run './fetchmgr.py *.fetchspec.json' " +
            "if you haven't already")
        sys.exit()

    cmd_args = ["-f", "preflib", "-t", outformat, thisfilename]
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    outputdict = json.loads("\n".join(abiftool_output))
    assert outputdict[key1][subkey1] == val1
