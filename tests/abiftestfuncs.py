import os
import pytest
import re
import subprocess
import sys

def get_pytest_param_for_file(this_file, this_pattern, fetchspec=None):
    skipmsg = f"Please run 'fetchmgr.py {fetchspec}'"
    return pytest.param(
        this_file,
        this_pattern,
        marks=pytest.mark.skipif(
            not os.path.isfile(this_file),
            reason=f"Missing {this_file=}. {skipmsg}")
    )
