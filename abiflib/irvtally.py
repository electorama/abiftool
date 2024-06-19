#!/usr/bin/env python3
from abiflib import *
import argparse
from copy import deepcopy
import pathlib
from pprint import pprint, pformat
import sys

def _eliminate_cands_from_votelines(candlist, votelines):
    '''Returns copy of votelines without candidate(s) in candlist'''
    retval = deepcopy(votelines)
    for cand in candlist:
        for vln in retval:
            if cand in vln['prefs']:
                del vln['prefs'][cand]
    return retval


def _get_valid_topcand_qty(voteline):
    prefs = voteline['prefs']
    rlist = sorted(prefs.keys(), key=lambda key: prefs[key]['rank'])
    overvote = 0

    if len(rlist) > 0:
        x = 0
        xtok = rlist[x]
        xrank = prefs[xtok]['rank']
        y = len(rlist)
        yrank = 9999999999 # close enough to infinity
        # this technique should find the index of the last candidate
        # in the rlist array that has the same rank as the first
        # candidate in rlist.
        while yrank > xrank:
            y += -1
            ytok = rlist[y]
            yrank = prefs[ytok]['rank']
        # if x < y, this means there is two or more elements in the
        # rlist array with the same rank
        if x == y:
            rcand = rlist[x]
        else:
            overvote += voteline['qty']
            klist = rlist[y+1:]
            nextprefs = {k: prefs[k] for k in klist if k in prefs}
            nextvln = {
                'qty': voteline['qty'],
                'prefs': nextprefs
            }
            (rcand, rqty, nextov) = _get_valid_topcand_qty(nextvln)
            overvote += nextov
    else:
        rcand = prefs
    rqty = voteline['qty']
    return (rcand, rqty, overvote)


def _irv_count_internal(candlist, votelines, rounds=None, roundmeta=None):
    """
    IRV count of given votelines
    """
    if rounds is None:
        rounds = []
    if roundmeta is None:
        roundmeta = []
    roundcount = {cand: 0 for cand in candlist}
    mymeta = {}
    # FIXME: stop resetting the baseline exhausted ballots to zero
    # every round.  As of this writing in June 2024, the full ballot
    # set is passed to _eliminate_cands_from_votelines in every round
    # (regardless of prior eliminations).  Since tied rankings are not
    # allowed in IRV, these rankings are supposed to be skipped.
    # HOWEVER, when a candidate is eliminated who shows up as a tie on
    # some ballots, these ranking tiers magically become valid in
    # _irv_count_internal, since the remaining candidate in the tied
    # ranking tier may not have been eliminated yet.  I'm pretty sure
    # that in most IRV implementations, once an invalid ranking tier
    # is encountered, the entire list of voter preferences is
    # eliminated from consideration.
    mymeta['exhaustedqty'] = 0
    mymeta['overvoteqty'] = 0
    mymeta['ballotcount'] = 0
    for (ckey, vln) in enumerate(votelines):
        (rcand, rqty, overvote) = _get_valid_topcand_qty(vln)
        mymeta['ballotcount'] += rqty
        if rcand:
            roundcount[rcand] += rqty
        else:
            mymeta['exhaustedqty'] += rqty
        if overvote:
            mymeta['overvoteqty'] += overvote


    # Check for majority of unexhausted votelines
    total_votes = sum(roundcount.values())
    mymeta['remainingqty'] = total_votes
    winner = None
    for cand, votes in roundcount.items():
        if votes > total_votes / 2:
            winner = cand
    rounds.append(roundcount)
    roundmeta.append(mymeta)
    if winner:
        retval = (winner, rounds, roundmeta)
    else:
        min_votes = min(roundcount.values())
        max_votes = max(roundcount.values())
        if min_votes == max_votes:
            winner = [c for c, v in roundcount.items() if v == max_votes]
            retval = (winner, rounds, roundmeta)
        else:
            bottomcands = [c for c, v in roundcount.items() if v <= min_votes]
            nextcands = list(set(candlist) - set(bottomcands))
            nextvotelines = \
                _eliminate_cands_from_votelines(bottomcands, votelines)
            (winner, nextrounds, nextmeta) = \
                _irv_count_internal(nextcands,
                                    nextvotelines,
                                    rounds=rounds,
                                    roundmeta=roundmeta)
            retval = (winner, rounds, roundmeta)
    return retval


def IRV_dict_from_jabmod(jabmod):
    retval = {}
    candlist = deepcopy(jabmod['candidates'])
    votelines = deepcopy(jabmod['votelines'])
    (retval['winner'], retval['rounds'], retval['roundmeta']) = \
        _irv_count_internal(candlist, votelines)
    retval['eliminated'] = []

    # Find the eliminated candidate(s) in each round
    for round_num, round_results in enumerate(retval['rounds']):
        if round_num < len(retval['rounds']) - 1:
            remainingset = set(retval['rounds'][round_num+1].keys())
            eliminated = list(set(round_results.keys()) - remainingset)
        else:
            winnerset = set(list(retval['winner']))
            eliminated = list(set(round_results.keys()) - winnerset)
        retval['eliminated'].append(eliminated)
    abiflib_test_log('IRV_dict_from_jabmod retval:')
    abiflib_test_log(pformat(retval))
    return retval


def get_IRV_report(IRV_dict):
    winner = IRV_dict['winner']
    rounds = IRV_dict['rounds']
    eliminated = IRV_dict['eliminated']
    output = ""

    for round_num, round_results in enumerate(rounds):
        thisroundmeta = IRV_dict['roundmeta'][round_num]
        output += f"\nRound {round_num + 1}:\n"
        output += f"  Total unexhausted votes: {thisroundmeta['remainingqty']}\n"
        output += f"  Exhausted votes: {thisroundmeta['exhaustedqty']}\n"
        output += f"  Overvotes: {thisroundmeta['overvoteqty']}\n"
        output += f"  Votes by candidate:\n"
        for candidate, votes in round_results.items():
            output += f"    {candidate}: {votes}\n"
        output += f"  Eliminated: {', '.join(eliminated[round_num])}\n"

    if type(winner) == str:
        output += f"The IRV winner is {winner}\n"
    else:
        output += f"The IRV winners are {' and '.join(winner)}"
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
    if args.json:
        output = json.dumps(IRV_dict, indent=4)
    else:
        output = get_IRV_report(IRV_dict)
    print(output)


if __name__ == "__main__":
    main()
