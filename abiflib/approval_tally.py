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
import argparse
import copy
import json
from pprint import pprint
import re
import sys
import urllib.parse
import pathlib
import textwrap


def detect_ballot_type(abifmodel):
    """
    Detect the type of ballots in a jabmod structure.

    Returns one of: 'approval', 'rated', 'ranked', 'choose_one', 'unknown'

    This function is designed to eventually be moved to core.py as a
    general utility for all voting methods.
    """
    has_ratings = False
    has_ranks = False
    has_binary_ratings = False
    has_non_binary_ratings = False
    has_equal_ranks = False
    has_multiple_choices = False
    has_comma_delimited = False
    has_rank_delimited = False
    non_blank_ballots = 0
    total_ballots = 0

    for vline in abifmodel['votelines']:
        total_ballots += vline.get('qty', 1)
        ballot_rankings = []
        ballot_ratings = []
        candidates_with_ratings = 0
        total_candidates_on_ballot = len(vline['prefs'])

        # Skip blank ballots (no preferences)
        if total_candidates_on_ballot == 0:
            continue

        non_blank_ballots += vline.get('qty', 1)

        for cand, prefs in vline['prefs'].items():
            # Check for ratings
            if 'rating' in prefs:
                has_ratings = True
                candidates_with_ratings += 1
                rating = prefs['rating']
                ballot_ratings.append(rating)

                # Check for binary ratings (0 or 1)
                if rating in [0, 1]:
                    has_binary_ratings = True
                else:
                    has_non_binary_ratings = True

            # Check for rankings
            if 'rank' in prefs:
                has_ranks = True
                rank = prefs['rank']
                ballot_rankings.append(rank)

        # Check for equal rankings (ties)
        if ballot_rankings:
            unique_ranks = set(ballot_rankings)
            if len(unique_ranks) < len(ballot_rankings):
                has_equal_ranks = True

        # Check if ballot has multiple choices
        if total_candidates_on_ballot > 1:
            has_multiple_choices = True

        # Detect delimiter patterns from original prefstr if available
        if 'prefstr' in vline:
            prefstr = vline['prefstr']
            if ',' in prefstr and '>' not in prefstr and '=' not in prefstr:
                has_comma_delimited = True
            if '>' in prefstr or '=' in prefstr:
                has_rank_delimited = True

    # If we have no non-blank ballots, we can't determine the type
    if non_blank_ballots == 0:
        return 'unknown'

    # Decision logic for ballot type

    # If we have comma-delimited format, it's not ranked
    if has_comma_delimited and not has_rank_delimited:
        if has_binary_ratings and not has_non_binary_ratings:
            return 'approval'
        elif has_non_binary_ratings:
            return 'rated'
        elif not has_ratings and has_multiple_choices:
            return 'unknown'  # Comma-delimited without ratings is ambiguous
        else:
            return 'choose_one'

    # Binary ratings or equal ranks with ratings = approval
    if has_binary_ratings and not has_non_binary_ratings:
        if has_equal_ranks or not has_ranks:
            return 'approval'

    # Non-binary ratings = rated (if all candidates have ratings)
    if has_non_binary_ratings:
        return 'rated'

    # Pure rankings without ratings
    if has_ranks and not has_ratings:
        if has_multiple_choices:
            return 'ranked'
        else:
            return 'choose_one'

    # Mixed ratings and rankings
    if has_ratings and has_ranks:
        if has_binary_ratings and not has_non_binary_ratings:
            return 'approval'
        elif has_non_binary_ratings:
            return 'rated'
        else:
            return 'unknown'

    # No clear pattern detected
    if has_multiple_choices:
        return 'unknown'
    else:
        return 'choose_one'


def has_approval_data(abifmodel):
    """Detect if jabmod contains native approval data."""
    return detect_ballot_type(abifmodel) == 'approval'


def has_only_rankings(abifmodel):
    """Detect if jabmod contains only ranked preferences."""
    ballot_type = detect_ballot_type(abifmodel)
    return ballot_type in ['ranked', 'choose_one']


def detect_approval_method(abifmodel):
    """Auto-detect appropriate approval calculation method."""
    # Returns 'native' or 'simulate' based on ballot content

    ballot_type = detect_ballot_type(abifmodel)

    if ballot_type == 'approval':
        return 'native'
    elif ballot_type in ['ranked', 'choose_one', 'rated']:
        return 'simulate'
    elif ballot_type == 'unknown':
        # For unknown types, try to simulate if we have any ranking/rating data
        # Otherwise default to native
        return 'simulate'
    else:
        # Default to native for any other types
        return 'native'


def _generate_approval_notices(method, ballot_type, viable_candidates=None, viable_candidate_maximum=None):
    """Generate appropriate notices based on approval calculation method."""
    notices = []

    if method == 'simulate':
        # Add strategic simulation disclaimer
        short_text = "Approval counts estimated from ranked ballots"

        viable_count = len(viable_candidates) if viable_candidates else 'N'
        vcm = viable_candidate_maximum if viable_candidate_maximum else 'floor((viable_count + 1) / 2)'

        long_text = (
            f"This uses a `reverse Droop` calculation to provide a crude estimate for "
            f"the number of viable candidates:\n"
            f"a) Count the top preferences for the all candidates\n"
            f"b) Determine the minimum number of figurative seats that would "
            f"need to be filled in order for the leading candidate to exceed "
            f"the Droop quota.\n"
            f"For this election, this is {viable_count} seats, so {viable_count} candidates are considered viable.\n"
            f"To then determine the number of viable candidates voters are likely to approve of, "
            f"divide the number of viable candidates by two, and round up.\n"
            f"In this election, each voter approves up to {vcm} viable candidates.\n"
            f"On these ballots, all candidates ranked at or above the lowest-ranked of each voter's "
            f"viable candidates are approved.")

        notices.append({
            "notice_type": "disclaimer",
            "short": short_text,
            "long": long_text
        })

    return notices


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
    ballot_type = detect_ballot_type(abifmodel)

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
        'ballot_type': ballot_type,
        'notices': []  # No notices for native approval
    }


def _simulated_approval_result(abifmodel):
    """Calculate approval results using strategic simulation from ranked ballots."""

    # Step 1: Get FPTP results to determine viable candidates
    fptp_results = FPTP_result_from_abifmodel(abifmodel)
    total_valid_votes = fptp_results['total_votes_recounted']
    ballot_type = detect_ballot_type(abifmodel)

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
            'ballot_type': ballot_type
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

    # Step 3: Calculate viable-candidate-maximum
    # (strategic approval limit per ballot)
    viable_candidate_maximum = (len(viable_candidates) + 1) // 2

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
        # (VCM = viable-candidate-maximum)
        vcm_viable_candidates_on_ballot = []
        for candidate, rank in ranked_prefs:
            if candidate in viable_candidates:
                vcm_viable_candidates_on_ballot.append(candidate)
                if len(vcm_viable_candidates_on_ballot) == viable_candidate_maximum:
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

    # Generate notices for strategic simulation
    notices = _generate_approval_notices('simulate', ballot_type, viable_candidates, viable_candidate_maximum)

    return {
        'approval_counts': approval_counts,
        'winners': winners,
        'top_qty': max_approvals,
        'top_pct': win_pct,
        'total_approvals': total_valid_approvals,
        'total_votes': total_ballots_processed,
        'invalid_ballots': invalid_ballots,
        'ballot_type': ballot_type,
        'notices': notices
    }


def get_approval_report(abifmodel, method='auto'):
    """Generate human-readable approval voting report."""
    results = approval_result_from_abifmodel(abifmodel, method)

    ballot_type = results['ballot_type']

    if ballot_type == 'approval':
        report = "Approval Voting Results (Native Approval Ballots):\n"
    elif ballot_type == 'ranked':
        report = "Approval Voting Results (Strategic Simulation from Ranked Ballots):\n"
        report += f"  Based on FPTP analysis with Droop quota viability threshold\n"
        report += "\n"
    elif ballot_type == 'rated':
        report = "Approval Voting Results (Strategic Simulation from Rated Ballots):\n"
        report += f"  Based on FPTP analysis with Droop quota viability threshold\n"
        report += "\n"
    elif ballot_type == 'choose_one':
        report = "Approval Voting Results (Strategic Simulation from Choose-One Ballots):\n"
        report += f"  Based on FPTP analysis with Droop quota viability threshold\n"
        report += "\n"
    elif ballot_type == 'unknown':
        report = "Approval Voting Results (Unknown Ballot Type - Strategic Simulation):\n"
        report += f"  Based on FPTP analysis with Droop quota viability threshold\n"
        report += f"  Warning: Ballot type could not be definitively determined\n"
        report += "\n"
    else:
        report = "Approval Voting Results:\n"

    report += f"  Approval counts:\n"

    # Sort candidates by approval count
    sorted_candidates = sorted(
        [(cand, count) for cand, count in results['approval_counts'].items() if cand is not None],
        key=lambda x: x[1],
        reverse=True
    )

    for cand, count in sorted_candidates:
        report += f"   * {cand}: {count}\n"

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

    # Add notices section if present
    if results.get('notices'):
        for notice in results['notices']:
            notice_type = notice.get('notice_type', 'info').upper()
            report += f"\n[{notice_type}] {notice['short']}\n"

            if notice.get('long'):
                # Word wrap the long notice at 78 characters
                wrapped = textwrap.fill(notice['long'], width=76, initial_indent='  ',
                                        subsequent_indent='  ')
                report += f"\n{wrapped}\n"

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
