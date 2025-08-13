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
from abiflib.util import clean_dict, candlist_text_from_abif, find_ballot_type
from abiflib.fptp_tally import FPTP_result_from_abifmodel
from abiflib.text_output import format_notices_for_text_output
import argparse
import copy
import json
from pprint import pprint
import re
import sys
import urllib.parse
import pathlib
import textwrap


def convert_to_approval_favorite_viable_half(abifmodel):
    """Convert ranked/rated ballots to approval using favorite_viable_half algorithm."""
    # Step 1: Get FPTP results to determine viable candidates
    fptp_results = FPTP_result_from_abifmodel(abifmodel)
    total_valid_votes = fptp_results['total_votes_recounted']
    ballot_type = find_ballot_type(abifmodel)

    # Step 2: Determine number of viable candidates using iterative Hare quota
    sorted_candidates = sorted(fptp_results['toppicks'].items(),
                               key=lambda x: x[1], reverse=True)

    # Filter out None (invalid ballots) from candidates
    sorted_candidates = [(cand, votes) for cand, votes in sorted_candidates if cand is not None]

    if not sorted_candidates:
        # Return empty approval jabmod for no valid candidates
        approval_jabmod = copy.deepcopy(abifmodel)
        approval_jabmod['votelines'] = []
        return approval_jabmod

    frontrunner_votes = sorted_candidates[0][1]  # Top candidate's vote total

    # Find minimum number of figurative seats where frontrunner exceeds Hare quota
    # This is the algorithm as described: iterate through seat counts and find the
    # first (minimum) number where frontrunner_votes > quota
    number_of_viable_candidates = 2  # Default fallback

    # Check each possible number of seats, starting from 2
    for seats in range(2, len(sorted_candidates) + 2):  # +2 because we want seats, not candidates
        # Calculate Hare quota for this number of seats: total_votes / seats
        quota = total_valid_votes // seats

        if frontrunner_votes > quota:
            # Found the minimum number of seats where frontrunner exceeds quota
            number_of_viable_candidates = seats
            break

    # If frontrunner never exceeds quota even with maximum seats, use fallback
    if number_of_viable_candidates == 2 and frontrunner_votes <= (total_valid_votes // 2):
        # Frontrunner is very weak, estimate conservatively
        number_of_viable_candidates = min(len(sorted_candidates), 10)    # Create list of top N candidates based on first-place votes
    viable_candidates = []
    for i in range(min(number_of_viable_candidates, len(sorted_candidates))):
        candidate, votes = sorted_candidates[i]
        viable_candidates.append(candidate)

    # Step 3: Calculate viable-candidate-maximum (half of viable)
    viable_candidate_maximum = (len(viable_candidates) + 1) // 2

    # Step 4: Create new approval jabmod by converting votelines
    approval_jabmod = copy.deepcopy(abifmodel)
    approval_jabmod['votelines'] = []

    for vline in abifmodel['votelines']:
        # Get ranked preferences for this ballot (sorted by rank)
        ranked_prefs = []
        for cand, prefs in vline['prefs'].items():
            if 'rank' in prefs:
                ranked_prefs.append((cand, prefs['rank']))

        # Sort by rank (lower rank number = higher preference)
        ranked_prefs.sort(key=lambda x: x[1])

        if not ranked_prefs:
            # Skip empty ballots
            continue

        # Check for overvotes at top rank
        top_rank = ranked_prefs[0][1]
        top_candidates = [cand for cand, rank in ranked_prefs if rank == top_rank]

        if len(top_candidates) > 1:
            # Skip overvoted ballots
            continue

        # Apply halfviable approval rules

        # 1. Identify the top viable-candidate-maximum viable candidates on THIS ballot
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

        # Create new approval voteline
        new_prefs = {}
        for candidate in approvals:
            new_prefs[candidate] = {'rating': 1, 'rank': 1}

        if new_prefs:  # Only add votelines with actual approvals
            new_vline = {
                'qty': vline['qty'],
                'prefs': new_prefs
            }
            if 'prefstr' in vline:
                # Create a simple approval prefstr
                approved_cands = list(new_prefs.keys())
                new_vline['prefstr'] = '='.join(approved_cands) + '/1'

            approval_jabmod['votelines'].append(new_vline)

    # Store conversion metadata for notices
    approval_jabmod['_conversion_meta'] = {
        'method': 'favorite_viable_half',
        'original_ballot_type': ballot_type,
        'viable_candidates': viable_candidates,
        'viable_candidate_maximum': viable_candidate_maximum
    }

    return approval_jabmod


def approval_result_from_abifmodel(abifmodel):
    """Calculate approval voting results from jabmod (main entry point)."""
    ballot_type = find_ballot_type(abifmodel)

    if ballot_type == 'choose_many':
        # Handle native approval ballots directly
        return _calculate_approval_from_jabmod(abifmodel)
    else:
        # Convert to approval format first, then calculate
        approval_jabmod = convert_to_approval_favorite_viable_half(abifmodel)
        return _calculate_approval_from_jabmod(approval_jabmod)


def _calculate_approval_from_jabmod(abifmodel):
    """Calculate approval results from pure approval ballots."""
    approval_counts = {}
    # Initialize all candidates with 0 approvals
    for cand_token in abifmodel['candidates'].keys():
        approval_counts[cand_token] = 0

    invalid_ballots = 0
    total_ballots_processed = abifmodel['metadata']['ballotcount']
    original_ballot_type = find_ballot_type(abifmodel)

    # Check if this was converted from another ballot type
    conversion_meta = abifmodel.get('_conversion_meta', {})
    if conversion_meta:
        original_ballot_type = conversion_meta.get('original_ballot_type', original_ballot_type)

    for vline in abifmodel['votelines']:
        ballot_qty = vline['qty']

        # For approval ballots, candidates with rating=1 or rank=1 are approved
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

    # Add None category for invalid ballots
    approval_counts[None] = invalid_ballots

    # Generate notices if this was converted
    notices = []
    if conversion_meta:
        notices = _generate_conversion_notices(conversion_meta)

    return {
        'approval_counts': approval_counts,
        'winners': winners,
        'top_qty': max_approvals,
        'top_pct': win_pct,
        'total_approvals': total_valid_approvals,
        'total_votes': total_ballots_processed,
        'invalid_ballots': invalid_ballots,
        'ballot_type': original_ballot_type,
        'notices': notices
    }


def _generate_conversion_notices(conversion_meta):
    """Generate notices for ballot conversion."""
    notices = []

    method = conversion_meta.get('method')
    if method == 'favorite_viable_half':
        viable_candidates = conversion_meta.get('viable_candidates', [])
        viable_candidate_maximum = conversion_meta.get('viable_candidate_maximum', 0)
        original_ballot_type = conversion_meta.get('original_ballot_type', 'unknown')

        short_text = f"Approval counts estimated from {original_ballot_type} ballots using favorite_viable_half method"

        viable_count = len(viable_candidates)

        if (viable_count % 2) == 0:
            viable_paren_note = f"(half of {viable_count}). "
        else:
            viable_paren_note = f"(half of {viable_count}, rounded up). "
        long_text = (
            f"The 'favorite_viable_half' conversion algorithm: find the candidate with the most "
            f"first preferences, and then determine the minimum number of figurative seats that would "
            f"need to be open in order for the candidate to exceed the Hare quota with the given first-prefs. "
            f"We use this to estimate how many candidates are likely to be viable candidates. "
            f"For this election by this calculation, {viable_count} candidates are considered viable. "
            f"The approximation then assumes each voter approves up to {viable_candidate_maximum} "
            f"of their top-ranked viable candidates {viable_paren_note}"
            f"All candidates ranked at or above the lowest-ranked of each voter's top {viable_candidate_maximum} "
            f"viable candidates receive approval."
        )

        notices.append({
            "notice_type": "note",
            "short": short_text,
            "long": long_text
        })

    return notices


def get_approval_report(abifmodel):
    """Generate human-readable approval voting report."""
    results = approval_result_from_abifmodel(abifmodel)

    ballot_type = results['ballot_type']

    if ballot_type == 'approval':
        report = "Approval Voting Results (Native Approval Ballots):\n"
    else:
        # This was converted from another ballot type
        notices = results.get('notices', [])
        conversion_method = 'favorite_viable_half'  # Our current default method
        if notices:
            for notice in notices:
                if 'favorite_viable_half' in notice.get('short', ''):
                    conversion_method = 'favorite_viable_half'
                    break

        report = f"Approval Voting Results (Converted from {ballot_type} ballots using {conversion_method} method):\n"
        report += "\n"

    report += f"  Approval counts:\n"

    # Sort candidates by approval count
    sorted_candidates = sorted(
        [(cand, count) for cand, count in results['approval_counts'].items() if cand is not None],
        key=lambda x: x[1],
        reverse=True
    )

    total_votes = results['total_votes']
    for cand, count in sorted_candidates:
        pct = (count / total_votes) * 100 if total_votes > 0 else 0
        # Get the full candidate name from the candidates mapping
        full_name = abifmodel['candidates'].get(cand, cand)
        if full_name != cand:
            # Show full name with token in parentheses
            display_name = f"{full_name} ({cand})"
        else:
            # If full name same as token, just show the name
            display_name = cand
        report += f"   * {display_name}: {count:,} ({pct:.2f}%)\n"

    if results['approval_counts'].get(None, 0) > 0:
        invalid_count = results['approval_counts'][None]
        report += f"   * Invalid ballots: {invalid_count:,}\n"

    pctreport = f"{results['top_qty']:,} approvals of " + \
        f"{results['total_votes']:,} total votes ({results['top_pct']:.2f}%)"

    if len(results['winners']) == 1:
        winner = results['winners'][0]
        full_name = abifmodel['candidates'].get(winner, winner)
        if full_name != winner:
            display_name = f"{full_name} ({winner})"
        else:
            display_name = winner
        report += f"\n  Winner with {pctreport}:\n"
        report += f"   * {display_name}\n"
    elif len(results['winners']) > 1:
        report += f"\n  Tied winners each with {pctreport}:\n"
        for w in results['winners']:
            full_name = abifmodel['candidates'].get(w, w)
            if full_name != w:
                display_name = f"{full_name} ({w})"
            else:
                display_name = w
            report += f"   * {display_name}\n"
    else:
        report += f"\n  No winner determined\n"

    # Add notices section if present
    if results.get('notices'):
        report += format_notices_for_text_output(results['notices'])

    return report


def main():
    parser = argparse.ArgumentParser(description='Approval voting calculator for ABIF')
    parser.add_argument('input_file', help='Input .abif file')
    parser.add_argument('-j', '--json', action="store_true",
                        help='Provide raw json output')

    args = parser.parse_args()
    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext)
    approval_dict = approval_result_from_abifmodel(jabmod)
    output = ""
    if args.json:
        output += json.dumps(clean_dict(approval_dict), indent=4)
    else:
        output += candlist_text_from_abif(jabmod)
        output += get_approval_report(jabmod)
    print(output)


if __name__ == "__main__":
    main()
