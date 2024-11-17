#!/usr/bin/env python3
from abiflib import *
import argparse
from copy import deepcopy
import pathlib
from pprint import pprint, pformat
import random
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
        try:
            abiflib_test_log(f"{prefs.keys()=}")
            rlist = sorted(prefs.keys(), key=lambda key: prefs[key]['rank'])
        except:
            #import json
            #print(json.dumps(prefs, indent=2))
            abiflib_test_logblob(prefs)
            raise
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


def _irv_count_internal(candlist, votelines, rounds=None, roundmeta=None, roundnum=None):
    """
    IRV count of given votelines

    This returns the following triple:
    * winner - the winner(s) of this round, if there are any
    * rounds - round-by-round votecounts
    * roundmeta - metadata associated with all rounds
    """
    # 1. initializing/calculating rounds, roundmeta, and roundcount
    # abiflib_test_log("1. initializing/calculating rounds, roundmeta, and roundcount")
    # 1a. rounds, roundmeta, and roundnum are passed in recursively; init if needed
    # abiflib_test_log(pformat(roundmeta))
    if rounds is None:
        rounds = []
    if roundmeta is None:
        roundmeta = []
    # 1b. populating roundcount, which contains all remaining candidates in this round
    roundcount = {cand: 0 for cand in candlist}

    # 2. initializing mymeta, which will eventually be appended to roundmeta
    # abiflib_test_log("2. Initializing mymeta")
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
    #print(f"{candlist=}")
    (ov, prunedvlns) = _discard_toprank_overvotes(votelines)
    mymeta['overvoteqty'] += ov
    for (i, vln) in enumerate(prunedvlns):
        (rcand, rqty) = _get_valid_topcand_qty(vln)

        mymeta['ballotcount'] += rqty
        if rcand:
            roundcount[rcand] += rqty
        else:
            mymeta['exhaustedqty'] += rqty
    total_votes = sum(roundcount.values())
    mymeta['countedqty'] = total_votes - mymeta['exhaustedqty']

    # 4. Other mymeta stuff
    winner = None
    min_votes = mymeta['bottom_votes_percand'] = min(roundcount.values())
    max_votes = mymeta['leading_votes_percand'] = max(roundcount.values())
    if min_votes == max_votes:
        mymeta['penultimate_votes_percand'] = penultvotesper = max_votes
    else:
        mymeta['penultimate_votes_percand'] = penultvotesper = \
            min(votes for cand, votes in roundcount.items() if votes > min_votes)
    mymeta['starting_cands'] = candlist
    mymeta['top_voteqty'] = min(roundcount.values())
    mymeta['bottom_voteqty'] = max(roundcount.values())
    # abiflib_test_log("votelines=")
    # abiflib_test_log(json.dumps(votelines, indent=4))

    # 5. Adding newly created "mymeta" to larger "roundmeta" variable
    rounds.append(roundcount)
    roundmeta.append(mymeta)
    bottomcands = [c for c, v in roundcount.items() if v <= min_votes]
    has_tie = False

    # abiflib_test_log(f"{roundnum=}")
    # abiflib_test_log(f"{roundcount=}")
    # abiflib_test_log(f"{roundcount.items()=}")

    # * penultvotestot -- total topvotes among second-to-last-place
    #                     candidates
    # * penultvotesper -- per candidate topvotes among
    #                     second-to-last-place candidates
    # * bottomvotestot -- total topvotes among last-place candidates
    # * bottomvotesper -- per candidate topvotes among last-place
    #                     candidates

    bottomvotestot = sum(roundcount[c] for c in bottomcands if c in
                         roundcount)
    bottomvotesper = mbv = max(roundcount[cand] for cand in
                               bottomcands if cand in roundcount)
    #abiflib_test_log(f"{bottomvotestot=}")
    #abiflib_test_log(f"{bottomvotesper=}")

    if len(bottomcands) > 1:
        roundmeta[-1]['bottomtie'] = bottomcands
        has_tie = True
        roundmeta[-1]['tiecandlist'] = bottomcands
        ntc = [cand for cand, votes in roundcount.items() \
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
            nextvotelines = \
                _eliminate_cands_from_votelines(bottomcands, deepcopy(prunedvlns))
        else:
            # FIXME - develop better logic to calculate what happens
            #         with each possible advancing candidate than
            #         selecting the next candidate randomly
            roundmeta[-1]['random_elim'] = True
            unluckycand = random.choice(bottomcands)
            roundmeta[-1]['eliminated'] = [ unluckycand ]
            nextcands = list(set(candlist) - set([unluckycand]))
            nextvotelines = \
                _eliminate_cands_from_votelines([unluckycand], deepcopy(prunedvlns))
        thisroundloserlist = [ unluckycand ]
    else:
        roundmeta[-1]['eliminated'] = bottomcands
        nextcands = list(set(candlist) - set(bottomcands))
        nextvotelines = \
            _eliminate_cands_from_votelines(bottomcands, prunedvlns)
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

    # This is where we determine if we need to add another layer of recursion
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
        _irv_count_internal(candlist, votelines, roundnum = 1)

    winner = retval['winner']
    if len(winner) > 1:
        winnerstr = " and ".join(canddict[w] for w in sorted(winner))
    else:
        winnerstr = canddict[winner[0]]
    retval['winnerstr'] = winnerstr

    retval['has_tie'] = any(
        "bottomtie" in rm for rm in retval.get("roundmeta", []))

    #abiflib_test_log('IRV_dict_from_jabmod retval:')
    #abiflib_test_log(pformat(retval))
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
