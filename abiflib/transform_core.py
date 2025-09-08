#!/usr/bin/env python3
"""transform_core.py - Method-agnostic ballot transformations for abiflib

This module centralizes cross-format ballot conversions so that tally
modules (IRV/RCV, Condorcet/Copeland, Approval, etc.) can delegate
transform policy to a single place.

Public functions:
- ranked_to_choose_many_favorite_viable_half(abifmodel)
- choose_many_to_ranked_least_approval_first(abifmodel, tie_breaker='token')

Both functions return a new jabmod and attach `_conversion_meta` for
provenance. Callers may choose to attach method-specific notices.
"""

from abiflib.util import find_ballot_type
from abiflib.fptp_tally import FPTP_result_from_abifmodel
import copy


def ranked_to_choose_many_favorite_viable_half(abifmodel):
    """Convert ranked/rated ballots to approval (choose_many) using
    favorite_viable_half algorithm.

    Returns a new jabmod with approvals and `_conversion_meta`.
    """
    # Step 1: FPTP results to determine viable candidates
    fptp_results = FPTP_result_from_abifmodel(abifmodel)
    total_valid_votes = fptp_results['total_votes_recounted']
    ballot_type = find_ballot_type(abifmodel)

    # Step 2: Determine number of viable candidates using iterative Hare quota
    sorted_candidates = sorted(
        ((cand, votes) for cand, votes in fptp_results['toppicks'].items() if cand is not None),
        key=lambda x: x[1], reverse=True)

    if not sorted_candidates:
        approval_jabmod = copy.deepcopy(abifmodel)
        approval_jabmod['votelines'] = []
        return approval_jabmod

    frontrunner_votes = sorted_candidates[0][1]
    number_of_viable_candidates = 2
    for seats in range(2, len(sorted_candidates) + 2):
        quota = total_valid_votes // seats
        if frontrunner_votes > quota:
            number_of_viable_candidates = seats
            break
    if number_of_viable_candidates == 2 and frontrunner_votes <= (total_valid_votes // 2):
        number_of_viable_candidates = min(len(sorted_candidates), 10)

    viable_candidates = [sorted_candidates[i][0]
                         for i in range(min(number_of_viable_candidates, len(sorted_candidates)))]
    viable_candidate_maximum = (len(viable_candidates) + 1) // 2

    # Step 4: Create new approval jabmod by converting votelines
    approval_jabmod = copy.deepcopy(abifmodel)
    approval_jabmod['votelines'] = []

    for vline in abifmodel.get('votelines', []):
        ranked_prefs = []
        for cand, prefs in vline.get('prefs', {}).items():
            if 'rank' in prefs:
                ranked_prefs.append((cand, prefs['rank']))
        ranked_prefs.sort(key=lambda x: x[1])
        if not ranked_prefs:
            continue
        top_rank = ranked_prefs[0][1]
        top_candidates = [cand for cand, rank in ranked_prefs if rank == top_rank]
        if len(top_candidates) > 1:
            # Skip overvoted ballots at top rank
            continue

        vcm_viable_candidates_on_ballot = []
        for candidate, _rank in ranked_prefs:
            if candidate in viable_candidates:
                vcm_viable_candidates_on_ballot.append(candidate)
                if len(vcm_viable_candidates_on_ballot) == viable_candidate_maximum:
                    break

        if not vcm_viable_candidates_on_ballot:
            approvals = []
        else:
            cutoff_candidate = vcm_viable_candidates_on_ballot[-1]
            approvals = []
            for candidate, _rank in ranked_prefs:
                approvals.append(candidate)
                if candidate == cutoff_candidate:
                    break

        new_prefs = {candidate: {'rating': 1, 'rank': 1} for candidate in approvals}
        if new_prefs:
            new_vline = {'qty': vline.get('qty', 0), 'prefs': new_prefs}
            if 'prefstr' in vline:
                approved_cands = list(new_prefs.keys())
                new_vline['prefstr'] = '='.join(approved_cands) + '/1'
            approval_jabmod['votelines'].append(new_vline)

    total_ballots = sum(vline.get('qty', 0) for vline in abifmodel.get('votelines', []))

    approval_jabmod['_conversion_meta'] = {
        'method': 'favorite_viable_half',
        'original_ballot_type': ballot_type,
        'viable_candidates': viable_candidates,
        'viable_candidate_maximum': viable_candidate_maximum,
        'total_ballots': total_ballots,
        'candidate_names': abifmodel.get('candidates', {})
    }
    return approval_jabmod


def _compute_approval_counts_for_order(abifmodel):
    """Compute approval counts dict for approval/choose_many jabmod."""
    counts = {}
    for cand in abifmodel.get('candidates', {}).keys():
        counts[cand] = 0
    for vline in abifmodel.get('votelines', []):
        qty = vline.get('qty', 0)
        for cand, prefs in vline.get('prefs', {}).items():
            is_approved = False
            if 'rating' in prefs and prefs['rating'] == 1:
                is_approved = True
            elif 'rank' in prefs and prefs['rank'] == 1:
                is_approved = True
            if is_approved:
                counts[cand] = counts.get(cand, 0) + qty
    return counts


def _get_order_least_approval_first(abifmodel, tie_breaker: str = 'token'):
    """Deterministic global order by ascending total approvals.

    Converts to approval first if needed using favorite_viable_half.
    """
    bt = find_ballot_type(abifmodel)
    # Only convert ranked to approval; choose_one is already effectively binary at rank 1
    if bt == 'ranked':
        abifmodel = ranked_to_choose_many_favorite_viable_half(abifmodel)
    elif bt in ('choose_many', 'choose_one'):
        pass
    else:
        raise ValueError(f"Unsupported ballot_type for order computation: {bt}")
    counts = _compute_approval_counts_for_order(abifmodel)
    items = [(tok, cnt) for tok, cnt in counts.items() if tok is not None]
    if tie_breaker == 'token':
        items.sort(key=lambda x: (x[1], x[0]))
    else:
        items.sort(key=lambda x: (x[1], x[0]))
    return [tok for tok, _ in items]


def choose_many_to_ranked_least_approval_first(abifmodel, tie_breaker: str = 'token'):
    """Build ranked ballots from choose_many ballots (least_approval_first).

    - Global order is ascending by total approvals (fewest approvals rank highest).
    - Each ballot ranks only its approved candidates in that order.
    - Returns a new jabmod with ranked prefs and attaches `_conversion_meta`.
    """
    bt = find_ballot_type(abifmodel)
    base_for_counts = abifmodel
    # Only convert ranked; treat choose_one as binary approvals (rank==1)
    if bt == 'ranked':
        base_for_counts = ranked_to_choose_many_favorite_viable_half(abifmodel)
    elif bt in ('choose_many', 'choose_one'):
        pass
    else:
        raise ValueError(f"Unsupported ballot_type for choose_many→ranked: {bt}")

    order = _get_order_least_approval_first(base_for_counts, tie_breaker=tie_breaker)

    ranked_jabmod = copy.deepcopy(abifmodel)
    ranked_jabmod['votelines'] = []
    for vline in abifmodel.get('votelines', []):
        qty = vline.get('qty', 0)
        prefs = vline.get('prefs', {})
        approved = []
        for tok, p in prefs.items():
            if isinstance(p, dict):
                if ('rating' in p and p['rating'] == 1) or ('rank' in p and p['rank'] == 1):
                    approved.append(tok)
        ordered = [tok for tok in order if tok in approved]
        new_prefs = {tok: {'rank': i} for i, tok in enumerate(ordered, start=1)}
        new_vline = {'qty': qty, 'prefs': new_prefs}
        if ordered:
            new_vline['prefstr'] = '>'.join(ordered)
        ranked_jabmod['votelines'].append(new_vline)

    ranked_jabmod['_conversion_meta'] = {
        'method': 'least_approval_first',
        'original_ballot_type': find_ballot_type(abifmodel),
        'parameters': {
            'basis': 'ascending_total_approvals',
            'tie_breaker': tie_breaker,
        }
    }
    return ranked_jabmod


def ranked_to_choose_many_all_ranked_approved(abifmodel):
    """Simple ranked→choose_many conversion.

    Approve all candidates that appear with any rank on a ballot; unranked
    candidates are not approved. Does not attach conversion metadata and
    avoids emitting notices upstream.
    """
    bt = find_ballot_type(abifmodel)
    if bt == 'choose_many':
        return abifmodel
    approval_jabmod = copy.deepcopy(abifmodel)
    approval_jabmod['votelines'] = []
    for vline in abifmodel.get('votelines', []):
        qty = vline.get('qty', 0)
        prefs = vline.get('prefs', {})
        approved = [tok for tok, p in prefs.items() if isinstance(p, dict) and ('rank' in p)]
        new_prefs = {tok: {'rating': 1, 'rank': 1} for tok in approved}
        new_vline = {'qty': qty, 'prefs': new_prefs}
        if approved:
            new_vline['prefstr'] = '='.join(approved) + '/1'
        approval_jabmod['votelines'].append(new_vline)
    # Attach conversion metadata so callers can emit a notice
    approval_jabmod['_conversion_meta'] = {
        'method': 'all_ranked_approved',
        'original_ballot_type': bt,
        'total_ballots': sum(v.get('qty', 0) for v in abifmodel.get('votelines', [])),
        'candidate_names': abifmodel.get('candidates', {})
    }
    return approval_jabmod
