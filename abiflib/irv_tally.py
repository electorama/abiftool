#!/usr/bin/env python3
''' irvtally.py - Convert IRV results to/from jabmod (JSON ABIF model) '''
#
# Copyright (c) 2024, 2025 Rob Lanphier
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
from abiflib.pairwise_tally import pairwise_count_dict
import re
import datetime
import argparse
import pathlib
from pprint import pprint, pformat
import random
import sys
import os
import time
from datetime import timezone


# Add fallback for @profile if not running under kernprof
try:
    profile
except NameError:
    def profile(func):
        return func


@profile
def _eliminate_cands_from_votelines(candlist, votelines):
    '''Returns a new list of votelines without the specified candidates.'''
    t0 = time.perf_counter()
    elim_set = set(candlist)
    new_votelines = []
    append = new_votelines.append  # Localize for speed
    # Use list comprehension for speed, and skip copying if no candidates are eliminated
    return [
        {'qty': vln['qty'], 'prefs': {cand: prefs for cand, prefs in vln['prefs'].items() if cand not in elim_set}}
        if any(cand in elim_set for cand in vln['prefs']) else vln
        for vln in votelines
    ]
    t1 = time.perf_counter()
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"[irv_tally] _eliminate_cands_from_votelines: {t1 - t0:.4f}s for {len(votelines)} votelines, elim {candlist}")
    return new_votelines


@profile
def _discard_toprank_overvotes(votelines):
    '''Separates overvoted ballots and returns a tuple of (overvote_qty, valid_votelines).'''
    t0 = time.perf_counter()
    valid_votelines = []
    overvotes_qty = 0
    for vln in votelines:
        prefs = vln['prefs']
        if not prefs:
            valid_votelines.append(vln)
            continue

        # Single pass: find min_rank and count how many have it
        min_rank = None
        top_rank_count = 0
        for p in prefs.values():
            r = p['rank']
            if min_rank is None or r < min_rank:
                min_rank = r
                top_rank_count = 1
            elif r == min_rank:
                top_rank_count += 1

        if top_rank_count > 1:
            # This is an overvote
            overvotes_qty += vln['qty']
        else:
            # This is a valid voteline
            valid_votelines.append(vln)
    t1 = time.perf_counter()
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"[irv_tally] _discard_toprank_overvotes: {t1 - t0:.4f}s for {len(votelines)} votelines")
    return (overvotes_qty, valid_votelines)


@profile
def _get_valid_topcand_qty(voteline):
    """Finds the top-ranked candidate in a voteline, handling ties (iterative version)."""
    qty = voteline['qty']
    prefs = voteline['prefs']
    if not prefs:
        return (None, qty)
    # Convert to a list of (candidate, rank) pairs for in-place filtering
    items = list(prefs.items())
    while items:
        min_rank = float('inf')
        for _, p in items:
            r = p['rank']
            if r < min_rank:
                min_rank = r
        # Collect all candidates with min_rank
        top_cands = [c for c, p in items if p['rank'] == min_rank]
        if len(top_cands) == 1:
            return (top_cands[0], qty)
        # Remove all tied candidates in-place
        items = [(c, p) for c, p in items if p['rank'] != min_rank]
    return (None, qty)


@profile
def _irv_count_internal(candlist, votelines, rounds=None, roundmeta=None, roundnum=None, canddict=None):
    """
    IRV count of given votelines

    This returns the following triple:
    * winner - the winner(s) of this round, if there are any
    * rounds - round-by-round votecounts
    * roundmeta - metadata associated with all rounds
    """
    t0 = time.perf_counter()
    depth = len(rounds) if rounds else 0
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem02: Entering _irv_count_internal: depth={depth}")
    # 1. initializing/calculating rounds, roundmeta, and roundcount
    # 1a. rounds, roundmeta, and roundnum are passed in recursively; init if needed
    if rounds is None:
        rounds = []
    if roundmeta is None:
        roundmeta = []
    # 1b. populating roundcount, which contains all remaining candidates in this round
    roundcount = {cand: 0 for cand in candlist}

    # 2. initializing mymeta, which will eventually be appended to roundmeta
    mymeta = {}
    if roundnum is None:
        roundnum = mymeta['roundnum'] = roundmeta[-1]['roundnum'] + 1
    else:
        mymeta['roundnum'] = roundnum
    mymeta['startingqty'] = sum(vln['qty'] for vln in votelines)
    mymeta['exhaustedqty'] = 0
    mymeta['overvoteqty'] = 0
    mymeta['ballotcount'] = 0

    # 3. Overvote pruning and counting remaining ballots
    t_ov0 = time.perf_counter()
    (ov, prunedvlns) = _discard_toprank_overvotes(votelines)
    t_ov1 = time.perf_counter()
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"[irv_tally]   _discard_toprank_overvotes: {t_ov1 - t_ov0:.4f}s at depth={depth}")
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem03: After _discard_toprank_overvotes")
    mymeta['overvoteqty'] += ov
    # Count top-ranked candidates in pruned votelines
    get_valid_topcand_qty_calls = 0
    t_topcand0 = time.perf_counter()
    for vln in prunedvlns:
        get_valid_topcand_qty_calls += 1
        (rcand, rqty) = _get_valid_topcand_qty(vln)
        if rcand:
            roundcount[rcand] += rqty
        else:
            mymeta['exhaustedqty'] += rqty
    t_topcand1 = time.perf_counter()
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"[irv_tally]   _get_valid_topcand_qty: {t_topcand1 - t_topcand0:.4f}s for {get_valid_topcand_qty_calls} prunedvlns at depth={depth}")
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem04: After _get_valid_topcand_qty loop")
    total_votes = sum(roundcount.values())
    mymeta['countedqty'] = total_votes

    # 4. Other mymeta stuff
    winner = None
    if len(roundcount.values()) > 0:
        min_votes = mymeta['bottom_votes_percand'] = min(roundcount.values())
        max_votes = mymeta['leading_votes_percand'] = max(roundcount.values())
    else:
        min_votes = mymeta['bottom_votes_percand'] = 0
        max_votes = mymeta['leading_votes_percand'] = 0
    if min_votes == max_votes:
        mymeta['penultimate_votes_percand'] = penultvotesper = max_votes
    else:
        mymeta['penultimate_votes_percand'] = penultvotesper = \
            min(votes for cand, votes in roundcount.items() if votes > min_votes)
    mymeta['starting_cands'] = candlist

    if len(roundcount.values()) > 0:
        mymeta['top_voteqty'] = min(roundcount.values())
        mymeta['bottom_voteqty'] = max(roundcount.values())
    else:
        mymeta['top_voteqty'] = 0
        mymeta['bottom_voteqty'] = 0

    # 5. Adding newly created "mymeta" to larger "roundmeta" variable
    rounds.append(roundcount)
    roundmeta.append(mymeta)
    bottomcands = [c for c, v in roundcount.items() if v <= min_votes]
    has_tie = False

    # * penultvotestot -- total topvotes among second-to-last-place
    #                     candidates
    # * penultvotesper -- per candidate topvotes among
    #                     second-to-last-place candidates
    # * bottomvotestot -- total topvotes among last-place candidates
    # * bottomvotesper -- per candidate topvotes among last-place
    #                     candidates

    bottomvotestot = sum(roundcount[c] for c in bottomcands if c in
                         roundcount)
    if len(roundcount) > 0:
        bottomvotesper = mbv = max(roundcount[cand] for cand in
                                   bottomcands if cand in roundcount)
    else:
        bottomvotesper = mbv = 0

    if len(bottomcands) > 1:
        roundmeta[-1]['bottomtie'] = bottomcands
        has_tie = True
        roundmeta[-1]['tiecandlist'] = bottomcands
        ntc = [cand for cand, votes in roundcount.items()
               if bottomvotesper < votes <= penultvotesper]

        penultvotestot = sum(roundcount[cand] for cand in ntc)

        # Batch elimination: Eliminate all candidates if the total top
        # score for all tied candidates in this round is less than the
        # total of any one candidate in subsequently higher total top
        # vote counts.
        if bottomvotestot <= penultvotesper:
            roundmeta[-1]['batch_elim'] = True
            roundmeta[-1]['eliminated'] = bottomcands
            unluckycand = None
            nextcands = list(set(candlist) - set(bottomcands))
            nextvotelines = _eliminate_cands_from_votelines(bottomcands, prunedvlns[:])
            if os.environ.get("ABIFTOOL_DEBUG"):
                print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem05: After eliminate_cands_from_votelines (batch)")
        else:
            # FIXME - develop better logic to calculate what happens
            #         with each possible advancing candidate than
            #         selecting the next candidate randomly
            roundmeta[-1]['random_elim'] = True
            unluckycand = random.choice(bottomcands)
            roundmeta[-1]['eliminated'] = [unluckycand]
            nextcands = list(set(candlist) - set([unluckycand]))
            nextvotelines = _eliminate_cands_from_votelines([unluckycand], prunedvlns[:])
            if os.environ.get("ABIFTOOL_DEBUG"):
                print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem06: After eliminate_cands_from_votelines (random)")
        thisroundloserlist = [unluckycand]
    else:
        roundmeta[-1]['eliminated'] = bottomcands
        nextcands = list(set(candlist) - set(bottomcands))
        nextvotelines = _eliminate_cands_from_votelines(bottomcands, prunedvlns)
        if os.environ.get("ABIFTOOL_DEBUG"):
            print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem07: After eliminate_cands_from_votelines (no tie)")
        thisroundloserlist = bottomcands
    # now populate 'all_eliminated'
    if "all_eliminated" not in roundmeta[-1]:
        roundmeta[-1]['all_eliminated'] = set()
    if len(roundmeta) > 1:
        roundmeta[-1]['all_eliminated'].update(roundmeta[-2]['all_eliminated'])
    if (len(roundmeta) > 1):
        for cand in roundmeta[-1]['eliminated']:
            roundmeta[-1]['all_eliminated'].add(cand)
    if thisroundloserlist != [None]:
        roundmeta[-1]['all_eliminated'].update(thisroundloserlist)

    # Calculate transfers of votes from eliminated candidates
    transfers = {}
    if bottomcands:
        # Isolate the votelines that will be transferred
        transferring_votelines = []
        for vln in prunedvlns:
            (top_cand, _) = _get_valid_topcand_qty(vln)
            if top_cand in bottomcands:
                transferring_votelines.append(vln)

        # For each eliminated candidate, see where their votes go
        for elim_cand in bottomcands:
            transfers[elim_cand] = {}
            # Get just the votelines for this one eliminated candidate
            elim_cand_votelines = []
            for vln in transferring_votelines:
                (top_cand, _) = _get_valid_topcand_qty(vln)
                if top_cand == elim_cand:
                    elim_cand_votelines.append(vln)

            if not elim_cand_votelines:
                continue

            # Eliminate the candidate from their own votelines
            # and find the next preference
            next_pref_votelines = _eliminate_cands_from_votelines(
                [elim_cand], elim_cand_votelines)

            # Tally the new top preferences
            for vln in next_pref_votelines:
                (next_cand, qty) = _get_valid_topcand_qty(vln)
                if next_cand:
                    transfers[elim_cand][next_cand] = \
                        transfers[elim_cand].get(next_cand, 0) + qty
                else:
                    # Exhausted
                    transfers[elim_cand]['exhausted'] = \
                        transfers[elim_cand].get('exhausted', 0) + qty
    roundmeta[-1]['transfers'] = transfers

    if canddict:
        # Calculate pairwise preferences on eliminated ballots
        elim_votelines = []
        if bottomcands:
            for vln in prunedvlns:
                (top_cand, _) = _get_valid_topcand_qty(vln)
                if top_cand in bottomcands:
                    elim_votelines.append(vln)

        if elim_votelines:
            # We need the full candidate dictionary, not just the list of names
            # It's passed down through the recursion now.
            next_cand_dict = {c: canddict[c] for c in nextcands if c in canddict}

            temp_abifmodel = {
                'votelines': elim_votelines,
                'candidates': next_cand_dict
            }
            elimcand_supporter_pairwise_results = pairwise_count_dict(temp_abifmodel)
            roundmeta[-1]['elimcand_supporter_pairwise_results'] = elimcand_supporter_pairwise_results
        else:
            roundmeta[-1]['elimcand_supporter_pairwise_results'] = {}

        # Calculate next choices for all remaining candidate.  This
        # was called "hypothetical transfers" when it was fist
        # written, because I hadn't thought about simply calling it
        # "next choices".
        next_choices = {}
        for remaining_cand in candlist:
            if remaining_cand not in bottomcands:  # Don't calculate for already eliminated candidates
                hyp_cand_votelines = []
                for vln in prunedvlns:
                    (top_cand, _) = _get_valid_topcand_qty(vln)
                    if top_cand == remaining_cand:
                        hyp_cand_votelines.append(vln)

                if hyp_cand_votelines:
                    next_choices[remaining_cand] = {}

                    # Eliminate the hypothetical candidate from their own votelines
                    hyp_next_pref_votelines = _eliminate_cands_from_votelines(
                        [remaining_cand], hyp_cand_votelines)

                    # Tally where their votes would go - use the ORIGINAL candidate list
                    # (not excluding the actually eliminated candidates, since we're asking
                    # "what if this candidate was eliminated INSTEAD?")
                    for vln in hyp_next_pref_votelines:
                        (next_cand, qty) = _get_valid_topcand_qty(vln)
                        if next_cand and next_cand in candlist and next_cand != remaining_cand:
                            # Count transfers to any candidate from
                            # the original round (including actually
                            # eliminated ones)
                            next_choices[remaining_cand][next_cand] = \
                                next_choices[remaining_cand].get(next_cand, 0) + qty
                        else:
                            # Exhausted
                            next_choices[remaining_cand]['exhausted'] = \
                                next_choices[remaining_cand].get('exhausted', 0) + qty

        roundmeta[-1]['next_choices'] = next_choices

    # This is where we determine if we need to add another layer of recursion
    if min_votes == max_votes:
        # This should be reached only if there's a tie between candidates
        winner = [c for c, v in roundcount.items() if v == max_votes]
        retval = (winner, rounds, roundmeta)
        roundmeta[-1]['winner'] = winner
        roundmeta[-1]['eliminated'] = set(
            mymeta['starting_cands']) - set(winner)
    elif max_votes > total_votes / 2:
        # This is the normal end of the IRV elimination cycle
        winner = [c for c, v in roundcount.items() if v == max_votes]
        retval = (winner, rounds, roundmeta)
        roundmeta[-1]['winner'] = winner
        roundmeta[-1]['eliminated'] = set(
            mymeta['starting_cands']) - set(winner)
    else:
        # We need another round, hence recursion
        t_rec0 = time.perf_counter()
        if os.environ.get("ABIFTOOL_DEBUG"):
            print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem08: Before recursive call to _irv_count_internal")
        (winner, nextrounds, nextmeta) = \
            _irv_count_internal(nextcands,
                                nextvotelines,
                                rounds=rounds,
                                roundmeta=roundmeta,
                                canddict=canddict)
        t_rec1 = time.perf_counter()
        if os.environ.get("ABIFTOOL_DEBUG"):
            print(f"[irv_tally]   recursion: {t_rec1 - t_rec0:.4f}s at depth={depth}")
        if os.environ.get("ABIFTOOL_DEBUG"):
            print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem09: After recursive call to _irv_count_internal")
        retval = (winner, rounds, roundmeta)
    t1 = time.perf_counter()
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"[irv_tally] Exiting _irv_count_internal: depth={depth}, elapsed={t1 - t0:.4f}s, cands={candlist}")
    return retval


def IRV_dict_from_jabmod(jabmod, include_irv_extra=False):
    t0 = time.perf_counter()
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem01: Entering IRV_dict_from_jabmod")
    retval = {}
    canddict = retval['canddict'] = jabmod['candidates']
    candlist = list(jabmod['candidates'].keys())
    votelines = jabmod['votelines']

    canddict_arg = canddict if include_irv_extra else None
    (retval['winner'], retval['rounds'], retval['roundmeta']) = \
        _irv_count_internal(candlist, votelines, roundnum=1, canddict=canddict_arg)

    # Sort candidate keys in each round by descending order of topranks
    if retval['rounds']:
        for idx, round_dict in enumerate(retval['rounds']):
            sorted_items = sorted(round_dict.items(), key=lambda item: item[1], reverse=True)
            retval['rounds'][idx] = {k: v for k, v in sorted_items}

    winner = retval['winner']
    if len(winner) > 1:
        winnerstr = " and ".join(canddict[w] for w in sorted(winner))
    elif len(winner) == 1:
        winnerstr = canddict[winner[0]]
    else:
        winnerstr = None
    retval['winnerstr'] = winnerstr

    retval['has_tie'] = any(
        "bottomtie" in rm for rm in retval.get("roundmeta", []))

    t1 = time.perf_counter()
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"[irv_tally] IRV_dict_from_jabmod: {t1 - t0:.4f}s for {len(votelines)} votelines, {len(candlist)} candidates")
    if os.environ.get("ABIFTOOL_DEBUG"):
        print(f"{datetime.datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]} [irv_tally] tgem10: Exiting IRV_dict_from_jabmod")
    return retval


def IRV_result_from_abifmodel(abifmodel):
    """Create IRV result with summary data for consistent display in CLI and web"""
    from . import convert_abif_to_jabmod
    if isinstance(abifmodel, str):
        jabmod = convert_abif_to_jabmod(abifmodel)
    else:
        jabmod = abifmodel

    # Get the basic IRV computation
    irv_dict = IRV_dict_from_jabmod(jabmod)

    # Add summary information
    result = {}
    result['irv_dict'] = irv_dict
    result['winner'] = irv_dict['winner']
    result['winner_name'] = irv_dict['winnerstr']

    # Get final round information
    if irv_dict['rounds'] and irv_dict['roundmeta']:
        final_round = irv_dict['rounds'][-1]
        final_meta = irv_dict['roundmeta'][-1]

        # Sort final round candidates by vote count
        final_candidates = sorted(final_round.items(), key=lambda x: x[1], reverse=True)

        result['final_round_candidates'] = final_candidates
        result['winner_votes'] = final_candidates[0][1] if final_candidates else 0
        result['runner_up'] = final_candidates[1][0] if len(final_candidates) > 1 else None
        result['runner_up_votes'] = final_candidates[1][1] if len(final_candidates) > 1 else 0

        # Summary statistics
        total_ballots = irv_dict['roundmeta'][0]['startingqty']
        result['total_ballots'] = total_ballots
        result['final_round_counted'] = final_meta['countedqty']
        result['final_round_exhausted'] = total_ballots - final_meta['countedqty']
        result['majority_threshold'] = total_ballots // 2 + 1
        result['num_rounds'] = len(irv_dict['rounds'])

        # Calculate percentages
        if total_ballots > 0:
            result['winner_percentage'] = (result['winner_votes'] / total_ballots) * 100
            result['runner_up_percentage'] = (result['runner_up_votes'] / total_ballots) * 100 if result['runner_up_votes'] else 0
            result['final_round_counted_percentage'] = (result['final_round_counted'] / total_ballots) * 100
            result['final_round_exhausted_percentage'] = (result['final_round_exhausted'] / total_ballots) * 100
            result['majority_threshold_percentage'] = (result['majority_threshold'] / total_ballots) * 100
        else:
            result['winner_percentage'] = 0
            result['runner_up_percentage'] = 0
            result['final_round_counted_percentage'] = 0
            result['final_round_exhausted_percentage'] = 0
            result['majority_threshold_percentage'] = 0

    return result


def get_IRV_report(IRV_dict):
    winner = IRV_dict['winner']
    rounds = IRV_dict['rounds']
    canddict = IRV_dict['canddict']
    output = ""

    for round_num, round_results in enumerate(rounds):
        thisroundmeta = IRV_dict['roundmeta'][round_num]
        eliminated = thisroundmeta.get('eliminated')
        starting_cands_str = ", ".join(
            sorted(thisroundmeta.get('starting_cands')))
        output += f"\nRound {round_num + 1}:\n"
        output += f"  Starting cands: {starting_cands_str}\n"
        output += f"  Total starting votes: {thisroundmeta['startingqty']}\n"
        output += f"  Exhausted votes: {thisroundmeta['exhaustedqty']}\n"
        output += f"  Overvotes: {thisroundmeta['overvoteqty']}\n"
        output += f"  Total counted votes: {thisroundmeta['countedqty']}\n"
        output += f"  Votes by candidate:\n"
        for candidate, votes in round_results.items():
            output += f"    {candidate}: {votes}\n"
        output += f"  Eliminated this round: {', '.join(sorted(eliminated))}\n"

    if len(winner) > 1:
        output += f"The IRV winners are {' and '.join(sorted(winner))}\n"
    elif len(winner) == 1:
        output += f"The IRV winner is {winner[0]}\n"
    else:
        output += f"No IRV winner due to blank preferences."
    return output


def main():
    parser = argparse.ArgumentParser(description='IRV calculator')
    parser.add_argument('input_file', help='Input .abif')
    parser.add_argument('-j', '--json', action="store_true",
                        help='Provide raw json output')

    args = parser.parse_args()
    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext)
    IRV_dict = IRV_dict_from_jabmod(jabmod)
    output = ""
    if args.json:
        output += json.dumps(clean_dict(IRV_dict), indent=4)
    else:
        output += candlist_text_from_abif(jabmod)
        output += get_IRV_report(IRV_dict)
    print(output)


if __name__ == "__main__":
    main()
