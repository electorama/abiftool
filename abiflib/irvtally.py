#!/usr/bin/env python3
from abiflib import *
import argparse
from copy import deepcopy
import pathlib
from pprint import pprint, pformat
import sys

def _eliminate_cands_from_votelines(candlist, votelines):
    retval = deepcopy(votelines)
    for cand in candlist:
        for vln in retval:
            if cand in vln['prefs']:
                del vln['prefs'][cand]
    return retval


def _get_ranked_cands_from_voteline(voteline):
    prefs = voteline['prefs']
    retval = sorted(prefs.keys(), key=lambda key: prefs[key]['rank'])
    return retval


def _irv_count_internal(candlist, votelines, rounds=None):
    """
    IRV count of given votelines
    """
    if rounds is None:
        rounds = []
    roundcount = {cand: 0 for cand in candlist}
    for (ckey, vln) in enumerate(votelines):
        rlist = _get_ranked_cands_from_voteline(vln)
        if len(rlist) > 0:
            roundcount[rlist[0]] += vln['qty']
    # Check for majority of remaining votelines
    total_votes = sum(roundcount.values())
    winner = None
    for cand, votes in roundcount.items():
        if votes > total_votes / 2:
            winner = cand
    if not winner:
        min_votes = min(roundcount.values())
        max_votes = max(roundcount.values())
        if min_votes == max_votes:
            winner = [c for c, v in roundcount.items() if v == max_votes]
            return (winner, [roundcount])
        else:
            bottomcands = [c for c, v in roundcount.items() if v <= min_votes]
            nextcands = list(set(candlist) - set(bottomcands))
            nextvotelines = \
                _eliminate_cands_from_votelines(bottomcands, votelines)
            (winner, nextrounds) = \
                _irv_count_internal(nextcands, nextvotelines, rounds)
            return (winner, [roundcount] + nextrounds)
    else:
        rounds.append(roundcount)
        return (winner, rounds)
    return None


def IRV_count_from_jabmod(jabmod):
    retval = {}
    candlist = deepcopy(jabmod['candidates'])
    votelines = deepcopy(jabmod['votelines'])
    (retval['winner'], retval['rounds']) = \
        _irv_count_internal(candlist, votelines)
    retval['eliminated'] = []

    # Find the eliminated candidate(s) in each round
    for round_num, round_results in enumerate(retval['rounds'], start=1):
        if round_num < len(retval['rounds']):
            remainingset = set(retval['rounds'][round_num])
            eliminated = list(set(round_results) - remainingset)
            retval['eliminated'].append([eliminated, round_num])
        else:
            eliminated = list(round_results)
            retval['eliminated'].append(eliminated)
    abiflib_test_log(f"IRV_count_from_jabmod {retval=}")
    return retval


def get_IRV_report(jabmod):
    IRV_dict = IRV_count_from_jabmod(jabmod)
    winner = IRV_dict['winner']
    rounds = IRV_dict['rounds']
    output = ""

    for round_num, round_results in enumerate(rounds, start=1):
        output += f"\nRound {round_num}:\n"
        for candidate, votes in round_results.items():
            output += f"  {candidate}: {votes}\n"
        # REMOVE ME
        # TODO: replace all of this duplicated calculation with
        #       results calculated in IRV_count_from_jabmod
        if round_num < len(rounds):
            eliminated = set(round_results) - set(rounds[round_num])
            abiflib_test_log(f"{eliminated=}")
            output += f"  Eliminated: {eliminated}\n"
        # REMOVE COMMENT ABOVE

    output += f"The IRV winner is {winner}\n"
    return output


def main():
    parser = argparse.ArgumentParser(description='IRV calculator')
    parser.add_argument('input_file', help='Input .abif')

    args = parser.parse_args()
    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext)
    output = get_IRV_report(jabmod)
    print(output)


if __name__ == "__main__":
    main()
