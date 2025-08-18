#!/usr/bin/env python3
''' abiflib/fptp_tally.py - Functions for tallying FPTP elections '''

# Copyright (c) 2025 Rob Lanphier
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from abiflib import *
import copy
import json
from pprint import pprint
import re
import sys
import urllib.parse

def FPTP_result_from_abifmodel(abifmodel):
    """Calculate the First Past the Post (FPTP/Plurality) result from the ABIF model."""
    toppicks = {}
    # Initialize all candidates with 0 votes
    for cand_token in abifmodel['candidates'].keys():
        toppicks[cand_token] = 0

    invalid_ballots = 0

    for vline in abifmodel['votelines']:
        first_prefs = []
        for cand, prefs in vline['prefs'].items():
            if prefs.get('rank') == 1:
                first_prefs.append(cand)

        if len(first_prefs) == 1:
            # valid votes
            toppicks[first_prefs[0]] += vline['qty']
        elif len(first_prefs) > 1:
            # overvotes
            invalid_ballots += vline['qty']

    # Calculate winner based on the new toppicks
    maxtop = 0
    winners = []
    for cand, votes in toppicks.items():
        if votes > maxtop:
            maxtop = votes
            winners = [cand]
        elif votes == maxtop:
            winners.append(cand)

    total_valid_votes = sum(toppicks.values())
    total_ballots_processed = abifmodel['metadata']['ballotcount']

    # The 'None' category should reflect ballots that were either blank or overvoted
    # This aligns more closely with official summary's undervotes/overvotes
    toppicks[None] = total_ballots_processed - total_valid_votes

    top_pct = (maxtop / total_valid_votes) * 100 if total_valid_votes > 0 else 0

    result = {
        'toppicks': toppicks,
        'winners': winners,
        'top_qty': maxtop,
        'top_pct': top_pct,
        'total_votes_recounted': total_valid_votes,
        'total_votes': total_ballots_processed,
        'invalid_ballots': invalid_ballots
    }

    # Add notice if this election uses ranked ballots
    notices = []
    if abifmodel.get('metadata', {}).get('ballot_type') == 'ranked':
        notices.append({
            'notice_type': 'note',
            'short': 'Only using first-choices on ranked ballots'
        })

    if notices:
        result['notices'] = notices

    return result


def get_FPTP_report(abifmodel):
    """Generate FPTP report from the ABIF model."""
    results = FPTP_result_from_abifmodel(abifmodel)
    report = f"First-Past-The-Post (FPTP) Results:\n"
    report += f"  Top prefs:\n"

    for cand in results['toppicks']:
        report += f"   * {cand}: {results['toppicks'][cand]}\n"
    pctreport = f"{results['top_qty']} votes of " + \
        f"{results['total_votes']} total votes ({results['top_pct']:.2f}%)"
    if len(results['winners']) == 1:
        report += f"  Winner with {pctreport}:\n"
        report += f"   * {results['winners'][0]} with {pctreport}.\n"
    else:
        report += f"  Tied winners each with {pctreport}:\n"
        for w in results['winners']:
           report += f"   * {w}\n"
    return report


def main():
    parser = argparse.ArgumentParser(description='FPTP calculator for ABIF')
    parser.add_argument('input_file', help='Input .abif')
    parser.add_argument('-j', '--json', action="store_true",
                        help='Provide raw json output')

    args = parser.parse_args()
    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext)
    FPTP_dict = FPTP_result_from_abifmodel(jabmod)
    output = ""
    if args.json:
        output += json.dumps(clean_dict(FPTP_dict), indent=4)
    else:
        output += candlist_text_from_abif(jabmod)
        output += get_FPTP_report(jabmod)
    print(output)


if __name__ == "__main__":
    main()
