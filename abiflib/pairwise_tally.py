#!/usr/bin/env python3
''' pairwise.py - Pairwise/Condorcet calculator for Python '''

# Copyright (c) 2023, 2024 Rob Lanphier
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
import argparse
import json
import pathlib
from pprint import pprint
import re
import sys
import urllib.parse


def pairwise_count_dict(abifmodel):
    '''Convert abifmodel into pairwise matrix of vote counts'''
    candidates = abifmodel['candidates']
    votelines = abifmodel['votelines']
    candtoks = list(candidates.keys())

    # Initialize the pairwise matrix
    pairwise_matrix = {atok: {btok: (None if atok == btok else 0) for btok in candtoks} for atok in candtoks}

    maxrank = sys.maxsize
    for line in votelines:
        thisqty = line['qty']
        lineprefs = line['prefs']
        # Precompute all ranks for this ballot
        ranks = {cand: lineprefs[cand].get('rank', maxrank) if cand in lineprefs else maxrank for cand in candtoks}
        for atok in candtoks:
            arank = ranks[atok]
            for btok in candtoks:
                if atok == btok:
                    continue
                brank = ranks[btok]
                if arank < brank:
                    pairwise_matrix[atok][btok] += thisqty

    return pairwise_matrix


def pairwise_result_from_abifmodel(abifmodel):
    '''Calculate pairwise results with notices (main entry point for web interface)'''
    candidates = abifmodel['candidates']
    candtoks = list(candidates.keys())

    # Get the basic pairwise matrix
    pairwise_matrix = pairwise_count_dict(abifmodel)

    # Check for ties or cycles to determine if notice is needed
    has_ties_or_cycles = False

    # Check for pairwise ties
    for cand1 in candtoks:
        for cand2 in candtoks:
            if cand1 != cand2:
                cand1_votes = pairwise_matrix.get(cand1, {}).get(cand2, 0)
                cand2_votes = pairwise_matrix.get(cand2, {}).get(cand1, 0)
                if cand1_votes == cand2_votes:
                    has_ties_or_cycles = True
                    break
        if has_ties_or_cycles:
            break

    # Check for cycles using win-loss-tie data
    if not has_ties_or_cycles:
        wltdict = winlosstie_dict_from_pairdict(candidates, pairwise_matrix)
        sorted_candidates = sorted(candtoks, key=lambda x: wltdict[x]['wins'], reverse=True)
        for i, cand1 in enumerate(sorted_candidates):
            for j, cand2 in enumerate(sorted_candidates):
                if i > j:  # cand1 should be ranked lower than cand2
                    cand1_beats_cand2 = (pairwise_matrix.get(cand1, {}).get(cand2, 0) >
                                         pairwise_matrix.get(cand2, {}).get(cand1, 0))
                    if cand1_beats_cand2:
                        has_ties_or_cycles = True
                        break
            if has_ties_or_cycles:
                break

    # Create result structure with notices
    result = {
        'pairwise_matrix': pairwise_matrix,
        'has_ties_or_cycles': has_ties_or_cycles
    }

    # Add notices if there are ties or cycles
    notices = []
    if has_ties_or_cycles:
        notices.append({
            "notice_type": "note",
            "short": "Condorcet cycle or Copeland tie",
            "long": '"Victories" and "losses" sometimes aren\'t displayed in the expected location when there are ties and/or cycles in the results, but the numbers provided should be accurate.'
        })

    result['notices'] = notices
    return result


def get_pairwise_report(abifmodel):
    """Generate human-readable pairwise voting report with notices."""
    from abiflib.text_output import format_notices_for_text_output, textgrid_for_2D_dict
    result = pairwise_result_from_abifmodel(abifmodel)

    retval = ""
    # Add the main pairwise matrix display
    retval += textgrid_for_2D_dict(twodimdict=result['pairwise_matrix'],
                                   tablelabel='   Loser ->\nv Winner')

    # Add notices section if present
    if result.get('notices'):
        retval += format_notices_for_text_output(result['notices'])

    return retval


def winlosstie_dict_from_pairdict(candidates, pairdict):
    candtoks = list(candidates.keys())
    winlosstie_dict = {}
    for atok in candtoks:
        winlosstie_dict[atok] = {'wins': 0,
                                 'losses': 0,
                                 'ties': 0}
    for atok in candtoks:
        for btok in candtoks:
            a2b = pairdict[atok][btok]
            b2a = pairdict[btok][atok]
            # When atok == btok, that's the diagonal stripe in the
            # middle of the matrix with no values because candidates
            # don't run against each other.
            if atok != btok:
                if a2b > b2a:
                    winlosstie_dict[atok]['wins'] += 1
                    winlosstie_dict[btok]['losses'] += 1
                elif a2b == b2a:
                    winlosstie_dict[atok]['ties'] += 1
                    winlosstie_dict[btok]['ties'] += 1
                else:
                    # Avoiding counting each matchup twice by only paying
                    # attention to half of the matrix
                    pass

    stuples = sorted(winlosstie_dict.items(),
                     key=lambda item: item[1]['wins'], reverse=True)
    sorted_dict = {k: v for k, v in stuples}

    return sorted_dict


def calculate_pairwise_victory_sizes(pairdict, method="winning-votes"):
    """
    Calculate victory sizes for all pairwise matchups.

    Args:
        pairdict: Dictionary of pairwise vote counts
        method: "winning-votes" (default) or "margins"

    Returns:
        List of dictionaries with victory information, sorted by victory size
    """
    candtoks = list(pairdict.keys())
    victories = []

    for winner in candtoks:
        for loser in candtoks:
            if winner == loser:
                continue

            winner_votes = pairdict[winner][loser]
            loser_votes = pairdict[loser][winner]

            if winner_votes is None or loser_votes is None:
                continue

            if winner_votes > loser_votes:
                # Calculate victory size based on method
                if method == "margins":
                    victory_size = winner_votes - loser_votes
                else:  # winning-votes (default)
                    victory_size = winner_votes

                victories.append({
                    'winner': winner,
                    'loser': loser,
                    'winner_votes': winner_votes,
                    'loser_votes': loser_votes,
                    'victory_size': victory_size,
                    'total_votes': winner_votes + loser_votes
                })
            elif winner_votes == loser_votes:
                # Handle ties
                victories.append({
                    'winner': None,
                    'loser': None,
                    'tied_candidates': [winner, loser],
                    'winner_votes': winner_votes,
                    'loser_votes': loser_votes,
                    'victory_size': 0,
                    'total_votes': winner_votes + loser_votes,
                    'is_tie': True
                })

    # Remove duplicate ties (since we iterate over all pairs)
    unique_victories = []
    tie_pairs_seen = set()

    for victory in victories:
        if victory.get('is_tie'):
            # Create a sorted tuple to identify unique ties
            tie_pair = tuple(sorted(victory['tied_candidates']))
            if tie_pair not in tie_pairs_seen:
                tie_pairs_seen.add(tie_pair)
                unique_victories.append(victory)
        else:
            unique_victories.append(victory)

    # Sort by victory size (descending for largest first, ascending for smallest first)
    sorted_victories = sorted(unique_victories, key=lambda x: x['victory_size'], reverse=True)

    return sorted_victories


def generate_pairwise_summary_text(abifmodel, wltdict, victory_data, victory_method):
    """
    Generate text summary bullets for pairwise elections.
    Format matches the examples in docs/summary-per-method.md
    """
    candidates = abifmodel['candidates']
    candidate_list = list(wltdict.items())

    if not candidate_list:
        return "No pairwise data available.\n"

    lines = []
    lines.append("Pairwise Election Summary:")
    lines.append("=" * 50)

    # Winner
    winner_token = candidate_list[0][0]
    winner_record = candidate_list[0][1]
    winner_name = candidates.get(winner_token, winner_token)
    lines.append(f"* Winner: {winner_name} ({winner_record['wins']}-{winner_record['losses']}-{winner_record['ties']})")

    # Runner-up
    if len(candidate_list) > 1:
        runner_up_token = candidate_list[1][0]
        runner_up_record = candidate_list[1][1]
        runner_up_name = candidates.get(runner_up_token, runner_up_token)
        lines.append(f"* Runner-up: {runner_up_name} ({runner_up_record['wins']}-{runner_up_record['losses']}-{runner_up_record['ties']})")

        # Find head-to-head between winner and runner-up
        decisive_victories = [v for v in victory_data if not v.get('is_tie', False)]
        for victory in decisive_victories:
            if ((victory['winner'] == winner_token and victory['loser'] == runner_up_token) or
                    (victory['winner'] == runner_up_token and victory['loser'] == winner_token)):
                margin = victory['winner_votes'] - victory['loser_votes']
                winner_name_h2h = candidates.get(victory['winner'], victory['winner'])
                loser_name_h2h = candidates.get(victory['loser'], victory['loser'])
                lines.append(f"* Head-to-head: {winner_name_h2h} beats {loser_name_h2h} ({victory['winner_votes']}-{victory['loser_votes']}; margin: {margin})")
                break

    # Victory margins analysis
    decisive_victories = [v for v in victory_data if not v.get('is_tie', False)]
    if decisive_victories:
        smallest_victory = min(decisive_victories, key=lambda x: x['victory_size'])
        largest_victory = max(decisive_victories, key=lambda x: x['victory_size'])

        method_label = "margin" if victory_method == "margins" else "winning votes"

        smallest_winner = candidates.get(smallest_victory['winner'], smallest_victory['winner'])
        smallest_loser = candidates.get(smallest_victory['loser'], smallest_victory['loser'])
        lines.append(f"* Smallest {method_label}: {smallest_winner} over {smallest_loser} "
                     f"({smallest_victory['winner_votes']}-{smallest_victory['loser_votes']}; "
                     f"{method_label}: {smallest_victory['victory_size']})")

        largest_winner = candidates.get(largest_victory['winner'], largest_victory['winner'])
        largest_loser = candidates.get(largest_victory['loser'], largest_victory['loser'])
        lines.append(f"* Largest {method_label}: {largest_winner} over {largest_loser} "
                     f"({largest_victory['winner_votes']}-{largest_victory['loser_votes']}; "
                     f"{method_label}: {largest_victory['victory_size']})")

    # Ties
    ties = [v for v in victory_data if v.get('is_tie', False)]
    if ties:
        lines.append(f"* Pairwise ties: {len(ties)}")
    else:
        lines.append("* Pairwise ties: none")

    # Total ballots
    total_ballots = abifmodel.get('metadata', {}).get('ballotcount', 0)
    if total_ballots > 0:
        lines.append(f"* Total ballots counted: {total_ballots:,}")

    return "\n".join(lines) + "\n"


def full_copecount_from_abifmodel(abifmodel, pairdict=None):
    '''Consolidate pairwise tally and win-loss-tie structs'''
    copecount = {}
    if pairdict is None:
        pairdict = pairwise_count_dict(abifmodel)
    copecount['winningvotes'] = pairdict
    copecount['winlosstie'] = winlosstie_dict_from_pairdict(
        abifmodel['candidates'],
        copecount['winningvotes'])
    return copecount


def calc_Copeland_scores(copecount):
    point_totals = {}
    for candidate, results in copecount['winlosstie'].items():
        points = results['wins'] + (results['ties'] * 0.5)
        point_totals[candidate] = points
    sorted_point_tuples = sorted(point_totals.items(),
                                 key=lambda x: x[1],
                                 reverse=True)
    return sorted_point_tuples


def get_Copeland_winners(copecount):
    """Return a list of candidates having the highest Copeland score"""
    copescores = calc_Copeland_scores(copecount)
    if len(copescores) > 0:
        winning_score = max(cscore for name, cscore in copescores)
    else:
        winning_score = 0
    return [name for name, score in copescores if score == winning_score]


def Copeland_report(canddict, copecount):
    retval = ""
    # retval += f"{canddict=}\n"
    copescores = calc_Copeland_scores(copecount)
    # retval += f"odlWinner: {copescores[0][0]=} {copescores[0][1]=}\n"
    retval += f"Copeland Winner: {canddict[copescores[0][0]]} (score: {copescores[0][1]})\n"
    return retval


def main():
    """Create pairwise matrix"""
    parser = argparse.ArgumentParser(
        description='Condorcet calc')
    parser.add_argument('input_file', help='Input .abif')

    args = parser.parse_args()

    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext)

    outstr = ""
    outstr += "======= ABIF FILE =======\n\n"
    outstr += headerfy_text_file(abiftext,
                                 filename=args.input_file)

    outstr += "\n======= PAIRWISE RESULTS =======\n\n"

    pairdict = pairwise_count_dict(jabmod)

    outstr += textgrid_for_2D_dict(
        twodimdict=pairdict,
        tablelabel='   Loser ->\nv Winner')

    print(outstr)


if __name__ == "__main__":
    main()
