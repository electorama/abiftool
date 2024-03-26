# Functions for use in my tests.  The basic architecture of these tests involves
# fetchspec -> json file that shows where to download test data from
# options -> the commandline options that should be passed prior to the filename
# filename -> the filename of the file to pass into abiftool
# html_test.py is the best place to look for guidance on the direction that the
# testing API is heading.

import os
import pytest
import re
import subprocess
import sys
from subprocess import run, PIPE


def get_abiftool_output_as_string(cmd_args):
    command = ['python3', 'abiftool.py', *cmd_args]
    completed_process = subprocess.run(command,
                                       stdout=subprocess.PIPE, text=True)
    retval = completed_process.stdout
    return retval

#def check_regex_in_string(needle, haystack):
#    haystack.readlines
#    retval = False
#    for stackline in haystack:
#        retval = re.search(needle, stackline) or retval
#    return retval
#def check_regex_in_output(cmd_args, inputfile, pattern):
#    cmd_args.append(inputfile)
#    output_lines = get_abiftool_output_as_text_array(cmd_args)
#
#    return check_regex_in_textarray(pattern, output_lines)

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
    command = ['python3', 'abiftool.py', *cmd_args, inputfile]
    completed_process = subprocess.run(command,
                                       stdout=subprocess.PIPE, text=True)

    # Get the captured output and count the lines
    output_lines = completed_process.stdout.splitlines()
    print(output_lines)

    return check_regex_in_textarray(pattern, output_lines)


if False:
    def testme():
        mycols = ('in_format', 'filename', 'element', 'index', 'pattern')
        pytestlist = []
        for testdict in testdicts:
            myparam = get_pytest_abif_testsubkey (testdict, cols=mycols)
            pytestlist.append(myparam)

        print(f"{pytestlist=}")

def html_element_search(elementname, needle, haystack):
    soup = bs4.BeautifulSoup(html_from_abiftool, "html.parser")
    table_rows = soup.find_all(elementname)
    test_this_table_row = table_rows[index]
    table_row_contents = [td.text for td in test_this_table_row.find_all(True)]
    print(f"{table_rows=}")

    haystack = table_row_contents[5]
    assert re.search(pattern, haystack)


    """Test HTML for presence of text in an element"""
    fh = open(filename, 'rb')
    html_from_abiftool = \
        subprocess.run(["abiftool.py",
                        "-f", in_format,
                        "-t", "html", filename],
                       capture_output=True,
                       text=True).stdout
