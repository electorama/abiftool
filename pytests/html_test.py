#!/usr/bin/env python3
from abiftestfuncs import *

import pytest
import sys

###################################################################
# fetchspec -> json file that shows where to download test data from
# options -> the commandline options that should be passed prior to the filename
# filename -> the filename of the file to pass into abiftool
# test_type -> the type of test to perform
# test_data -> generic data structure passed to the test

test_list=[
    pytest.param(
        {
            "fetchspec":"tennessee-example.fetchspec.json",
            "options":["-f", "abif", "-t", "html"],
            "filename":"testdata/mock-elections/tennessee-example-scores.abif",
            "test_type": "regex_htmltag",
            "test_data": {"tag": "tr",
                          "pattern": r"Nash: 68"}
        },
        id='html_001'),
    pytest.param(
        {
            "fetchspec":None,
            "options":['-t', 'html_snippet', '--modifier', 'svg'],
            "filename":'testdata/mock-elections/tennessee-example-simple.abif',
            "test_type":"regex",
            "test_data":r"← Knox: 58"
        },
        id='html_002'),
]


@pytest.mark.parametrize("test_case", test_list)
def test_abiftool(test_case):
    optstr = " ".join(test_case['options'])
    if 'svg' in test_case['options'] and not has_lib("graphviz"):
        pytest.skip("Skipping test because 'graphviz' is not installed.")

    fnstr = test_case['filename']
    testfilearray = get_abiftool_output_as_array(test_case['options'] +
                                                 [ test_case['filename'] ])
    testfilestr = str(testfilearray)
    testval = None
    if(test_case['test_type'] == 'regex_htmltag'):
        tdata = test_case['test_data']
        testval = html_element_search(tdata['tag'],
                                      tdata['pattern'],
                                      testfilestr)
    elif(test_case['test_type'] == 'regex'):
        testval = re.search(test_case['test_data'], testfilestr)
    assert bool(testval)
