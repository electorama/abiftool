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

import abiflib
from abiflib import *
import argparse
import json
import re
import sys
import texttable
import urllib.parse


def pairwise_count_dict(candidates, votelines):
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


def main():
    """Create pairwise matrix"""
    global DEBUGFLAG

    parser = argparse.ArgumentParser(
        description='Condorcet calc')
    parser.add_argument('input_file', help='Input .abif')
    parser.add_argument('-d', '--debug',
                        help='Flip the global DEBUGFLAG',
                        action="store_true")

    args = parser.parse_args()
    DEBUGFLAG = args.debug
    jabmod = abiflib.convert_abif_to_jabmod(
        args.input_file,
        debugflag=DEBUGFLAG,
        extrainfo=False)

    outstr = ""
    outstr += headerfy_text_file(args.input_file)

    pairdict = pairwise_count_dict(
        jabmod['candidates'],
        jabmod['votelines']
    )

    outstr += textgrid_for_2D_dict(
        twodimdict=pairdict,
        DEBUGFLAG=DEBUGFLAG,
        tablelabel='   Loser ->\nv Winner')

    debugprint(f"{DEBUGFLAG=}")
    print(outstr)


if __name__ == "__main__":
    main()
