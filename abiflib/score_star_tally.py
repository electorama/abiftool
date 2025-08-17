#!/usr/bin/env python3
''' scorestar.py - Score and STAR tally functions '''

# Copyright (C) 2024, 2025 Rob Lanphier
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
import json
import math
import pathlib
import re
import sys
import time


def basic_score_result_from_abifmodel(abifmodel):
    candidates = abifmodel['candidates']
    votelines = abifmodel['votelines']
    retval = {cand: {'candname': candidates[cand], 'score': 0, 'votercount': 0} for cand in candidates}
    for voteline in votelines:
        qty = voteline['qty']
        prefs = voteline['prefs']
        for cand, candval in prefs.items():
            entry = retval.get(cand)
            if entry is not None:
                rating = candval.get('rating')
                if rating is not None:
                    rating = int(rating)
                    entry['score'] += rating * qty
                    if rating > 0:
                        entry['votercount'] += qty
    return retval


def enhanced_score_result_from_abifmodel(abifmodel):
    retval = {}
    newscores = basic_score_result_from_abifmodel(abifmodel)
    # Use a tuple list for sorting to avoid repeated dict lookups
    score_items = [(cand, newscores[cand]['score']) for cand in newscores]
    score_items.sort(key=lambda x: x[1], reverse=True)
    ranklist = [cand for cand, _ in score_items]
    retval['scores'] = newscores

    # Calculate the ranks, ensuring that equal scores results in equal ranks
    rank = 0
    prev_score = None
    for i, cand in enumerate(ranklist):
        tscore = newscores[cand]['score']
        if prev_score is None:
            prev_score = tscore
        elif prev_score > tscore:
            rank += 1
            prev_score = tscore
        newscores[cand]['rank'] = rank
    retval['ranklist'] = ranklist
    retval['total_all_scores'] = sum(x['score'] for x in newscores.values())
    retval['totalvoters'] = abifmodel['metadata']['ballotcount']
    return retval


def STAR_result_from_abifmodel(abifmodel):
    retval = enhanced_score_result_from_abifmodel(abifmodel)
    bc = retval['totalvoters']
    retval['round1winners'] = retval['ranklist'][0:2]

    candcount = len(abifmodel['candidates'])
    if abifmodel.get('metadata', {}).get('is_ranking_to_rating'):
        notice = {
            "notice_type": "note",
            "short": ("STAR ratings estimated from ranked ballots "
                      "using Borda scoring method"),
            "long": ( "The ranked ballots have been converted to STAR ratings "
                      "using Borda scoring: each candidate receives points "
                      "equal to (number_of_candidates - their_rank). In this "
                      f"election, we have {candcount} candidates, so the 1st "
                      f"choice gets {candcount - 1} points, the 2nd choice "
                      f"gets {candcount - 2} points, etc. These Borda scores "
                      "are then used as STAR ratings for tabulation by STAR." )
        }
        retval['notices'] = [notice]
    # Optimization: Only compute the pairwise result for the top two if possible
    finalists = retval['ranklist'][0:2]
    copecount = None
    if len(finalists) == 2:
        fin1, fin2 = finalists
        # Only compute the head-to-head for the two finalists
        # Use the same logic as pairwise_count_dict but just for these two
        pairdict = {fin1: {fin2: 0}, fin2: {fin1: 0}}
        for vl in abifmodel['votelines']:
            qty = vl['qty']
            prefs = vl['prefs']
            maxrank = sys.maxsize
            arank = prefs.get(fin1, {}).get('rank', maxrank)
            brank = prefs.get(fin2, {}).get('rank', maxrank)
            if arank < brank:
                pairdict[fin1][fin2] += qty
            elif brank < arank:
                pairdict[fin2][fin1] += qty
        copecount = {'winningvotes': pairdict}
        if os.environ.get("ABIFTOOL_DEBUG"):
            print(f"[score_star_tally] fast head-to-head: {fin1} vs {fin2}")
    else:
        t0 = time.perf_counter()
        copecount = full_copecount_from_abifmodel(abifmodel)
        t1 = time.perf_counter()
        if os.environ.get("ABIFTOOL_DEBUG"):
            print(f"[score_star_tally] full_copecount_from_abifmodel: {t1-t0:.4f}s")

    if len(retval['ranklist']) == 0:
        fin1 = retval['fin1'] = None
        fin2 = retval['fin2'] = None
        fin1n = retval['fin1n'] = None
        fin2n = retval['fin2n'] = None

        retval['fin1votes'] = 0
        retval['fin2votes'] = 0
        retval['final_abstentions'] = bc
        retval['winner'] = fin1n
        retval['winner_names'] = [fin1n] if fin1n else []
        retval['winner_tokens'] = [fin1] if fin1 else []
    elif len(retval['ranklist']) == 1:
        fin1 = retval['fin1'] = retval['ranklist'][0]
        fin2 = retval['fin2'] = None
        fin1n = retval['fin1n'] = retval['scores'][fin1]['candname']
        fin2n = retval['fin2n'] = None

        # Count how many voters gave fin1 a positive rating
        fin1votes = 0
        for vl in abifmodel['votelines']:
            qty = vl['qty']
            prefs = vl['prefs']
            rating = prefs.get(fin1, {}).get('rating', 0)
            if rating > 0:
                fin1votes += qty

        retval['fin1votes'] = fin1votes
        retval['fin2votes'] = 0
        retval['final_abstentions'] = bc - fin1votes
        retval['winner'] = fin1n
        retval['winner_names'] = [fin1n]
        retval['winner_tokens'] = [fin1]
    else:
        fin1 = retval['fin1'] = retval['ranklist'][0]
        fin2 = retval['fin2'] = retval['ranklist'][1]
        fin1n = retval['fin1n'] = retval['scores'][fin1]['candname']
        fin2n = retval['fin2n'] = retval['scores'][fin2]['candname']
        f1v = retval['fin1votes'] = copecount['winningvotes'][fin1][fin2]
        f2v = retval['fin2votes'] = copecount['winningvotes'][fin2][fin1]
        retval['final_abstentions'] = bc - f1v - f2v
        if f1v > f2v:
            retval['winner'] = fin1n
            retval['winner_names'] = [fin1n]
            retval['winner_tokens'] = [fin1]
        elif f2v > f1v:
            retval['winner'] = fin2n
            retval['winner_names'] = [fin2n]
            retval['winner_tokens'] = [fin2]
        else:
            retval['winner'] = f"tie {fin1n} and {fin2n}"
            retval['winner_names'] = [fin1n, fin2n]
            retval['winner_tokens'] = [fin1, fin2]

    # Add percentage strings for both text output and template use
    tvot = retval['totalvoters']
    total_stars = retval['total_all_scores']

    # Add percentage strings to candidate score data
    for candtok in retval['ranklist']:
        candinfo = retval['scores'][candtok]
        candinfo['score_pct_str'] = f"{candinfo['score']/total_stars:.1%}" if total_stars else "0.0%"
        candinfo['voter_pct_str'] = f"{candinfo['votercount']/tvot:.1%}" if tvot else "0.0%"

    # Add percentage strings for finalists
    retval['fin1votes_pct_str'] = f"{retval['fin1votes']/tvot:.1%}" if tvot else "0.0%"
    if retval['fin2votes']:
        retval['fin2votes_pct_str'] = f"{retval['fin2votes']/tvot:.1%}" if tvot else "0.0%"
    retval['final_abstentions_pct_str'] = f"{retval['final_abstentions']/tvot:.1%}" if tvot else "0.0%"

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
    retval += f"Score Winner: {sr['scores'][winnertok]['candname']}\n"
    return retval


def STAR_report(jabmod):
    retval = ""
    sr = STAR_result_from_abifmodel(jabmod)
    tvot = sr['totalvoters']

    retval += f"Total voters: {tvot:,}\n"
    retval += f"Scores:\n"
    for candtok in sr['ranklist']:
        candinfo = sr['scores'][candtok]
        retval += f"- {candinfo['score']:,} stars ({candinfo['score_pct_str']})"
        retval += f" from {candinfo['votercount']:,} voters ({candinfo['voter_pct_str']})"
        retval += f" -- {candinfo['candname']}\n"

    retval += f"Finalists: \n"
    retval += f"- {sr['fin1n']} preferred by {sr['fin1votes']:,} of {tvot:,} voters ({sr['fin1votes_pct_str']})\n"
    if sr['fin2n']:
        retval += f"- {sr['fin2n']} preferred by {sr['fin2votes']:,} of {tvot:,} voters ({sr['fin2votes_pct_str']})\n"
    retval += f"- {sr['final_abstentions']:,} abstentions ({sr['final_abstentions_pct_str']})\n"
    retval += f"STAR Winner: {sr['winner']}\n"

    # Add notices section if present
    if sr.get('notices'):
        retval += format_notices_for_text_output(sr['notices'])

    return retval


def scaled_scores(jabmod, target_scale=100):
    retval = {}
    scores = STAR_result_from_abifmodel(jabmod)
    ballotcount = jabmod['metadata']['ballotcount']
    retval['max_rating'] = jabmod['metadata'].get('max_rating')
    retval['total_all_scores'] = scores['total_all_scores']
    try:
        scale = target_scale / retval['total_all_scores']
    except ZeroDivisionError:
        scale = 0
    retval['scale_factor'] = scale
    scaled_total = 0
    candidates = jabmod['candidates']
    retval['canddict'] = {}
    for candtoken, candname in candidates.items():
        candscore = scores['scores'][candtoken]['score']
        scaled_score = candscore * scale
        retval['canddict'][candtoken] = {
            'candname': candname,
            'scaled_score': scaled_score,
            'score': candscore
        }
        scaled_total += scaled_score
    retval['scaled_total'] = scaled_total
    return retval


def abifmodel_has_ratings(abifmodel):
    '''Check if abifmodel has rating data to use by STAR or score methods

    It would be nice to do a more sophisticated test.  As of this
    writing, this function just checks the first candidate in the
    first voteline and hopes that's good enough.
    '''
    has_rating = bool(list(abifmodel['votelines'][0]['prefs'].values())[0].get('rating'))
    return(has_rating)


def main():
    """Library for calculating score voting and STAR voting results"""
    parser = argparse.ArgumentParser(
        description='Takes abif and returns score results')
    parser.add_argument('input_file', help='Input .abif')

    args = parser.parse_args()

    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext, add_ratings=True)

    outstr = ""

    report_abif_file = True
    report_raw_jabmod = True
    report_raw_score_json = True
    report_raw_STAR_json = True
    report_score_results = True
    report_star_results = True
    report_scaled_scores = True
    if report_abif_file:
        outstr += "======= ABIF File =======\n"
        outstr += abiftext

    if report_raw_jabmod:
        outstr += "======= ABIF Model (jabmod) =======\n"
        outstr += json.dumps(jabmod, indent=4)

    if report_raw_score_json:
        outstr += "\n======= Raw Score JSON =======\n"
        scoreres = enhanced_score_result_from_abifmodel(jabmod)
        outstr += json.dumps(scoreres, indent=4)

    if report_raw_STAR_json:
        outstr += "\n======= Raw STAR JSON =======\n"
        retval = STAR_result_from_abifmodel(jabmod)
        outstr += json.dumps(retval, indent=4)

    if report_score_results:
        outstr += "\n======= Score Results =======\n"
        outstr += score_report(jabmod)

    if report_star_results:
        outstr += "\n======= STAR Results =======\n"
        outstr += STAR_report(jabmod)

    if report_scaled_scores:
        outstr += "\n======= Scaled Scores ========\n"
        outstr += json.dumps(scaled_scores(jabmod=jabmod,
                                           target_scale=50),
                             indent=4)
    print(outstr)


if __name__ == "__main__":
    main()
