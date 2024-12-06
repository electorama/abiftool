from abiflib import (
    convert_abif_to_jabmod,
    get_IRV_report,
    IRV_dict_from_jabmod
)
import pathlib
import pytest
import re
from subprocess import run, PIPE
from abiftestfuncs import *


@pytest.mark.parametrize(
    'cmd_args, inputfile, pattern',
    [
        #irv test001
        (['-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-scores.abif',
         r"Chat: 15"),
        #irv test002
        (['-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-STAR.abif',
         r'The IRV winner is Knox'),
        #irv test003
        (['-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-STAR-score-difference.abif',
         r"Knox: 17"),
        #irv test004
        (['-t', 'text', '-m', 'IRV'],
         'testdata/commasep/tn-example-scores-and-commas.abif',
         r"Knox: 58"),
        #irv test005
        (['-t', 'text', '-m', 'IRV'],
         'testdata/burl2009/burl2009.abif',
         r'The IRV winner is Kiss'),
        #irv test006
        # FIXME - There are a number of interpretations of this
        # example.  The abiftool implmementation of IRV/RCV may need
        # to be tweaked to match the popular usage of IRV/RCV.
        (['-f', 'abif', '-t', 'text', '-m', 'IRV'],
        'testdata/commasep/jman722-example.abif',
         r'The IRV winner is Georgie'),
        #irv test007
        (['-f', 'abif', '-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-overvote-02.abif',
         r"Memph: 42"),
        #irv test008
        (['-f', 'abif', '-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-overvote-02.abif',
         r"Total starting votes: 100"),
        #irv test009
        (['-f', 'abif', '-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-overvote-02.abif',
         r"Total counted votes: 83"),
        #irv test010
        (['-f', 'abif', '-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-overvote-02.abif',
         r'Overvotes: 17'),
        #irv test011
        (['-f', 'abif', '-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-overvote-02.abif',
         r'Eliminated this round: Chat, Knox, Nash'),
        #irv test012
        (['-f', 'abif', '-t', 'text', '-m', 'IRV'],
         'testdata/commasep/jman722-example.abif',
         r'Total starting votes: 24'),
        #irv test013
        (['-f', 'abif', '-t', 'text', '-m', 'IRV'],
         'testdata/tenn-example/tennessee-example-irv-tie.abif',
         r'The IRV winners are Knox and Memph'),
        #irv test014
        (['-f', 'abif', '-t', 'irvjson'],
         'testdata/tenn-example/tennessee-example-irv-tie.abif',
         r'Knoxville, TN and Memphis, TN'),
        #irv test015
        (['-f', 'abif', '-t', 'irvjson'],
         'testdata/burl2009/burl2009.abif',
         r'Bob Kiss \(Progressive\)'),
    ]
)
def test_IRV_text_output(cmd_args, inputfile, pattern):
    print(inputfile)
    from pathlib import Path
    print(Path(inputfile).read_text())
    assert check_regex_in_output(cmd_args, inputfile, pattern)


@pytest.mark.parametrize(
    'abif_filename',
    [
        #irv test016
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
