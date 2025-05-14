from abiftestfuncs import *
import abiflib
import pytest
import re
from subprocess import run, PIPE

LOGOBJ = abiflib.LogfileSingleton()

@pytest.mark.parametrize(
    'cmd_args, inputfiles, pattern',
    [
        (['-f', 'sftxt', '-t', 'abif', '-m', 'consolidate'],
         ['downloads/california/20180627_masterlookup.txt',
          'downloads/california/20180627_ballotimage.txt'],
         r"11937:LONDON_BREED>MARK_LENO>JANE_KIM"),
    ],
    ids=['sftxt_001']
)

def test_grep_output_for_regexp(cmd_args, inputfiles, pattern):
    """Testing text output from abiftool.py for regexp"""
    for inf in inputfiles:
        try:
            fh = open(inf, 'rb')
        except:
            msg = f'Missing file: {inf}'
            msg += ". Please run './fetchmgr.py sf-elections.fetchspec.json' "
            msg += "to get SF election data for this test."
            pytest.skip(msg)
    output_lines = get_abiftool_output_as_array(cmd_args + inputfiles,
                                                log_post=' (check_regex)')
    assert check_regex_in_textarray(pattern, output_lines)
    return None
