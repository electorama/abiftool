#!/usr/bin/env python3
# pairwise.py - Pairwise/Condorcet calculator for Python
#
# Copyright (C) 2023 Rob Lanphier
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
import argparse
import pathlib
import re
import sys


def score_result_from_abifmodel(abifmodel):
    scores = {}
    voterct = {}
    for voteline in abifmodel['votelines']:
        qty = voteline['qty']
        for cand, candval in voteline['prefs'].items():
            rating = int(candval['rating'])
            if cand in scores:
                scores[cand] += rating * qty
            else:
                scores[cand] = rating * qty
            if rating > 0:
                if cand in voterct:
                    voterct[cand] += qty
                else:
                    voterct[cand] = qty

    result = [{"candtok": cand,
               "score": score,
               "voterct": voterct[cand],
               "candname": abifmodel['candidates'][cand]} for cand, score in scores.items()]
    result.sort(key=lambda x: x['score'], reverse=True)
    return result


def score_report(jabmod):
    retval = ""
    totalvoters = jabmod['metadata']['ballotcount']
    sr = score_result_from_abifmodel(jabmod)
    for s in sr:
        retval += f"- {s['score']
                       } points (from {s['voterct']} voters) -- {s['candname']}\n"
    retval += f"Voter count: {totalvoters}\n"
    retval += f"Winner: {sr[0]['candname']}\n"
    return retval


def STAR_result_from_abifmodel(abifmodel):
    retval = {}
    bc = retval['totalvoters'] = abifmodel['metadata']['ballotcount']
    scres = retval['scores'] = score_result_from_abifmodel(abifmodel)
    retval['round1winners'] = retval['scores'][0:2]
    copecount = full_copecount_from_abifmodel(abifmodel)

    fin1 = retval['fin1'] = scres[0]['candtok']
    fin2 = retval['fin2'] = scres[1]['candtok']
    fin1n = retval['fin1n'] = scres[0]['candname']
    fin2n = retval['fin2n'] = scres[1]['candname']

    f1v = retval['fin1votes'] = copecount['winningvotes'][fin1][fin2]
    f2v = retval['fin2votes'] = copecount['winningvotes'][fin2][fin1]
    retval['final_abstentions'] = bc - f1v - f2v
    if f1v > f2v:
        retval['winner'] = fin1n
    elif f2v > f1v:
        retval['winner'] = fin2n
    else:
        retval['winner'] = f"tie {fin1n} and {fin2n}"
    return retval


def STAR_report(jabmod):
    retval = ""
    sr = STAR_result_from_abifmodel(jabmod)
    tvot = sr['totalvoters']
    retval += f"Total voters: {tvot}\n"
    retval += f"Scores:\n"
    for s in sr['scores']:
        retval += f"- {s['score']
                       } stars (from {s['voterct']} voters) -- {s['candname']}\n"
    retval += f"Finalists: \n"
    retval += f"- {sr['fin1n']
                   } preferred by {sr['fin1votes']} of {tvot} voters\n"
    retval += f"- {sr['fin2n']
                   } preferred by {sr['fin2votes']} of {tvot} voters\n"
    retval += f"- {sr['final_abstentions']} abstentions\n"
    retval += f"Winner: {sr['winner']}\n"
    return retval


def main():
    """Create score array"""
    parser = argparse.ArgumentParser(
        description='Takes abif and returns score results')
    parser.add_argument('input_file', help='Input .abif')

    args = parser.parse_args()

    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext, add_ratings=True)

    outstr = ""
    outstr += "======= ABIF File =======\n"
    outstr += abiftext

    outstr += "\n======= Score Results =======\n"
    outstr += score_report(jabmod)

    outstr += "\n======= STAR Results =======\n"
    outstr += STAR_report(jabmod)

    print(outstr)


if __name__ == "__main__":
    main()
