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

def FPTP_result_from_abifmodel(abifmodel, count_blanks=True):
    """Calculate the First Past the Post (FPTP/Plurality) result from the ABIF model."""
    toppicks = {}
    maxtop = 0
    winners = []

    for vline in abifmodel['votelines']:
        if len(vline['prefs']) > 0:
            xtop = min(vline['prefs'], key=lambda cand: vline['prefs'][cand]['rank'])
            toppicks[xtop] = toppicks.get(xtop, 0) + vline['qty']
            if toppicks[xtop] > maxtop:
                maxtop = toppicks[xtop]
                winners = [xtop]
            elif toppicks[xtop] == maxtop:
                winners.append(xtop)
        elif count_blanks:
            toppicks[None] = toppicks.get(None, 0) + vline['qty']

    total_votes_recounted = sum(toppicks.values()),
    total_votes = abifmodel['metadata']['ballotcount']
    top_pct = (maxtop / total_votes) * 100 if total_votes > 0 else 0

    return {
        'toppicks': toppicks,
        'winners': winners,
        'top_qty': maxtop,
        'top_pct': top_pct,
        'total_votes_recounted': total_votes_recounted,
        'total_votes': total_votes,
    }


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
