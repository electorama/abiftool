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
    {
        "fetchspec":"tennessee-example.fetchspec.json",
        "options":["-f", "abif", "-t", "html"],
        "filename":"testdata/tenn-example/tennessee-example-scores.abif",
        "test_type": "regex_htmltag",
        "test_data": {"tag": "tr",
                      "pattern": r"\bNash:68\W{1,5}Chat:32\s"}
    },
    {
        "fetchspec":None,
        "options":['-t', 'html_snippet', '--modifier', 'svg'],
        "filename":'testdata/tenn-example/tennessee-example-simple.abif',
        "test_type":"regex",
        "test_data":r"← Knox: 58"
    }
]


@pytest.mark.parametrize("test_case", test_list)
def test_abiftool(test_case):
    launchstr = "abiftool.py"
    optstr = " ".join(test_case['options'])
    fnstr = test_case['filename']
    print(f"{launchstr} {optstr} {fnstr}")
    testfilestr = get_abiftool_output_as_string(test_case['options'] +
                                                [ test_case['filename'] ])
    testval = None
    if(test_case['test_type'] == 'regex_htmltag'):
        tdata = test_case['test_data']
        testval = html_element_search(tdata['tag'],
                                      tdata['pattern'],
                                      testfilestr)
    elif(test_case['test_type'] == 'regex'):
        testval = re.search(test_case['test_data'], testfilestr)
    print(f"{testval=} {test_case['test_data']=} {testfilestr=}")
    assert bool(testval)
