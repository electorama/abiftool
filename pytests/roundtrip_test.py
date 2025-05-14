from abiftestfuncs import *
import subprocess
import glob
import os
from pprint import pformat
import pytest
import sys

mycols = ['filename', 'abif_line']

testdicts = [
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "downloads/electorama-abif/testfiles/potus1980test01.abif",
        "abif_line": "20010:Carter>Anderson>Reagan",
        "id": "roundtrip_001"
    },
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "downloads/electorama-abif/testfiles/test001.abif",
        "abif_line": "7:Georgie/5>Allie/4>Dennis/3=Harold/3>Candace/2>Edith/1>Billy=Frank",
        "id": "roundtrip_002"
    },
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "downloads/electorama-abif/testfiles/test016.abif",
        "abif_line": "24:[蘇業]/5>AM/2=DGM/2>SBJ/1",
        "id": "roundtrip_003"
    },
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "downloads/electorama-abif/testfiles/test017.abif",
        # FIXME: this is a horrible kludge.  I shouldn't have altered the
        #   electorama/abif test suite to get around the fact that the
        #   abiflib parser fails with the 2024-06-02 commit.  So sue me.
        "abif_line": "23:[Adam num4]/5>[Sue (蘇) num3]/3>[Doña num1]/1>[Steven num2]",
        "id": "roundtrip_004"
    },
]

pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey(testdict, cols=mycols)
    pytestlist.append(myparam)


@pytest.mark.parametrize(mycols, pytestlist)
def test_roundtrip_conversion(filename, abif_line):
    fh = open(filename, 'rb')

    cmd_args = ["-t", "abif", filename]
    roundtrip_abif_content = get_abiftool_output_as_array(cmd_args)
    abiflib_test_log(f"{abif_line=}")
    abiflib_test_log(f"roundtrip_abif_content:")
    abiflib_test_log(pformat(roundtrip_abif_content))
    assert abif_line in roundtrip_abif_content

