import pytest
from abiflib.core import convert_abif_to_jabmod
from abiflib.fptp_tally import FPTP_result_from_abifmodel

def test_fptp_overvote_handling():
    # ABIF string with an overvoted ballot (multiple rank 1s)
    abif_str = """
# metadata
{ballotcount: 2}
# candlines
=A:Candidate A
=B:Candidate B
=C:Candidate C
# votelines
1:A
1:A=B
"""

    jabmod = convert_abif_to_jabmod(abif_str)
    result = FPTP_result_from_abifmodel(jabmod)

    # Expect Candidate A to have 1 vote from the first ballot
    assert result['toppicks']['A'] == 1
    # Expect Candidate B and C to have 0 votes
    assert result['toppicks']['B'] == 0
    assert result['toppicks']['C'] == 0
    # Expect 1 invalid ballot due to overvote
    assert result['invalid_ballots'] == 1
    # Expect total valid votes to be 1 (only the first ballot)
    assert result['total_votes_recounted'] == 1
    # Expect total ballots processed to be 2
    assert result['total_votes'] == 2
    # Expect 'None' (undervotes/overvotes) to be 1
    assert result['toppicks'][None] == 1


def test_fptp_undervote_handling():
    # ABIF string with an undervoted ballot (no rank 1s)
    abif_str = """
# metadata
{ballotcount: 2}
# candlines
=A:Candidate A
=B:Candidate B
# votelines
1:A
1:
"""

    jabmod = convert_abif_to_jabmod(abif_str)
    result = FPTP_result_from_abifmodel(jabmod)

    # Expect Candidate A to have 1 vote
    assert result['toppicks']['A'] == 1
    # Expect Candidate B to have 0 votes
    assert result['toppicks']['B'] == 0
    # Expect 0 invalid ballots (it's an undervote, not an overvote)
    assert result['invalid_ballots'] == 0
    # Expect total valid votes to be 1
    assert result['total_votes_recounted'] == 1
    # Expect total ballots processed to be 2
    assert result['total_votes'] == 2
    # Expect 'None' (undervotes/overvotes) to be 1
    assert result['toppicks'][None] == 1
