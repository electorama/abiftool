import pathlib
import pytest
import re
from subprocess import run, PIPE
from abiftestfuncs import *

@pytest.mark.parametrize(
    'cmd_args, inputfile, pattern',
    [
        (['-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-scores.abif',
         r"Chat: 15"),
        (['-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-STAR.abif',
         r"The IRV winner is Knox"),
        (['-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"Knox: 17"),
        (['-t', 'text', '-m', 'IRV'],
         'testdata/commasep/tn-example-scores-and-commas.abif',
         r"Knox: 58"),
        (['-t', 'text', '-m', 'IRV'],
         'testdata/burl2009/burl2009.abif',
         r"The IRV winner is Kiss"),
    ]
)

def test_IRV_text_output(cmd_args, inputfile, pattern):
    print(inputfile)
    from pathlib import Path
    print(Path(inputfile).read_text())
    assert check_regex_in_output(cmd_args, inputfile, pattern)


from abiflib import (
    convert_abif_to_jabmod,
    get_IRV_report,
    IRV_dict_from_jabmod
    )


@pytest.mark.parametrize(
    'abif_filename',
    [
        'testdata/tenn-example/tennessee-example-scores.abif'
    ]
)
def test_IRV_multiple_calls(abif_filename):
    abiftext = pathlib.Path(abif_filename).read_text()
    jabmod = convert_abif_to_jabmod(abiftext)
    call001 = IRV_dict_from_jabmod(jabmod)
    call002 = IRV_dict_from_jabmod(jabmod)
    outstr = f"{len(call001['rounds'])=}\n"
    outstr += f"{len(call002['rounds'])=}\n"
    abiflib_test_log(outstr)

    assert len(call001['rounds']) == len(call002['rounds'])
