import subprocess
import os
import glob
import sys

def test_roundtrip_conversion():
    abif_files = [
        ("testdata/electorama-abif/testfiles/potus1980test01.abif",
         "20010:Carter>Anderson>Reagan"),
        ("testdata/electorama-abif/testfiles/test001.abif",
         "7:Georgie/5>Allie/4>Dennis/3=Harold/3>Candace/2>Edith/1>Billy/0=Frank/0")
        ]

    for (fn, abstr) in abif_files:
        try:
            fh = open(fn, 'rb')
        except:
            print(f'Missing file: {fn}')
            print(
                "Please run './repomgr.py *.repospec.json' " +
                "if you haven't already")
            sys.exit()

    ##########################
    for (fn, abstr) in abif_files:
        # Convert abif to jabmod
        jabmod_content = subprocess.run(["abiftool.py", "-t", "jabmod", fn],
                                        capture_output=True,
                                        text=True).stdout

        # Convert jabmod back to abif after roundtrip
        roundtrip_abif_content = subprocess.run(["abiftool.py",
                                                 "-f", "jabmod",
                                                 "-t", "abif", "-"
                                                 ], capture_output=True,
                                                text=True, input=jabmod_content).stdout
        assert abstr in roundtrip_abif_content

