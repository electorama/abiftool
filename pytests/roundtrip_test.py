from abiftestfuncs import *
import subprocess
import os
import glob
import sys
import pytest

mycols = ['filename', 'abif_line']

testdicts = [
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "localabif/electorama-abif/potus1980test01.abif",
        "abif_line": "20010:Carter>Anderson>Reagan"
    },
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "localabif/electorama-abif/test001.abif",
        "abif_line": "7:Georgie/5>Allie/4>Dennis/3=Harold/3>Candace/2>Edith/1>Billy/0=Frank/0"
    }
]

pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey(testdict, cols=mycols)
    pytestlist.append(myparam)


@pytest.mark.parametrize(mycols, pytestlist)
def test_roundtrip_conversion(filename, abif_line):
    fh = open(filename, 'rb')

    roundtrip_abif_content = \
        subprocess.run(["abiftool.py", "-t", "abif", filename],
                       capture_output=True,
                       text=True).stdout

    assert abif_line in roundtrip_abif_content

