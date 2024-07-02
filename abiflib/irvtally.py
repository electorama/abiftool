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


def _discard_toprank_overvotes(votelines):
    retval = deepcopy(votelines)
    overvotes = 0
    for i, vln in enumerate(retval):
        prefs = vln['prefs']
        rlist = sorted(prefs.keys(), key=lambda key: prefs[key]['rank'])
        if len(rlist) > 0:
            x = 0
            xtok = rlist[x]
            xrank = prefs[xtok]['rank']
            y = len(rlist)
            yrank = 9999999999  # close enough to infinity
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
                overvotes += vln['qty']
                del retval[i]
        else:
            rcand = prefs

    return (overvotes, retval)


def _get_valid_topcand_qty(voteline):
    prefs = voteline['prefs']
    rlist = sorted(prefs.keys(), key=lambda key: prefs[key]['rank'])

    if len(rlist) > 0:
        x = 0
        xtok = rlist[x]
        xrank = prefs[xtok]['rank']
        y = len(rlist)
        yrank = 9999999999  # close enough to infinity
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
            klist = rlist[y+1:]
            nextprefs = {k: prefs[k] for k in klist if k in prefs}
            nextvln = {
                'qty': voteline['qty'],
                'prefs': nextprefs
            }
            (rcand, rqty) = _get_valid_topcand_qty(nextvln)
    else:
        rcand = prefs
    rqty = voteline['qty']
    return (rcand, rqty)


def _irv_count_internal(candlist, votelines, rounds=None, roundmeta=None):
    """
    IRV count of given votelines

    This returns the following triple:
    * winner - the winner(s) of this round, if there are any
    * rounds - round-by-round votecounts
    * roundmeta - metadata associated with all rounds
    """
    abiflib_test_log("1. looking for all_eliminated in roundmeta:")
    abiflib_test_log(pformat(roundmeta))
    if rounds is None:
        rounds = []
    if roundmeta is None:
        roundmeta = []
    roundcount = {cand: 0 for cand in candlist}

    # initializing mymeta, which will eventually be appended to roundmeta
    mymeta = {}
    mymeta['exhaustedqty'] = 0
    mymeta['overvoteqty'] = 0
    mymeta['ballotcount'] = 0
    mymeta['starting_cands'] = candlist
    mymeta['startingqty'] = sum(vln['qty'] for vln in votelines)

    (ov, prunedvlns) = _discard_toprank_overvotes(votelines)
    mymeta['overvoteqty'] += ov
    for (i, vln) in enumerate(prunedvlns):
        # (rcand, rqty, overvote) = _get_valid_topcand_qty(vln)
        (rcand, rqty) = _get_valid_topcand_qty(vln)

        mymeta['ballotcount'] += rqty
        if rcand:
            roundcount[rcand] += rqty
        else:
            mymeta['exhaustedqty'] += rqty

    total_votes = sum(roundcount.values())
    mymeta['countedqty'] = total_votes - mymeta['exhaustedqty']
    winner = None
    rounds.append(roundcount)
    roundmeta.append(mymeta)
    min_votes = min(roundcount.values())
    max_votes = max(roundcount.values())
    roundmeta[-1]['top_voteqty'] = min(roundcount.values())
    roundmeta[-1]['bottom_voteqty'] = max(roundcount.values())
    bottomcands = [c for c, v in roundcount.items() if v <= min_votes]
    if "all_eliminated" not in roundmeta[-1]:
        roundmeta[-1]['all_eliminated'] = set()
    if len(roundmeta) > 1:
        roundmeta[-1]['all_eliminated'].update(roundmeta[-2]['all_eliminated'])

    if (len(roundmeta) > 1):
        roundmeta[-1]['all_eliminated'].update(
            list(roundmeta[-2]['eliminated']))
        try:
            roundmeta[-1]['all_eliminated'].update(
                list(roundmeta[-2]['eliminated']))
        except TypeError:
            print(roundmeta[-2]['eliminated'])
            print(pformat(roundmeta))
            sys.exit()
    try:
        roundmeta[-1]['all_eliminated'].update(bottomcands)
    except TypeError:
        print(f"{bottomcands=}")
        sys.exit()
    if min_votes == max_votes:
        # This should be reached only if there's a tie between candidates
        winner = [c for c, v in roundcount.items() if v == max_votes]
        retval = (winner, rounds, roundmeta)
        roundmeta[-1]['winner'] = winner
        roundmeta[-1]['eliminated'] = set(mymeta['starting_cands']) - set(winner)
    elif max_votes > total_votes / 2:
        # This is the normal end of the IRV elimination cycle
        winner = [c for c, v in roundcount.items() if v == max_votes]
        retval = (winner, rounds, roundmeta)
        roundmeta[-1]['winner'] = winner
        roundmeta[-1]['eliminated'] = set(mymeta['starting_cands']) - set(winner)
    else:
        # We need another round, hence recursion
        roundmeta[-1]['eliminated'] = bottomcands
        nextcands = list(set(candlist) - set(bottomcands))
        nextvotelines = \
            _eliminate_cands_from_votelines(bottomcands, prunedvlns)
        (winner, nextrounds, nextmeta) = \
            _irv_count_internal(nextcands,
                                nextvotelines,
                                rounds=rounds,
                                roundmeta=roundmeta)
        retval = (winner, rounds, roundmeta)
    return retval


def IRV_dict_from_jabmod(jabmod):
    retval = {}
    canddict = retval['canddict'] = jabmod['candidates']
    candlist = list(jabmod['candidates'].keys())
    votelines = deepcopy(jabmod['votelines'])
    (retval['winner'], retval['rounds'], retval['roundmeta']) = \
        _irv_count_internal(candlist, votelines)

    winner = retval['winner']
    if len(winner) > 1:
        winnerstr = " and ".join(canddict[w] for w in sorted(winner))
    else:
        winnerstr = canddict[winner[0]]
    retval['winnerstr'] = winnerstr

    abiflib_test_log('IRV_dict_from_jabmod retval:')
    abiflib_test_log(pformat(retval))
    return retval


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
    else:
        output += f"The IRV winner is {winner[0]}\n"
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
