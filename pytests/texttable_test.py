from abiftestfuncs import *
import os
import pytest
import re
import subprocess
import sys

testdicts = [
    {
        "fetchspec":"vt-burl-2009.preflib.fetchspec.json",
        "filename":"testdata/burl2009/burl2009.abif",
        "pattern":r"Copeland Winner: Andy Montroll",
        "options": ["-t", "text"],
        "id": "texttable_001"
    },
    {
        "fetchspec":"vt-burl-2009.preflib.fetchspec.json",
        "filename":"testdata/burl2009/burl2009.abif",
        "pattern":r"Montroll",
        "options": ["-t", "text", "-m", "winlosstie", "-m", "score"],
        "id": "texttable_002"
    },
    {
        "fetchspec":"vt-burl-2009.preflib.fetchspec.json",
        "filename":"testdata/burl2009/burl2009.abif",
        "pattern":r"Montroll \(5-0-0\)",
        "options": ["-t", "text"],
        "id": "texttable_003"
    }
]

mycols = ('filename', 'pattern', 'options')

pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey(testdict, cols=mycols)
    pytestlist.append(myparam)


@pytest.mark.parametrize(mycols, pytestlist)
def test_pattern_match(filename, pattern, options):
    if not has_lib("texttable"):
        pytest.skip("Skipping test because 'texttable' is not installed.")

    fh = open(filename, 'rb')

    texttable_content = \
        subprocess.run([get_abiftool_scriptloc(), *options, filename],
                       capture_output=True,
                       text=True).stdout

    if not re.search(pattern, texttable_content):
        print(f"{pattern=}")
        print("texttable_content:")
        print(texttable_content)
        raise AssertionError(
            f"No match for {pattern=} in '{filename}'.\n"
            f"abiftool.py {' '.join(options)} {filename}"
        )
