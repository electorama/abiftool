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
import re
import sys
import texttable
import urllib.parse

def pairwise_count_dict(abifmodel):
    candidates = abifmodel['candidates']
    votelines = abifmodel['votelines']

    candtoks = list(candidates.keys())
    retval_a_over_b = {}
    for atok in candtoks:
        retval_a_over_b[atok] = {}
        for btok in candtoks:
            if atok == btok:
                retval_a_over_b[atok][btok] = None
            else:
                retval_a_over_b[atok][btok] = 0

    for i, line in enumerate(votelines):
        thisqty = line['qty']
        prevrank = None
        prevcand = None
        prevcandlist = []
        for j, (jkey,
                jitem) in enumerate(line['prefs'].items()):
            for pkey in prevcandlist:
                retval_a_over_b[pkey][jkey] += thisqty

            prevcand = jkey
            prevcandlist.append(jkey)
            prevrank = jitem['rank']
    return retval_a_over_b


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
            # midddle of the matrix with no values because candidates
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
