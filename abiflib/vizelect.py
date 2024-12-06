#!/usr/bin/env python3
"""
vizelect - functions for election visualizations
"""
# Copyright (C) 2024 Rob Lanphier
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
import json
import os
import sys


def copecount_diagram(copecount, outformat='svg', is_inline=False):
    winningvotes = copecount['winningvotes']
    winlosstie = copecount['winlosstie']

    # Determine the candidate with the highest Copeland score (most wins)
    top_candidate = max(winlosstie,
                        key=lambda candidate: winlosstie[candidate]['wins'])

    dot = Digraph(comment='Pairwise Matchup Visualization')

    # Add nodes with win-loss-tie counts
    for candidate, scores in winlosstie.items():
        wins = scores['wins']
        losses = scores['losses']
        ties = scores['ties']
        label = f"{candidate}"
        label += f"\n{wins}-{losses}-{ties}"
        # Include full description only for the top candidate
        if candidate == top_candidate:
            label += f"\n({wins} wins, {losses} losses, {ties} ties)"
        dot.node(candidate, label)

    # Add edges for matchups with full candidate names in labels
    for wcand, wvotes in winningvotes.items():
        for lcand, wtally in wvotes.items():
            ltally = winningvotes[lcand][wcand]
            if wcand != lcand and wtally >= ltally:
                label_text = f"← {wcand}: {wtally}\n{lcand}: {ltally}"
                dot.edge(wcand, lcand, label=label_text)

    diagram_output = dot.pipe(format=outformat).decode('utf-8')

    is_inline = True
    # strip out initial xml cruft if this intended for embedding in html
    if is_inline:
        # TODO: does it make sense to generalize this beyond svg?
        start_index = diagram_output.find('<svg')
        if start_index != -1:
            diagram_output = diagram_output[start_index:]

    return diagram_output
