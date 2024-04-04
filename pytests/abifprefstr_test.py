import pytest
import re
from subprocess import run, PIPE
from abiftestfuncs import *

import abiflib.core

@pytest.mark.parametrize(
    'prefstr, outpattern, toknumber',
    [
        ('DGM/5 > SBJ/2 >  "蘇業"/1 > AM/0', r"蘇業", 6),
        ('[Doña García Márquez]/3, [Steven B. Jensen]/5, [Sue Ye (蘇業)]/3, [Adam Muñoz]/1',
         r"Adam Muñoz", 9),
    ]
)
def test_tokenize_abif_prefstr_grep(prefstr, outpattern, toknumber):
    # check_regex_in_textarray(needle, haystack)
    tokdictlist = abiflib.core._tokenize_abif_prefstr(prefstr)
    print(tokdictlist)
    toklist = [list(d.values())[0] for d in tokdictlist]
    print(f"{toklist=}")
    print(f"{toknumber=} (zero indexed)")
    print(f"{toklist[toknumber]=}")

    assert check_regex_in_textarray(outpattern, toklist)
    assert toklist[toknumber] == outpattern
