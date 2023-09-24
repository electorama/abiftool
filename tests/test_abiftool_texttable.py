import subprocess
import os
import re
import glob
import sys
import pytest

@pytest.mark.parametrize(
    ('abif_file', 'pattern'),
    [
        ("testdata/burl2009/burl2009.abif",
         r"Montroll[^\d]+2708")
    ]
)


def test_roundtrip_conversion(abif_file, pattern):
    try:
        fh = open(abif_file, 'rb')
    except:
        print(f'Missing file: {abif_file}')
        print(
            "Please run './fetchmgr.py *.fetchspec.json' " +
            "if you haven't already")
        sys.exit()

    texttable_content = \
        subprocess.run(["abiftool.py", "-t", "texttable", abif_file],
                       capture_output=True,
                       text=True).stdout

    if not re.search(pattern, texttable_content):
        raise AssertionError(
            f"No match for {pattern=} in '{abif_file}'.")
