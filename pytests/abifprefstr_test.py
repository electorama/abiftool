import json
import pytest
import re
from subprocess import run, PIPE
from abiftestfuncs import *
from abiflib.core import abiflib_test_log, abiflib_test_logblob, _process_abif_prefline


prefline_test_entries = [
    ('DGM/5 > SBJ/2 >  "蘇業"/1 > AM/0',
     r"蘇業",
     3,
     1,
     ),
    ('[Doña García Márquez]/3, [Steven B. Jensen]/5, [Sue Ye (蘇業)]/3, [Adam Muñoz]/1',
     r"Adam Muñoz",
     3,
     1,
     ),
    ('"Doña #1"/3, [Steven #2]/5, [Sue (蘇) #3]/3, [Adam #4]/1',
     r"Steven #2",
     1,
     5,
     ),
]


@pytest.mark.parametrize(
    'prefstr, candtok, testrank, testrating', prefline_test_entries
)
def test_process_abif_prefline_parse(prefstr, candtok, testrank, testrating):
    jabmod = _process_abif_prefline(0, prefstr)
    assert candtok in jabmod['votelines'][0]['prefs']


@pytest.mark.parametrize(
    'prefstr, candtok, testrank, testrating', prefline_test_entries
)
def test_process_abif_prefline_rank(prefstr, candtok, testrank, testrating):
    jabmod = _process_abif_prefline(0, prefstr)
    jabcandinfo = jabmod['votelines'][0]['prefs'][candtok]
    assert jabmod['votelines'][0]['prefs'][candtok].get('rank') == testrank
    return None


@pytest.mark.parametrize(
    'prefstr, candtok, testrank, testrating', prefline_test_entries
)
def test_process_abif_prefline_rating(prefstr, candtok, testrank, testrating):
    jabmod = _process_abif_prefline(0, prefstr)
    jabcandinfo = jabmod['votelines'][0]['prefs'][candtok]
    jabrat = int(jabmod['votelines'][0]['prefs'][candtok].get('rating'))
    assert jabrat == testrating
    return None

