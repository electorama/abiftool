# CVR-related conversion and metadata tests
#
# This file focuses on tests for container-based CVR conversions and
# associated metadata fields. Over time, sftxt/sfjson and other CVR
# format tests can be merged here to avoid city-by-city test files.

from abiftestfuncs import run_json_output_test_from_abif
import pytest


testlist = [
    # Burlington 2009 URL metadata (Wikipedia)
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/burl2009/burl2009.abif',
        'contains',
        ["metadata", "wikipedia_url"],
        'wikipedia.org/wiki/2009_Burlington,_Vermont_mayoral_election',
        id='cvr_001_burl2009_wikipedia'
    ),

    # Burlington 2009 URL metadata (Electowiki)
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/burl2009/burl2009.abif',
        'contains',
        ["metadata", "electowiki_url"],
        'electowiki.org/wiki/2009_Burlington_mayoral_election',
        id='cvr_002_burl2009_electowiki'
    ),

    # Burlington 2009 official results URL (archived official page)
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/burl2009/burl2009.abif',
        'contains',
        ["metadata", "official_results_url"],
        'web.archive.org/web/20090502034115/http://www.ci.burlington.vt.us/ct/elections/',
        id='cvr_003_burl2009_official'
    ),

    # Burlington 2009 wikidata URL
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/burl2009/burl2009.abif',
        'contains',
        ["metadata", "wikidata_url"],
        'wikidata.org/wiki/Q4999304',
        id='cvr_004_burl2009_wikidata'
    ),

    # Burlington 2009 alternate official link included in ext_url_01
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'testdata/burl2009/burl2009.abif',
        'contains',
        ["metadata", "ext_url_01"],
        'burlingtonvotes.org/20090303/2009%20Burlington%20Mayor%20Round.htm',
        id='cvr_005_burl2009_ext_url_01'
    ),

    # St. Louis 2025 (Mayor) — Wikipedia URL present (skips if file missing)
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'localabif/stlouis/stl-2025-mayor.abif',
        'contains',
        ["metadata", "wikipedia_url"],
        'wikipedia.org/wiki/2025_St._Louis_mayoral_election',
        id='cvr_006_stl2025_mayor_wikipedia'
    ),

    # St. Louis 2025 (Mayor) — Approval.Vote link as ext_url_01 (skips if file missing)
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'localabif/stlouis/stl-2025-mayor.abif',
        'contains',
        ["metadata", "ext_url_01"],
        'approval.vote/report/us/mo/st_louis/2025/03/mayor',
        id='cvr_007_stl2025_mayor_approvalvote'
    ),

    # St. Louis 2025 (Mayor) — source_url should reflect the actual download URL
    pytest.param(
        ['-f', 'abif', '-t', 'jabmod'],
        'localabif/stlouis/stl-2025-mayor.abif',
        'contains',
        ["metadata", "source_url"],
        'github.com/fsargent/approval-vote/raw/refs/heads/main/st-louis-cvr/data/CVRExport-8-27-2025.zip',
        id='cvr_008_stl2025_mayor_source_url'
    ),
]


@pytest.mark.parametrize(
    'cmd_args, inputfile, testtype, keylist, value', testlist
)
def test_json_key_subkey_val(cmd_args, inputfile, testtype, keylist, value):
    """Test equality/containment of a subkey to a value for CVR-related cases"""
    run_json_output_test_from_abif(cmd_args, inputfile, testtype, keylist, value)
