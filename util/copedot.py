#!/usr/bin/env python3
"""
copedot - render directed graph of election in given abif file
"""
# Copyright (C) 2023 Rob Lanphier
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
from graphviz import Digraph
import argparse
import json
import os
import sys
OUTPUT_FORMATS = ['dot', 'json', 'svg']


def gen_output_from_copejson(copejson, outformat='svg'):
    winningvotes = copejson['winningvotes']
    winlosstie = copejson['winlosstie']

    # Determine the candidate with the highest Copeland score (most wins)
    top_candidate = max(winlosstie,
                        key=lambda candidate: winlosstie[candidate]['wins'])

    # Create a Digraph object
    dot = Digraph(comment='Pairwise Matchup Visualization')

    # Add nodes with win-loss-tie counts
    # Include the description only for the top candidate
    for candidate, scores in winlosstie.items():
        wins = scores['wins']
        losses = scores['losses']
        ties = scores['ties']
        if candidate == top_candidate:
            label = f"{candidate}\n"
            label += f"{wins}-{losses}-{ties}\n"
            label += f"({wins} wins, {losses} losses, {ties} ties)"
        else:
            label = f"{candidate}\n{
                scores['wins']}-{scores['losses']}-{scores['ties']}"
        dot.node(candidate, label)

    # Add edges for matchups with full candidate names in labels
    for wcand, wvotes in winningvotes.items():
        for lcand, wtally in wvotes.items():
            ltally = winningvotes[lcand][wcand]
            if wcand != lcand and wtally >= ltally:
                label_text = f"<--- {wcand}: {wtally}\n{lcand}: {ltally}"
                dot.edge(wcand, lcand, label=label_text)

    # Use pipe to render to requested format
    svg_output = dot.pipe(format=outformat).decode('utf-8')
    return svg_output


def main(argv=None):
    # using splitlines to just get the first line
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])

    parser.add_argument('--outfmt', dest='outfmt', type=str, default='svg',
                        choices=OUTPUT_FORMATS,
                        help='Format for the output')
    parser.add_argument('input_file', help='ABIF file to convert')
    args = parser.parse_args()

    inputstr = ""
    if args.input_file == '-':
        inputstr = sys.stdin.read()
    elif not os.path.exists(args.input_file):
        print(f"The file '{args.input_file}' doesn't exist.")
        sys.exit()
    else:
        with open(args.input_file, "r") as f:
            inputstr = f.read()

    abifmodel = convert_abif_to_jabmod(inputstr)
    copejson = {}
    copejson['winningvotes'] = pairwise_count_dict(abifmodel)
    copejson['winlosstie'] = winlosstie_dict_from_pairdict(
        abifmodel['candidates'],
        copejson['winningvotes'])

    if args.outfmt == 'svg' or 'dot':
        print(gen_output_from_copejson(copejson, outformat=args.outfmt))
    elif args.outfmt == 'json':
        print(json.dumps(copejson))
    else:
        print(f"wtf is {args.outfmt=}?")


if __name__ == '__main__':
    exit_status = main(sys.argv)
    sys.exit(exit_status)
