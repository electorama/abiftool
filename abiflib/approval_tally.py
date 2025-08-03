#!/usr/bin/env python3
''' abiflib/approval_tally.py - Functions for tallying approval voting elections '''

# Copyright (c) 2025 Rob Lanphier
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

from abiflib.core import convert_abif_to_jabmod
from abiflib.util import clean_dict, candlist_text_from_abif
from abiflib.fptp_tally import FPTP_result_from_abifmodel
import copy
import json
from pprint import pprint
import re
import sys
import urllib.parse
import argparse
import pathlib


def has_approval_data(abifmodel):
    """Detect if jabmod contains native approval data."""
    # Check for binary 0/1 scores, equal rankings with approval indicators
    # Look for patterns like: candA=candB/1>candC/0

    for vline in abifmodel['votelines']:
        has_binary_scores = False
        has_equal_ranks = False

        for cand, prefs in vline['prefs'].items():
            # Check for binary ratings (0 or 1)
            if 'rating' in prefs and prefs['rating'] in [0, 1]:
                has_binary_scores = True

            # Check for equal rankings (multiple candidates with same rank)
            rank = prefs.get('rank')
            if rank is not None:
                same_rank_count = sum(1 for c, p in vline['prefs'].items()
                                    if p.get('rank') == rank)
                if same_rank_count > 1:
                    has_equal_ranks = True

        if has_binary_scores or has_equal_ranks:
            return True

    return False


def has_only_rankings(abifmodel):
    """Detect if jabmod contains only ranked preferences."""
    # Check for rank-only data without scores or binary patterns

    for vline in abifmodel['votelines']:
        for cand, prefs in vline['prefs'].items():
            # If any candidate has a rating, it's not rank-only
            if 'rating' in prefs:
                return False

    return True


def detect_approval_method(abifmodel):
    """Auto-detect appropriate approval calculation method."""
    # Returns 'native' or 'simulate' based on ballot content

    if has_approval_data(abifmodel):
        return 'native'
    elif has_only_rankings(abifmodel):
        return 'simulate'
    else:
        # Mixed data - default to native if ratings exist
        return 'native'


def approval_result_from_abifmodel(abifmodel, method='auto'):
    """Calculate approval voting results from jabmod."""

    if method == 'auto':
        method = detect_approval_method(abifmodel)

    if method == 'native':
        return _native_approval_result(abifmodel)
    elif method in ['simulate', 'droop_strategic']:
        return _simulated_approval_result(abifmodel)
    else:
        raise ValueError(f"Unknown approval method: {method}")


def _native_approval_result(abifmodel):
    """Calculate approval results from native approval ballots."""

    approval_counts = {}
    # Initialize all candidates with 0 approvals
    for cand_token in abifmodel['candidates'].keys():
        approval_counts[cand_token] = 0

    invalid_ballots = 0
    total_ballots_processed = abifmodel['metadata']['ballotcount']

    for vline in abifmodel['votelines']:
        ballot_qty = vline['qty']

        # For native approval, candidates with rating=1 or rank=1 are approved
        approved_candidates = []

        for cand, prefs in vline['prefs'].items():
            is_approved = False

            # Check rating-based approval (rating = 1)
            if 'rating' in prefs and prefs['rating'] == 1:
                is_approved = True

            # Check rank-based approval (rank = 1, allowing ties)
            elif 'rank' in prefs and prefs['rank'] == 1:
                is_approved = True

            if is_approved:
                approved_candidates.append(cand)

        # Apply approvals
        for cand in approved_candidates:
            approval_counts[cand] += ballot_qty

    # Calculate winner(s)
    max_approvals = 0
    winners = []
    for cand, approvals in approval_counts.items():
        if approvals > max_approvals:
            max_approvals = approvals
            winners = [cand]
        elif approvals == max_approvals:
            winners.append(cand)

    total_valid_approvals = sum(approval_counts.values())
    win_pct = (max_approvals / total_ballots_processed) * 100 if total_ballots_processed > 0 else 0

    # Add None category for invalid ballots (minimal for native approval)
    approval_counts[None] = invalid_ballots

    return {
        'approval_counts': approval_counts,
        'winners': winners,
        'top_qty': max_approvals,
        'top_pct': win_pct,
        'total_approvals': total_valid_approvals,
        'total_votes': total_ballots_processed,
        'invalid_ballots': invalid_ballots,
        'method': 'native'
    }


def _simulated_approval_result(abifmodel):
    """Calculate approval results using strategic simulation from ranked ballots."""

    # Step 1: Get FPTP results to determine viable candidates
    fptp_results = FPTP_result_from_abifmodel(abifmodel)
    total_valid_votes = fptp_results['total_votes_recounted']

    # Step 2: Determine number of viable candidates using iterative Droop quota
    sorted_candidates = sorted(fptp_results['toppicks'].items(),
                              key=lambda x: x[1], reverse=True)

    # Filter out None (invalid ballots) from candidates
    sorted_candidates = [(cand, votes) for cand, votes in sorted_candidates if cand is not None]

    if not sorted_candidates:
        # No valid candidates
        return {
            'approval_counts': {None: total_valid_votes},
            'winners': [],
            'top_qty': 0,
            'top_pct': 0,
            'total_approvals': 0,
            'total_votes': total_valid_votes,
            'invalid_ballots': total_valid_votes,
            'method': 'simulate',
            'viable_candidates': [],
            'vcm': 0,
            'fptp_results': fptp_results
        }

    frontrunner_votes = sorted_candidates[0][1]  # Top candidate's vote total

    # Start with hypothetical 1 seat, increment until frontrunner CAN meet quota
    S = 1
    number_of_viable_candidates = 1  # Default minimum

    while S <= len(sorted_candidates):
        # Calculate Droop quota for S seats: floor(total_votes / (S + 1)) + 1
        quota = (total_valid_votes // (S + 1)) + 1

        if frontrunner_votes >= quota:
            # Frontrunner can win with S viable candidates
            number_of_viable_candidates = S
            break
        else:
            # Frontrunner can't win with S candidates, try more candidates
            S += 1

    # Create list of top N candidates based on first-place votes
    viable_candidates = []
    for i in range(min(number_of_viable_candidates, len(sorted_candidates))):
        candidate, votes = sorted_candidates[i]
        viable_candidates.append(candidate)

    # Step 3: Calculate viable-candidate-maximum (vcm)
    vcm = (len(viable_candidates) + 1) // 2

    # Initialize approval counts
    approval_counts = {}
    for cand_token in abifmodel['candidates'].keys():
        approval_counts[cand_token] = 0

    invalid_ballots = 0

    # Step 4: Process each ballot with strategic approval rules
    for vline in abifmodel['votelines']:
        ballot_qty = vline['qty']

        # Get ranked preferences for this ballot (sorted by rank)
        ranked_prefs = []
        for cand, prefs in vline['prefs'].items():
            if 'rank' in prefs:
                ranked_prefs.append((cand, prefs['rank']))

        # Sort by rank (lower rank number = higher preference)
        ranked_prefs.sort(key=lambda x: x[1])

        if not ranked_prefs:
            # Empty ballot
            invalid_ballots += ballot_qty
            continue

        # Check for overvotes at top rank
        top_rank = ranked_prefs[0][1]
        top_candidates = [cand for cand, rank in ranked_prefs if rank == top_rank]

        if len(top_candidates) > 1:
            # Overvote at top rank
            invalid_ballots += ballot_qty
            continue

        # Apply strategic approval rules using corrected algorithm

        # 1. Identify the top VCM viable candidates on THIS ballot
        vcm_viable_candidates_on_ballot = []
        for candidate, rank in ranked_prefs:
            if candidate in viable_candidates:
                vcm_viable_candidates_on_ballot.append(candidate)
                if len(vcm_viable_candidates_on_ballot) == vcm:
                    break

        # 2. Find the lowest-ranked candidate in that specific group
        if not vcm_viable_candidates_on_ballot:
            # No viable candidates were ranked, so no approvals
            approvals = []
        else:
            # The cutoff candidate is the last one in our list
            cutoff_candidate = vcm_viable_candidates_on_ballot[-1]

            # 3. Approve all candidates ranked at or above the cutoff
            approvals = []
            cutoff_found = False
            for candidate, rank in ranked_prefs:
                approvals.append(candidate)
                if candidate == cutoff_candidate:
                    cutoff_found = True
                    break

            if not cutoff_found:
                # This should not happen if logic is correct, but as safeguard
                approvals = vcm_viable_candidates_on_ballot

        # Apply approvals to vote counts
        for candidate in approvals:
            approval_counts[candidate] += ballot_qty

    # Calculate winner(s)
    max_approvals = 0
    winners = []
    for cand, approvals in approval_counts.items():
        if approvals > max_approvals:
            max_approvals = approvals
            winners = [cand]
        elif approvals == max_approvals:
            winners.append(cand)

    total_ballots_processed = abifmodel['metadata']['ballotcount']
    total_valid_approvals = sum(approval_counts.values())

    # Add None category for invalid ballots
    approval_counts[None] = invalid_ballots

    win_pct = (max_approvals / total_valid_votes) * 100 if total_valid_votes > 0 else 0

    return {
        'approval_counts': approval_counts,
        'winners': winners,
        'top_qty': max_approvals,
        'top_pct': win_pct,
        'total_approvals': total_valid_approvals,
        'total_votes': total_ballots_processed,
        'invalid_ballots': invalid_ballots,
        'viable_candidates': viable_candidates,
        'vcm': vcm,
        'droop_quota': (total_valid_votes // (number_of_viable_candidates + 1)) + 1,
        'fptp_results': fptp_results,
        'method': 'simulate'
    }


def get_approval_report(abifmodel, method='auto'):
    """Generate human-readable approval voting report."""
    results = approval_result_from_abifmodel(abifmodel, method)

    if results['method'] == 'native':
        report = "Approval Voting Results (Native Ballots):\n"
    else:
        report = "Approval Voting Results (Strategic Simulation):\n"
        report += f"  Based on FPTP analysis with Droop quota viability threshold\n"
        if 'droop_quota' in results:
            report += f"  Droop quota: {results['droop_quota']} votes\n"
        if 'viable_candidates' in results:
            viable_list = ', '.join(results['viable_candidates']) if results['viable_candidates'] else 'None'
            report += f"  Viable candidates: {viable_list}\n"
        if 'vcm' in results:
            report += f"  Viable-candidate-maximum (vcm): {results['vcm']}\n"
        report += "\n"

    report += f"  Approval counts:\n"

    # Sort candidates by approval count
    sorted_candidates = sorted(
        [(cand, count) for cand, count in results['approval_counts'].items() if cand is not None],
        key=lambda x: x[1],
        reverse=True
    )

    for cand, count in sorted_candidates:
        viable_marker = ""
        if results['method'] == 'simulate' and 'viable_candidates' in results:
            viable_marker = " (viable)" if cand in results['viable_candidates'] else ""
        report += f"   * {cand}: {count}{viable_marker}\n"

    if results['approval_counts'].get(None, 0) > 0:
        report += f"   * Invalid ballots: {results['approval_counts'][None]}\n"

    pctreport = f"{results['top_qty']} approvals of " + \
        f"{results['total_votes']} total votes ({results['top_pct']:.2f}%)"

    if len(results['winners']) == 1:
        report += f"\n  Winner with {pctreport}:\n"
        report += f"   * {results['winners'][0]}\n"
    elif len(results['winners']) > 1:
        report += f"\n  Tied winners each with {pctreport}:\n"
        for w in results['winners']:
           report += f"   * {w}\n"
    else:
        report += f"\n  No winner determined\n"

    return report


def main():
    parser = argparse.ArgumentParser(description='Approval voting calculator for ABIF')
    parser.add_argument('input_file', help='Input .abif file')
    parser.add_argument('-j', '--json', action="store_true",
                        help='Provide raw json output')
    parser.add_argument('-m', '--method', choices=['auto', 'native', 'simulate', 'droop_strategic'],
                        default='auto', help='Approval calculation method')

    args = parser.parse_args()
    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext)
    approval_dict = approval_result_from_abifmodel(jabmod, method=args.method)
    output = ""
    if args.json:
        output += json.dumps(clean_dict(approval_dict), indent=4)
    else:
        output += candlist_text_from_abif(jabmod)
        output += get_approval_report(jabmod, method=args.method)
    print(output)


if __name__ == "__main__":
    main()
