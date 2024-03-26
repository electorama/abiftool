#!/usr/bin/env python3
from abiftestfuncs import *

import bs4
import pytest
import sys

###################################################################
# fetchspec -> json file that shows where to download test data from
# options -> the commandline options that should be passed prior to the filename
# filename -> the filename of the file to pass into abiftool
# test_type -> the type of test to perform
# test_cond -> the value to test for

test_list=[
    {
        "fetchspec":"tennessee-example.fetchspec.json",
        "options":["-f", "abif"],
        "filename":"testdata/tenn-example/tennessee-example-scores.abif",
        "test_type": "regex_htmltag",
        "pattern":r"\bNash:68 -- Chat:32\s"
    },
    (
        None,
        ['-t', 'html_snippet', '--modifier', 'svg'],
        'testdata/tenn-example/tennessee-example-simple.abif',
        r"← Knox: 58",
        None
    )
]

# OLD test
#@pytest.mark.parametrize(mycols, pytestlist)
#def test_html_find_element(in_format, filename, element, index, pattern):
#    'cmd_args, inputfile, pattern',
#    [
#        (['-t', 'html_snippet', '--modifier', 'svg'],
#         'testdata/tenn-example/tennessee-example-simple.abif',
#         r"← Knox: 58")
#    ]
#    )


@pytest.mark.parametrize("fetchspec, options, filename, test_type, test_cond", test_list)
def test_abiftool(fetchspec, options, filename, test_type, test_cond):
    pass
#    print(f"{options=} {filename=}")
#    cmd_args = options + [ filename ]
#    output_lines = get_abiftool_output_as_string(cmd_args)
#    assert check_regex_in_output(cmd_args, inputfile, pattern)
