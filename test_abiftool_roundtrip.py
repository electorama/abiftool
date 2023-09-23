import subprocess
import os
import glob
import sys
import pytest

@pytest.mark.parametrize(
    ('abif_file', 'abif_line'),
    [
        ("testdata/electorama-abif/testfiles/potus1980test01.abif",
         "20010:Carter>Anderson>Reagan"),
        ("testdata/electorama-abif/testfiles/test001.abif",
         "7:Georgie/5>Allie/4>Dennis/3=Harold/3>Candace/2>Edith/1>Billy/0=Frank/0")
    ]
)


def test_roundtrip_conversion(abif_file, abif_line):
    try:
        fh = open(abif_file, 'rb')
    except:
        print(f'Missing file: {abif_file}')
        print(
            "Please run './fetchmgr.py *.fetchspec.json' " +
            "if you haven't already")
        sys.exit()

    roundtrip_abif_content = \
        subprocess.run(["abiftool.py", "-t", "abif", abif_file],
                       capture_output=True,
                       text=True).stdout

    assert abif_line in roundtrip_abif_content

