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
            "testdir": "testdata/preflib/vt-burlington-2009-preflib/",
            "filename": "burl2009-00005-00000002.toc",
            "key1": "metadata",
            "subkey1": "ballotcount",
            "val1": 8980
        },
        {
            "fetchspec": "vt-burl-2009.preflib.fetchspec.json",
            "outformat":"paircountjson",
            "testdir": "testdata/preflib/vt-burlington-2009-preflib/",
            "filename": "burl2009-00005-00000002.toc",
            "key1": "AndyMontroll",
            "subkey1": "BobKiss",
            "val1": 4067
        },
        {
            "fetchspec": "vt-burl-2009.preflib.fetchspec.json",
            "outformat": "jabmod",
            "testdir": "testdata/preflib/vt-burlington-2009-preflib/",
            "filename": "burl2009-00005-00000002.toi",
            "key1": "metadata",
            "subkey1": "ballotcount",
            "val1": 8980
        },
        {
            "fetchspec": "vt-burl-2009.preflib.fetchspec.json",
            "outformat": "paircountjson",
            "testdir": "testdata/preflib/vt-burlington-2009-preflib/",
            "filename": "burl2009-00005-00000002.toi",
            "key1": "AndyMontroll",
            "subkey1": "BobKiss",
            "val1": 4067
        },
        {
            "fetchspec": "debian-elections.preflib.fetchspec.json",
            "outformat": "jabmod",
            "testdir": "testdata/preflib/debian-2003/",
            "filename": "dpl-00002-00000002.toc",
            "key1": "metadata",
            "subkey1": "ballotcount",
            "val1": 488
        },
        {
            "fetchspec": "debian-elections.preflib.fetchspec.json",
            "outformat": "paircountjson",
            "testdir": "testdata/preflib/debian-2003/",
            "filename": "dpl-00002-00000002.toc",
            "key1": "MartinMichlmayr",
            "subkey1": "BdaleGarbee",
            "val1": 228
        },
        {
            "fetchspec": "debian-elections.preflib.fetchspec.json",
            "outformat": "jabmod",
            "testdir": "testdata/preflib/debian-2003/",
            "filename": "dpl-00002-00000002.soi",
            "key1": "metadata",
            "subkey1": "ballotcount",
            "val1": 488
        },
        {
            "fetchspec": "debian-elections.preflib.fetchspec.json",
            "outformat": "paircountjson",
            "testdir": "testdata/preflib/debian-2003/",
            "filename": "dpl-00002-00000002.soi",
            "key1": "MartinMichlmayr",
            "subkey1": "BdaleGarbee",
            "val1": 228
        }
    ]


mycols = ['outformat', 'testdir', 'filename', 'key1', 'subkey1', 'val1']
pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey(testdict, cols=mycols)
    pytestlist.append(myparam)

@pytest.mark.parametrize(mycols, pytestlist)
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

    abiftool_output = \
        subprocess.run(["abiftool.py",
                        "-f", "preflib",
                        "-t", outformat,
                        thisfilename],
                       capture_output=True,
                       text=True).stdout
    #print(abiftool_output)
    outputdict = json.loads(abiftool_output)
    assert outputdict[key1][subkey1] == val1
