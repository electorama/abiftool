import os
import pytest
import re
import subprocess
import sys
from subprocess import run, PIPE


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
