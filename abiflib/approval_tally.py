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

# Allow running this module directly by ensuring the package root is
# on sys.path
import os as _os
import sys as _sys
if __package__ is None or __package__ == "":
    _pkg_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
    if _pkg_root not in _sys.path:
        _sys.path.insert(0, _pkg_root)

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
    """Deprecated shim. Use transform_core.ranked_to_choose_many_favorite_viable_half.

    Retained for backward compatibility until callers migrate.
    """
    from .transform_core import ranked_to_choose_many_favorite_viable_half
    return ranked_to_choose_many_favorite_viable_half(abifmodel)


def approval_result_from_abifmodel(abifmodel):
    """Calculate approval voting results from jabmod (main entry point)."""
    ballot_type = find_ballot_type(abifmodel)

    notices = []
    if ballot_type == 'choose_many':
        # Native approval/choose_many: tally directly
        result = _calculate_approval_from_jabmod(abifmodel)
        return result
    elif ballot_type == 'choose_one':
        # For choose_one, treat the single top choice as an approval with no conversion
        # (rank==1 already suffices for _calculate_approval_from_jabmod)
        result = _calculate_approval_from_jabmod(abifmodel)
        # Attach a method-appropriate notice for choose_one
        note = {
            'notice_type': 'note',
            'short': 'Approvals inferred from choose_one ballots',
            'long': (
                'Approval results are derived by treating each voter\'s single top choice '
                'as their only approval. Lower preferences are not available on choose_one ballots.'
            )
        }
        existing = list(result.get('notices', []))
        existing.append(note)
        result['notices'] = existing
        return result
    else:
        # Ranked/rated (or others): convert via strategic method with notice
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


def build_ranked_from_choose_many(abifmodel, tie_breaker: str = 'token'):
    """Deprecated shim. Use transform_core.choose_many_to_ranked_least_approval_first.

    Retained for backward compatibility until callers migrate.
    """
    from .transform_core import choose_many_to_ranked_least_approval_first
    return choose_many_to_ranked_least_approval_first(abifmodel, tie_breaker=tie_breaker)


def get_order_least_approval_first(abifmodel, tie_breaker: str = 'token'):
    """Deprecated shim. Use transform_core.choose_many_to_ranked_least_approval_first
    to compute the order, or call transform_core internals.
    """
    from .transform_core import _get_order_least_approval_first as _core_laf
    return _core_laf(abifmodel, tie_breaker=tie_breaker)


def _generate_conversion_notices(conversion_meta):
    """Generate notices for ballot conversion."""
    notices = []

    method = conversion_meta.get('method')
    if method == 'favorite_viable_half':
        viable_candidates = conversion_meta.get('viable_candidates', [])
        viable_candidate_maximum = conversion_meta.get('viable_candidate_maximum', 0)
        original_ballot_type = conversion_meta.get('original_ballot_type', 'unknown')
        total_ballots = conversion_meta.get('total_ballots', 0)

        # Get candidate display names from conversion metadata
        candidate_names = conversion_meta.get('candidate_names', {})

        # Convert viable candidates to display names
        viable_names = []
        for cand_token in viable_candidates:
            display_name = candidate_names.get(cand_token, cand_token)
            viable_names.append(display_name)

        short_text = f"Approval counts estimated from {total_ballots:,} {original_ballot_type} ballots using favorite_viable_half method"

        viable_count = len(viable_candidates)
        # Format viable names list with proper "and" for last item
        if len(viable_names) > 2:
            viable_names_str = ", ".join(viable_names[:-1]) + f", and {viable_names[-1]}"
        elif len(viable_names) == 2:
            viable_names_str = f"{viable_names[0]} and {viable_names[1]}"
        else:
            viable_names_str = viable_names[0] if viable_names else ""

        if (viable_count % 2) == 0:
            viable_paren_note = f"(half of {viable_count}). "
        else:
            viable_paren_note = f"(half of {viable_count}, rounded up). "

        long_text = (
            f"The 'favorite_viable_half' conversion algorithm: find the candidate with the most "
            f"first preferences, and then determine the minimum number of figurative seats that would "
            f"need to be open in order for the candidate to exceed the Hare quota with the given first-prefs. "
            f"We use this to estimate how many candidates are likely to be viable candidates.\n\n"
            f"Using first-choice vote totals as a rough guide, approximately {viable_count} candidates appear viable: "
            f"{viable_names_str}. "
            f"The approximation then assumes each voter approves up to {viable_candidate_maximum} "
            f"of their top-ranked viable candidates {viable_paren_note}"
            f"All candidates ranked at or above the lowest-ranked of each ballot's top viable candidates receive approval "
            f"(considering up to {viable_candidate_maximum} viable candidates per ballot)."
        )

        notices.append({
            "notice_type": "note",
            "short": short_text,
            "long": long_text
        })
    elif method == 'all_ranked_approved':
        original_ballot_type = conversion_meta.get('original_ballot_type', 'unknown')
        total_ballots = conversion_meta.get('total_ballots', 0)
        short_text = (
            f"Approval counts derived from {total_ballots:,} {original_ballot_type} ballots by treating all ranked candidates as approved"
        )
        long_text = (
            "Each ballot approves every candidate that appears with any rank on the ballot; "
            "candidates not ranked are not approved. This avoids modeling strategic behavior, but may over-approve compared to real approval voting preferences."
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

    if ballot_type == 'choose_many':
        report = "Approval Voting Results (Native Approval/Choose-Many Ballots):\n"
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
    parser.add_argument('--global-order', action='store_true',
                        help='Print least-approval-first candidate order (Option F)')

    args = parser.parse_args()
    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext)
    approval_dict = approval_result_from_abifmodel(jabmod)
    output = ""
    if args.global_order:
        order = get_order_least_approval_first(jabmod)
        display_names = [jabmod.get('candidates', {}).get(tok, tok) for tok in order]
        output += "Global order (least-approval-first):\n"
        for i, (tok, name) in enumerate(zip(order, display_names), start=1):
            output += f"  {i:2d}. {name} ({tok})\n"
        output += "\n"
    if args.json:
        output += json.dumps(clean_dict(approval_dict), indent=4)
    else:
        output += candlist_text_from_abif(jabmod)
        output += get_approval_report(jabmod)
    print(output)


if __name__ == "__main__":
    main()
