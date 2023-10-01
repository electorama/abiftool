import json
import subprocess
import os
import re
import glob
import sys
import pytest

@pytest.mark.parametrize(
    ('outformat',
     'preflibtestdir',
     'preflibfile',
     'key1', 'subkey1', 'val1'),
    [
        (
            "jabmod",
            "testdata/preflib/vt-burlington-2009-preflib/",
            "burl2009-00005-00000002.toc",
            "metadata",
            "ballotcount",
            8980
        ),
        (
            "paircountjson",
            "testdata/preflib/vt-burlington-2009-preflib/",
            "burl2009-00005-00000002.toc",
            "AndyMontroll",
            "BobKiss",
            4067
        ),
        (
            "jabmod",
            "testdata/preflib/vt-burlington-2009-preflib/",
            "burl2009-00005-00000002.toi",
            "metadata",
            "ballotcount",
            8980
        ),
        (
            "paircountjson",
            "testdata/preflib/vt-burlington-2009-preflib/",
            "burl2009-00005-00000002.toi",
            "AndyMontroll",
            "BobKiss",
            4067
        ),
        (
            "jabmod",
            "testdata/preflib/debian-2003/",
            "dpl-00002-00000002.toc",
            "metadata",
            "ballotcount",
            488
        ),
        (
            "paircountjson",
            "testdata/preflib/debian-2003/",
            "dpl-00002-00000002.toc",
            "MartinMichlmayr",
            "BdaleGarbee",
            228
        ),
        (
            "jabmod",
            "testdata/preflib/debian-2003/",
            "dpl-00002-00000002.soi",
            "metadata",
            "ballotcount",
            488
        ),
        (
            "paircountjson",
            "testdata/preflib/debian-2003/",
            "dpl-00002-00000002.soi",
            "MartinMichlmayr",
            "BdaleGarbee",
            228
        )
    ]
)

def test_preflib_file(outformat,
                      preflibtestdir,
                      preflibfile,
                      key1, subkey1, val1):
    """Testing preflib"""
    thisfilename=os.path.join(preflibtestdir, preflibfile)
    try:
        fh = open(thisfilename, 'rb')
    except:
        print(f"{thisfilename=}")
        print(f"{preflibtestdir=}")
        print(f"{preflibfile=}")
        print(f'Missing file: {preflibfile}')
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
