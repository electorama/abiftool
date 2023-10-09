from abiftestfuncs import *
import os
import pytest
import re
import subprocess
import sys

testdicts = [
    {
        "fetchspec":"vt-burl-2009.preflib.fetchspec.json",
        "file":"testdata/burl2009/burl2009.abif",
        "pattern":r"Montroll[^\d]+4067"
    }
]

pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_param_for_file(testdict)
    pytestlist.append(myparam)


testcolnames = ('abif_file', 'pattern')
@pytest.mark.parametrize(testcolnames, pytestlist)
def test_roundtrip_conversion(abif_file, pattern):
    fh = open(abif_file, 'rb')

    texttable_content = \
        subprocess.run(["abiftool.py", "-t", "texttable", abif_file],
                       capture_output=True,
                       text=True).stdout

    if not re.search(pattern, texttable_content):
        raise AssertionError(
            f"No match for {pattern=} in '{abif_file}'.")
