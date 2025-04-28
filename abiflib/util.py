#!/usr/bin/env python3
# abiflib/util.py - misc ABIF-related functions
#
# Copyright (C) 2023, 2024, 2025 Rob Lanphier
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

def convert_text_to_abif(fromfmt, inputblobs, cleanws=False, add_ratings=False, metadata={}):
    if (fromfmt == 'abif'):
        try:
            abifmodel = convert_abif_to_jabmod(inputblobs[0],
                                               cleanws=cleanws,
                                               add_ratings=add_ratings)
        except ABIFVotelineException as e:
            print(f"ERROR: {e.message}")
            sys.exit()
    elif (fromfmt == 'debtally'):
        rawabifstr = convert_debtally_to_abif(inputblobs[0], metadata=metadata)
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (fromfmt == 'jabmod'):
        abifmodel = json.loads(inputblobs[0])
    elif (fromfmt == 'preflib'):
        rawabifstr = convert_preflib_str_to_abif(inputblobs[0])
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (fromfmt == 'sftxt'):
        abifmodel = convert_sftxt_to_jabmod(inputblobs[0], inputblobs[1])
    elif (fromfmt == 'widj'):
        abifmodel = convert_widj_to_jabmod(inputblobs[0])
    else:
        raise ABIFVotelineException(value=inputblobs[0],
                                    message=f"Cannot convert from {fromfmt} yet.")
    retval = convert_jabmod_to_abif(abifmodel, add_ratings=False)
    return retval


def candlist_text_from_abif(jabmod):
    canddict = jabmod['candidates']
    output = ""
    output += "Candidates:\n"
    for k, v in sorted(canddict.items()):
        output += f"  {k}: {v}\n"
    return output


def utf8_string_to_abif_token(longstring, max_length=20, add_sha1=False):
    '''Convert a name into a short token for use in abif'''
    # TODO: replace _short_token in sftxt.py with this
    # TDOO: make this more sophisticated, replacing candidate names with something
    #   recognizable as candidate names, even if there's a lot of upper ASCII in the
    #   name.
    if len(longstring) <= max_length and \
       re.match(r'^[A-Za-z0-9]+$', longstring):
        retval = longstring
    else:
        cleanstr = re.sub('[^A-Za-z0-9]+', '_', longstring)
        cleanstr = re.sub('WRITE_IN_', "wi_", cleanstr)
        retval = cleanstr[:max_length]
    return retval


def FPTP_result_from_abifmodel(abifmodel):
    """Calculate the First Past the Post (FPTP/Plurality) result from the ABIF model."""
    toppicks = {}
    maxtop = 0
    winners = []

    for vline in abifmodel['votelines']:
        xtop = min(vline['prefs'], key=lambda cand: vline['prefs'][cand]['rank'])
        toppicks[xtop] = toppicks.get(xtop, 0) + vline['qty']
        if toppicks[xtop] > maxtop:
            maxtop = toppicks[xtop]
            winners = [xtop]
        elif toppicks[xtop] == maxtop:
            winners.append(xtop)

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
