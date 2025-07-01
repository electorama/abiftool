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
        pytest.param(
            ['-t', 'text', '-m', 'IRV'],
            'testdata/mock-elections/tennessee-example-scores.abif',
            r"Chat: 15",
            id='irv_textout_001'),
        #irv test002
        pytest.param(
            ['-t', 'text', '-m', 'IRV'],
            'testdata/mock-elections/tennessee-example-STAR.abif',
            r'The IRV winner is Knox',
            id='irv_textout_002'),
        #irv test003
        pytest.param(
            ['-t', 'text', '-m', 'IRV'],
            'testdata/mock-elections/tennessee-example-STAR-score-difference.abif',
            r"Knox: 17",
            id='irv_textout_003'),
        #irv test004
        pytest.param(
            ['-t', 'text', '-m', 'IRV'],
            'testdata/commasep/tn-example-scores-and-commas.abif',
            r"Knox: 58",
            id='irv_textout_004'),
        #irv test005
        pytest.param(
            ['-t', 'text', '-m', 'IRV'],
            'testdata/burl2009/burl2009.abif',
            r'The IRV winner is Kiss',
            id='irv_textout_005'),
        #irv test006
        # FIXME - There are a number of interpretations of this
        # example.  The abiftool implmementation of IRV/RCV may need
        # to be tweaked to match the popular usage of IRV/RCV.
        pytest.param(
            ['-f', 'abif', '-t', 'text', '-m', 'IRV'],
            'testdata/commasep/jman722-example.abif',
            r'The IRV winner is Georgie',
            id='irv_textout_006'),
        #irv test007
        pytest.param(
            ['-f', 'abif', '-t', 'text', '-m', 'IRV'],
            'testdata/mock-elections/tennessee-example-overvote-02.abif',
            r"Memph: 42",
            id='irv_textout_007'),
        #irv test008
        pytest.param(
            ['-f', 'abif', '-t', 'text', '-m', 'IRV'],
            'testdata/mock-elections/tennessee-example-overvote-02.abif',
            r"Total starting votes: 100",
            id='irv_textout_008'),
        #irv test009
        pytest.param(
            ['-f', 'abif', '-t', 'text', '-m', 'IRV'],
            'testdata/mock-elections/tennessee-example-overvote-02.abif',
            r"Total counted votes: 83",
            id='irv_textout_009'),
        #irv test010
        pytest.param(
        ['-f', 'abif', '-t', 'text', '-m', 'IRV'],
         'testdata/mock-elections/tennessee-example-overvote-02.abif',
            r'Overvotes: 17',
            id='irv_textout_010'),
        #irv test011
        pytest.param(
            ['-f', 'abif', '-t', 'text', '-m', 'IRV'],
            'testdata/mock-elections/tennessee-example-overvote-02.abif',
            r'Eliminated this round: Chat, Knox, Nash',
            id='irv_textout_011'),
        #irv test012
        pytest.param(
            ['-f', 'abif', '-t', 'text', '-m', 'IRV'],
            'testdata/commasep/jman722-example.abif',
            r'Total starting votes: 24',
            id='irv_textout_012'),
        #irv test013
        pytest.param(
        ['-f', 'abif', '-t', 'text', '-m', 'IRV'],
            'testdata/mock-elections/tennessee-example-irv-tie.abif',
            r'The IRV winners are Knox and Memph',
            id='irv_textout_013'),
        #irv test014
        pytest.param(
            ['-f', 'abif', '-t', 'irvjson'],
            'testdata/mock-elections/tennessee-example-irv-tie.abif',
            r'Knoxville, TN and Memphis, TN',
            id='irv_textout_014'),
        #irv test015
        pytest.param(
            ['-f', 'abif', '-t', 'irvjson'],
            'testdata/burl2009/burl2009.abif',
            r'Bob Kiss \(Progressive\)',
            id='irv_textout_015'
        )
    ]
)
def test_IRV_text_output(cmd_args, inputfile, pattern):
    print(inputfile)
    from pathlib import Path
    print(Path(inputfile).read_text())
    assert check_regex_in_output(cmd_args, inputfile, pattern)


@pytest.mark.parametrize(
    'abif_filename',
    ['testdata/mock-elections/tennessee-example-scores.abif'],
    ids=['irv_multicall_001'],
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
