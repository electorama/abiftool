import subprocess
import os
import re
import glob
import sys
import pytest

@pytest.mark.parametrize(
    ('abif_file', 'outformat', 'key1', 'subkey1', 'val1'),
    [
        (
            "testdata/tennessee-example/tennessee-example-scores.abif",
            "winlosstiejson",
            "Chat",
            "wins",
            2
        )
    ]
)


def test_json_key_subkey_val(abif_file, outformat, key1, subkey1, val1):
    """Find a whether the abiftool.py parameters are sufficient to generate the specified subset"""
    import json
    try:
        fh = open(abif_file, 'rb')
    except:
        print(f'Missing file: {abif_file}')
        print(
            "Please run './fetchmgr.py *.fetchspec.json' " +
            "if you haven't already")
        sys.exit()

    abiftool_output = \
        subprocess.run(["abiftool.py", "-t", outformat, abif_file],
                       capture_output=True,
                       text=True).stdout
    print(abiftool_output)
    outputdict = json.loads(abiftool_output)
    assert outputdict[key1][subkey1] == val1
