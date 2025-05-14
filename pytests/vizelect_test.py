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
        "pattern":r"Montroll[^\d]+4067",
        "outfmt":"svg",
        "id": "vizelect_001"
    },
    {
        "fetchspec":"vt-burl-2009.preflib.fetchspec.json",
        "filename":"testdata/burl2009/burl2009.abif",
        "pattern":r"\(5 wins, 0 losses, 0 ties\)",
        "outfmt":"dot",
        "id": "vizelect_002"
    }
]

mycols = ('filename', 'pattern', 'outfmt')

pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey(testdict, cols=mycols)
    pytestlist.append(myparam)


@pytest.mark.parametrize(mycols, pytestlist)
def test_pattern_match(filename, pattern, outfmt):
    if not has_lib("graphviz"):
        pytest.skip("Skipping test because 'graphviz' is not installed.")

    fh = open(filename, 'rb')

    texttable_content = \
        subprocess.run([get_abiftool_scriptloc(), "-t", outfmt, filename],
                       capture_output=True,
                       text=True).stdout

    if not re.search(pattern, texttable_content):
        raise AssertionError(
            f"No match for {pattern=} in '{filename}'.\n"
            f"abiftool.py -t {outfmt} {filename}"
        )
