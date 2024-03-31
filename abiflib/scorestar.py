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
from abiflib.pairwise import *
import argparse
import json
import math
import pathlib
import re
import sys


def basic_score_result_from_abifmodel(abifmodel):
    retval = {candtok: {} for candtok in abifmodel['candidates'].keys()}
    for cand in abifmodel['candidates'].keys():
        retval[cand]['candname'] = abifmodel['candidates'][cand]
        retval[cand]['score'] = 0
        retval[cand]['votercount'] = 0
    for voteline in abifmodel['votelines']:
        qty = voteline['qty']
        for cand, candval in voteline['prefs'].items():
            rating = int(candval['rating'])
            retval[cand]['score'] += rating * qty
            if rating > 0:
                retval[cand]['votercount'] += qty
    return retval


def enhanced_score_result_from_abifmodel(abifmodel):
    retval = {}
    newscores = basic_score_result_from_abifmodel(abifmodel)
    ranklist = sorted(newscores.keys(), key=lambda x: newscores[x]["score"], reverse=True)
    retval['scores'] = newscores

    scores = {ct: newscores[ct]['score'] for ct in abifmodel['candidates'].keys()}

    # Calculate the ranks, ensuring that equal scores results in equal ranks
    rank = 0
    for i, c in enumerate(ranklist):
        if i > 0:
            pscore = newscores[ranklist[i-1]]['score']
        else:
            pscore = math.inf
        tscore = newscores[c]['score']
        if pscore > tscore:
            rank += 1
        newscores[c]['rank'] = rank
    retval['ranklist'] = ranklist
    return retval


def STAR_result_from_abifmodel(abifmodel):
    retval = enhanced_score_result_from_abifmodel(abifmodel)
    bc = retval['totalvoters'] = abifmodel['metadata']['ballotcount']
    retval['round1winners'] = retval['ranklist'][0:2]
    copecount = full_copecount_from_abifmodel(abifmodel)

    fin1 = retval['fin1'] = retval['ranklist'][0]
    fin2 = retval['fin2'] = retval['ranklist'][1]
    fin1n = retval['fin1n'] = retval['scores'][fin1]['candname']
    fin2n = retval['fin2n'] = retval['scores'][fin2]['candname']

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


def score_report(jabmod):
    retval = ""
    totalvoters = jabmod['metadata']['ballotcount']
    sr = enhanced_score_result_from_abifmodel(jabmod)
    for candtok in sr['ranklist']:
        candinfo = sr['scores'][candtok]
        retval += f"- {candinfo['score']} points"
        retval += f" (from {candinfo['votercount']} voters)"
        retval += f" -- {candinfo['candname']}\n"

    retval += f"Voter count: {totalvoters}\n"
    winnertok = sr['ranklist'][0]
    retval += f"Winner: {sr['scores'][winnertok]['candname']}\n"
    return retval


def STAR_report(jabmod):
    retval = ""
    sr = STAR_result_from_abifmodel(jabmod)
    tvot = sr['totalvoters']
    retval += f"Total voters: {tvot}\n"
    retval += f"Scores:\n"
    for candtok in sr['ranklist']:
        candinfo = sr['scores'][candtok]
        retval += f"- {candinfo['score']} stars"
        retval += f" (from {candinfo['votercount']} voters)"
        retval += f" -- {candinfo['candname']}\n"
    retval += f"Finalists: \n"
    retval += f"- {sr['fin1n']
                   } preferred by {sr['fin1votes']} of {tvot} voters\n"
    retval += f"- {sr['fin2n']
                   } preferred by {sr['fin2votes']} of {tvot} voters\n"
    retval += f"- {sr['final_abstentions']} abstentions\n"
    retval += f"Winner: {sr['winner']}\n"
    return retval


def scale_scores_to_starscale(jabmod,
                              total_stars_to_display=50):
    ballotcount = jabmod['metadata']['ballotcount']
    max_rating = jabmod['metadata']['max_rating']
    max_total_ratings = int(max_rating) * int(ballotcount)
    scale = int(total_stars_to_display) / float(max_total_ratings)
    #print(f"{total_stars_to_display=} / {max_total_ratings=} = {scale=}")
    #stars = round(total_stars_to_display * scale)
    candidates = jabmod['candidates']
    scores = STAR_result_from_abifmodel(jabmod)
    star_dict = {}
    star_total = 0
    for candtoken, candname in candidates.items():
        candscore = scores['scores'][candtoken]['score']
        candstars = candscore * scale
        star_dict[candtoken] = {
            'candname': candname,
            'stars': candstars,
            'score': candscore
        }
        star_total += candstars
    return star_dict, star_total


def main():
    """Create score array"""
    parser = argparse.ArgumentParser(
        description='Takes abif and returns score results')
    parser.add_argument('input_file', help='Input .abif')

    args = parser.parse_args()

    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext, add_ratings=True)

    outstr = ""
    report_abif_file = True
    report_raw_json = False
    report_score_results = True
    report_star_results = True
    report_star_scale = False
    if report_abif_file:
        outstr += "======= ABIF File =======\n"
        outstr += abiftext

    if report_raw_json:
        outstr += "\n======= Raw Score JSON =======\n"
        scoreres = enhanced_score_result_from_abifmodel(jabmod)
        outstr += json.dumps(scoreres, indent=4)

        outstr += "\n======= Raw STAR JSON =======\n"
        retval = STAR_result_from_abifmodel(jabmod)
        outstr += json.dumps(retval, indent=4)

    if report_score_results:
        outstr += "\n======= Score Results =======\n"
        outstr += score_report(jabmod)

    if report_star_results:
        outstr += "\n======= STAR Results =======\n"
        outstr += STAR_report(jabmod)

    if report_star_scale:
        outstr += "\n======= STAR scale ========\n"
        outstr += str(scale_scores_to_starscale(jabmod=jabmod,
                                                total_stars_to_display=50))
    print(outstr)


if __name__ == "__main__":
    main()
