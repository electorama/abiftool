#!/usr/bin/env python3
# pairwise.py - Pairwise/Condorcet calculator for Python
#
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

# import abiflib
from abiflib import *
from abiflib.textoutput import *
import argparse
import json
from pprint import pprint
import re
import sys
import texttable
import urllib.parse


def pairwise_count_dict(abifmodel):
    '''Convert abifmodel into pairwise matrix of vote counts'''
    candidates = abifmodel['candidates']
    votelines = abifmodel['votelines']

    candtoks = list(candidates.keys())

    # Initialize the return value matrix
    retval = {}
    for atok in candtoks:
        retval[atok] = {}
        for btok in candtoks:
            if atok == btok:
                retval[atok][btok] = None
            else:
                retval[atok][btok] = 0

    # Now add votelline qtys for each higher ranked cand
    for i, line in enumerate(votelines):
        thisqty = line['qty']
        lineprefs = line['prefs']
        maxrank = sys.maxsize
        for atok in candtoks:
            for btok in candtoks:
                if atok in lineprefs:
                    arank = lineprefs[atok]['rank']
                else:
                    arank = maxrank
                if btok in lineprefs:
                    brank = lineprefs[btok]['rank']
                else:
                    brank = maxrank
                # note that we're just ignoring arank > brank, since
                # the larger loop is only responsible for adding votes
                # when atok has a higher rank (lower number) than btok
                if atok == btok:
                    retval[atok][btok] = None
                elif arank < brank:
                    retval[atok][btok] += thisqty

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


def main():
    """Create pairwise matrix"""
    parser = argparse.ArgumentParser(
        description='Condorcet calc')
    parser.add_argument('input_file', help='Input .abif')

    args = parser.parse_args()
    jabmod = abiflib.convert_abif_to_jabmod(
        args.input_file,
        extrainfo=False)

    outstr = ""
    outstr += headerfy_text_file(args.input_file)

    pairdict = pairwise_count_dict(
        jabmod['candidates'],
        jabmod['votelines']
    )

    outstr += textgrid_for_2D_dict(
        twodimdict=pairdict,
        tablelabel='   Loser ->\nv Winner')

    print(outstr)


if __name__ == "__main__":
    main()
