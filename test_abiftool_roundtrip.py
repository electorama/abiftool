import subprocess
import os
import glob

def test_roundtrip_conversion():
    #abif_files = glob.glob("*.abif")  # Get a list of all *.abif files in the directory
    abif_files = [
        "testdata/abif_testsuite/potus1980test01.abif",
        "testdata/abif_testsuite/potus1980test01.abif"
        ]
    # next one to try: "testdata/abif_testsuite/test001.abif"

    for abif_file in abif_files:
        # Convert abif to jabmod
        jabmod_content = subprocess.run(["abiftool.py", "-t", "jabmod", abif_file], capture_output=True, text=True).stdout

        # Convert jabmod back to abif after roundtrip
        roundtrip_abif_content = subprocess.run(["abiftool.py",
                                                 "-f", "jabmod",
                                                 "-t", "abif", "-"
                                                 ], capture_output=True,
                                                text=True, input=jabmod_content).stdout
        assert "20010:Carter>Anderson>Reagan" in roundtrip_abif_content

