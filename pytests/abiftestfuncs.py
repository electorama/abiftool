# Functions for use in abiftool tests.  The parameter pattern that we're aspiring
# to (as of 2024-03-26):
#
# fetchspec -> json file that shows where to download test data from
# options -> the commandline options that should be passed prior to the filename
# filename -> the filename of the file to pass into abiftool
# test_type -> the type of test to perform
# test_data -> generic data structure passed to the test
#
# html_test.py is the best place to look for guidance on the direction that the
# testing API is heading.

import bs4
import os
import pytest
import re
import subprocess
import sys
from subprocess import run, PIPE
from abiflib import abiflib_test_log

def get_abiftool_output_as_array(cmd_args,
                                 log_pre="",
                                 log_post=""):
    command = ['abiftool.py', *cmd_args]
    commandstr = " ".join(command)
    abiflib_test_log(f"{log_pre}{commandstr}{log_post}")
    completed_process = subprocess.run(command,
                                       stdout=subprocess.PIPE,
                                       text=True)
    retval = completed_process.stdout.splitlines()
    return retval


def get_pytest_param_for_file(testdict):
    this_file = testdict['file']
    this_pattern = testdict['pattern']
    fetchspec = testdict['fetchspec']
    skipmsg = f"Please run 'fetchmgr.py {fetchspec}'"
    return pytest.param(
        this_file,
        this_pattern,
        marks=pytest.mark.skipif(
            not os.path.isfile(this_file),
            reason=f"Missing {this_file=}. {skipmsg}")
    )


def get_pytest_abif_testsubkey(testdict, cols=None):
    if not cols:
        raise
    this_list=[]
    for k in cols:
        this_list.append(testdict[k])
    if 'testdir' in testdict.keys(): 
        dbgmsg = f"{testdict['testdir']=}"
        dbgmsg += f"#{testdict['filename']=}"
        this_file = os.path.join(testdict['testdir'],
                                 testdict['filename'])
    else:
        dbgmsg = f"{testdict['filename']=}"
        this_file = testdict['filename']
    if 'fetchspec' in testdict.keys():
        fetchspec = testdict['fetchspec']
        skipmsg = f"Please run 'fetchmgr.py {fetchspec}'"
    else:
        fetchspec = ""
        skipmsg = f"No fetchspec: {this_file}"
    return pytest.param(
        *this_list,
        marks=pytest.mark.skipif(
            not os.path.isfile(this_file),
            reason=f"Missing {this_file=}. {skipmsg}")
    )


def check_regex_in_textarray(needle, haystack):
    retval = False
    for stackline in haystack:
        retval = re.search(needle, stackline) or retval
    return retval


def check_regex_in_output(cmd_args, inputfile, pattern):
    output_lines = get_abiftool_output_as_array(cmd_args + [inputfile],
                                                log_post=' (check_regex)')
    print(output_lines)
    return check_regex_in_textarray(pattern, output_lines)


def html_element_search(elementname, needle, haystack):
    soup = bs4.BeautifulSoup(haystack, "html.parser")
    elementlist = soup.find_all(elementname)
    elemtextlist = [elem.text for elem in elementlist]
    matchbool = any(re.search(needle, liststr) for liststr in elemtextlist)
    return matchbool

