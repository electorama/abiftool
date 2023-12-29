#!/usr/bin/env python3
from abiftestfuncs import *

import bs4
import pytest
import sys

testdicts=[
    {
        "fetchspec":"tennessee-example.fetchspec.json",
        "in_format":"abif",
        "filename":"testdata/tennessee-example/tennessee-example-scores.abif",
        "element":"tr",
        "index":1,
        "pattern":r"\bNash:68 -- Chat:32\s"
    }
]

mycols = ('in_format', 'filename', 'element', 'index', 'pattern')
pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey (testdict, cols=mycols)
    pytestlist.append(myparam)

print(f"{pytestlist=}")

@pytest.mark.parametrize(mycols, pytestlist)
def test_html_find_element(in_format, filename, element, index, pattern):
    """Test HTML for presence of text in an element"""
    fh = open(filename, 'rb')
    html_from_abiftool = \
        subprocess.run(["abiftool.py",
                        "-f", in_format,
                        "-t", "html", filename],
                       capture_output=True,
                       text=True).stdout
    soup = bs4.BeautifulSoup(html_from_abiftool, "html.parser")
    table_rows = soup.find_all("tr")
    second_table_row = table_rows[index]
    table_row_contents = [td.text for td in second_table_row.find_all(True)]

    haystack = table_row_contents[2]
    assert re.search(pattern, haystack)
