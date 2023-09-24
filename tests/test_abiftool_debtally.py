import json
import subprocess
import os
import re
import glob
import sys
import pytest

@pytest.mark.parametrize(
    ('outformat', 'debtallyfile', 'key1', 'subkey1', 'val1'),
    [
        (
            "jabmod",
            "testdata/debian-elections/2022/vote_002_tally.txt",
            "metadata",
            "ballotcount",
            354
        )
    ]
)


def test_debtallyfile(outformat, debtallyfile, key1, subkey1, val1):
    """Testing debtally"""
    try:
        fh = open(debtallyfile, 'rb')
    except:
        print(f'Missing file: {debtallyfile}')
        print(
            "Please run './fetchmgr.py *.fetchspec.json' " +
            "if you haven't already")
        sys.exit()

    abiftool_output = \
        subprocess.run(["abiftool.py",
                        "-f", "debtally",
                        "-t", outformat,
                        debtallyfile],
                       capture_output=True,
                       text=True).stdout
    #print(abiftool_output)
    outputdict = json.loads(abiftool_output)
    assert outputdict[key1][subkey1] == val1
