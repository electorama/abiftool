from abiftestfuncs import *
import subprocess
import json
import os
import re
import glob
import sys
import pytest


testlist = [
    # TEST 001:
    # Test the '-t winlosstiejson' parameter with the simplified TN example
    pytest.param(
        ['-f', 'abif', '-t', 'winlosstiejson'],
        'testdata/tenn-example/tennessee-example-simple.abif',
        'is_equal',
        ["Chat", "wins"],
        2,
        id='json_001'
    ),
    # TEST 002:
    # Test the '-t jabmod' parameter with the simplified TN example
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/tenn-example/tennessee-example-simple.abif',
        'is_equal',
        ["votelines", 0, "qty"],
        42,
        id='json_002'
    ),
    # TEST 003:
    # Test roundtripping jabmod with a mock election example
    pytest.param(
        ['-f', 'jabmod', '-t', 'jabmod'],
        'testdata/california/simple001-example.jabmod.json',
        'is_equal',
        ["votelines", 0, "qty"],
        1,
        id='json_003'
    ),
    # TEST 004:
    # Test roundtripping jabmod with a mock election example,
    # consolidating the results
    pytest.param(
        ['-f', 'jabmod', '-t', 'jabmod', '-m', 'consolidate'],
        'testdata/california/simple001-example.jabmod.json',
        'is_equal',
        ["votelines", 0, "qty"],
        5,
        id='json_004'
    ),
    # TEST 005:
    # Test IRV with the SF 2018 special election, checking if the winner
    # is correct
    pytest.param(
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
        'is_equal',
        ["roundmeta", -1, "winner"],
        ["LONDON_BREED"],
        id='json_005'
    ),
    # TEST 006:
    # Test IRV with the SF 2018 special election, checking for eliminated
    # candidates
    pytest.param(
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
        'is_equal',
        ["roundmeta", -1, "eliminated"],
        ["MARK_LENO"],
        id='json_006'
    ),
    # TEST 007:
    # Test IRV with the SF 2018 special election, checking for starting
    # quantity of votes
    pytest.param(
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
        'is_equal',
        ["roundmeta", -1, "startingqty"],
        254016,
        id='json_007'
    ),
    # TEST 008:
    # Test IRV with the SF 2018 special election, checking the final count
    # of votes for the winner
    #
    # FIXME - the report from the city says Breed won with 115977 in the final round, but my
    # count shows 116020
    # 
    # SF Report:
    #  https://www.sfelections.org/results/20180605/data/20180627/mayor/20180627_mayor.pdf
    pytest.param(
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
        'is_equal',
        ["rounds", -1, "LONDON_BREED"],
        116020,
        id='json_008'
    ),
    # TEST 009:
    # Test IRV with the SF 2018 special election, checking if a WRITE_IN
    # candidate is present. 
    pytest.param(
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/california/sf2018special-results.abif',
        'is_equal',
        ["roundmeta", 0, "eliminated", 3],
        r'WRITE_IN',
        id='json_009'
    ),
    # TEST 010:
    # Test IRV with a mock election, checking if it uses 14 rounds as
    # expected.
    pytest.param(
        ['-f', 'abif', '-t', 'irvjson'],
        'testdata/mock-elections/mock-twotie.abif',
        'contains',
        ["roundmeta", 13, "all_eliminated"],
        r'F',
        id='json_010'
    ),
    # TEST 011:
    # Testing whether an Alaska election has 4 candidates
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'localabif/bolson-nameq/votedata-2024-01-27/2022-08-16_Alaska-U.S._Representative_(Special_General).abif',
        'length',
        ["candidates"],
        4,
        id='json_011'
    ),
    # TEST 012:
    # Test the '-t paircountjson' parameter
    pytest.param(
        ['-f', 'abif', '-t', 'paircountjson'],
        'testdata/commasep/commasquare.abif',
        'is_equal',
        ["A,X", "B,Y"],
        12,
        id='json_012'
    ),
    # TEST 013:
    # FIXME: figure out what this test is supposed to be checking
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/commasep/commasquare.abif',
        'is_equal',
        ["votelines", 0, "prefs", "C,Z", "rank"],
        3,
        id='json_013'
    ),
    # TEST 014:
    # Test the deprecated '-t paircountjson' parameter, which will be
    # replaced by the "-t json -m pairwise" combo
    pytest.param(['-f', 'abif', '-t', 'paircountjson'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["Chat", "Knox"],
                 83,
                 id='json_014'),
    # TEST 015:
    # Test the "-t json -m pairwise" combo
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'pairwise'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["Chat", "Knox"],
                 83,
                 id='json_015'),
    # TEST 016:
    # Test the deprecated '-t irvjson' parameter, which will be
    # replaced by "-t json -m IRV" combo
    pytest.param(['-f', 'abif', '-t', 'irvjson'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["winner", 0],
                 "Knox",
                 id='json_016'),
    # TEST 017:
    # Test the "-t json -m IRV" combo
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'IRV'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["winner", 0],
                 "Knox",
                 id='json_017'),
    # TEST 018:
    # Test the "-t json -m FPTP" combo wth simplified TN example
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'FPTP'],
                 'testdata/mock-elections/tennessee-example-simple.abif',
                 'is_equal',
                 ["winners", 0],
                 "Memph",
                 id='json_018'),
    # TEST 019:
    # Test the "-t json -m FPTP" combo with a tie election
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'FPTP'],
                 'testdata/mock-elections/mock-tie.abif',
                 'is_equal',
                 ["winners", 1],
                 "S",
                 id='json_019'),
    # TEST 020:
    # Test that whitespace in quoted tokens is handled properly
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'localabif/bolson-nameq/votedata-2024-01-27/2022-08-16_Alaska-U.S._Representative_(Special_General).abif',
                 'is_equal',
                 ["candidates", "Begich, Nick"],
                 "Begich, Nick",
                 id='json_020'),
    # TEST 021:
    # Test that blank abif prefstrs are parsed and reported
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/mock-elections/tennessee-example-blank-prefstr.abif',
                 'is_equal',
                 ["votelines", 0, "prefstr"],
                 "",
                 id='json_021'),
    # TEST 022:
    # Test that embedded quotes are allowed within square brackets
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/mock-elections/tennessee-example-nested-quote.abif',
                 'is_equal',
                 ["votelines", 0, "prefs", "\"Memph\" Memphis", "rating"],
                 5,
                 id='json_022'),
    # TEST 023:
    # Test the way that ABIF files with nothing but blanks still counts the ballots
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/mock-elections/mock-all-blank.abif',
                 'is_equal',
                 ["metadata", "ballotcount"],
                 100,
                 id='json_023'),
    # TEST 024:
    # Test the way that ABIF files with nothing but blanks still counts the ballots
    pytest.param(['-f', 'abif', '-t', 'json', '-m', 'FPTP'],
                 'testdata/mock-elections/mock-all-blank.abif',
                 'is_equal',
                 ["winners"],
                 [],
                 id='json_024'),
    # TEST 025:
    # Test empty ABIF input string
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/empty.abif',
                 'is_equal',
                 ['metadata', 'ballotcount'],
                 0,
                 id='json_025'),
    # TEST 026:
    # Test ABIF with one voteline and one cand no newline
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/one-A.abif',
                 'is_equal',
                 ['metadata', 'ballotcount'],
                 1,
                 id='json_026'),
    # TEST 027:
    # Test ABIF with one voteline and one cand with newline
    pytest.param(['-f', 'abif', '-t', 'jabmod'],
                 'testdata/questionable/one-A-LF.abif',
                 'is_equal',
                 ['metadata', 'ballotcount'],
                 1,
                 id='json_027'),
    # TEST 028:
    # Test parsing of the Tennessee example in SF CVR format
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '1',
         '-t', 'jabmod'
        ],
        None,
        'is_equal',
        ["metadata", "ballotcount"],
        100,
        id='json_028'
    ),

    # TEST 029:
    # Test parsing of the Tennessee example in SF CVR format - specific voteline rank
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '1',
         '-t', 'jabmod'
        ],
        None,
        'is_equal',
        ["votelines", 0, "prefs", "Memph", "rank"],
        1,
        id='json_029'
    ),
    # TEST 030:
    # Make sure that we have 100 ballots on race #2 of the sample zipfile
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '2',
         '-t', 'jabmod'
        ],
        None,
        'is_equal',
        ["metadata", "ballotcount"],
        100,
        id='json_030'
    ),
    # TEST 031:
    # Make sure that Jackson shows up in race #2 in the sample zipfile
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '2',
         '-t', 'jabmod'
        ],
        None,
        'is_equal',
        ["votelines", 0, "prefs", "Jackson", "rank"],
        1,
        id='json_031'
    ),
    # TEST 032:
    # Make sure Memph has 42 first-place votes in race #1 in the sample zipfile
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '1',
         '-t', 'jabmod',
         '-m', 'consolidate'
        ],
        None,
        'is_equal',
        ["votelines", 0, "qty"],
        42,
        id='json_032'
    ),
    # TEST 033:
    # Ensure Murfreesboro has 26 first-place votes in race #1 in the sample zipfile
    pytest.param(
        ['-f', 'sfjson',
         '--container', 'testdata/mock-elections/tennessee-example-sfjson-cvr.zip',
         '--contestid', '2',
         '-t', 'jabmod',
         '-m', 'consolidate'
        ],
        None,
        'is_equal',
        ["votelines", 1, "qty"],
        26,
        id='json_033'
    )
]

@pytest.mark.parametrize(
    'cmd_args, inputfile, testtype, keylist, value', testlist
)
def test_json_key_subkey_val(cmd_args, inputfile, testtype, keylist, value):
    """Test equality of subkey to a value"""
    if inputfile:
        try:
            fh = open(inputfile, 'rb')
            fh.close()
        except:
            msg = f'Missing file: {inputfile}'
            msg += "Please run './fetchmgr.py *.fetchspec.json' "
            msg += "if you haven't already"
            pytest.skip(msg)
        cmd_args.append(inputfile)
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    outputdict = json.loads("\n".join(abiftool_output))

    if testtype == 'is_equal':
        assert get_value_from_obj(outputdict, keylist) == value
    elif testtype == 'contains':
        assert value in get_value_from_obj(outputdict, keylist)
    elif testtype == 'length':
        assert len(get_value_from_obj(outputdict, keylist)) == value
    else:
        assert testtype in ['is_equal', 'contains', 'length']
