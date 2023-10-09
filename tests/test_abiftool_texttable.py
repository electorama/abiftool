from abiftestfuncs import *
import os
import pytest
import re
import subprocess
import sys

testgrid = [
    [
        "testdata/burl2009/burl2009.abif",
        r"Montroll[^\d]+4067",
        "vt-burl-2009.preflib.fetchspec.json"
    ]
]

testlist = []
for testrow in testgrid:
    myparam = get_pytest_param_for_file(
        testrow[0], testrow[1], fetchspec=testrow[2])
    testlist.append(myparam)


testcolnames = ('abif_file', 'pattern')
@pytest.mark.parametrize(testcolnames, testlist)
def test_roundtrip_conversion(abif_file, pattern):
    fh = open(abif_file, 'rb')

    texttable_content = \
        subprocess.run(["abiftool.py", "-t", "texttable", abif_file],
                       capture_output=True,
                       text=True).stdout

    if not re.search(pattern, texttable_content):
        raise AssertionError(
            f"No match for {pattern=} in '{abif_file}'.")
