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

from abiflib import *
import argparse
import json
import pathlib
from pprint import pformat
import re
import sys
import urllib.parse

def score_result_from_abifmodel(abifmodel):
    scores = {}
    for voteline in abifmodel['votelines']:
        qty = voteline['qty']
        for cand, candval in voteline['prefs'].items():
            rating = int(candval['rating'])
            if cand in scores:
                scores[cand] += rating * qty
            else:
                scores[cand] = rating * qty

    result = [{"candname": cand, "score": score} for cand, score in scores.items()]
    result.sort(key=lambda x: x['score'], reverse=True)
    return result



def main():
    """Create score array"""
    parser = argparse.ArgumentParser(
        description='Takes abif and returns score results')
    parser.add_argument('input_file', help='Input .abif')

    args = parser.parse_args()

    abiftext = pathlib.Path(args.input_file).read_text()
    jabmod = convert_abif_to_jabmod(abiftext, add_ratings=True)

    outstr = ""
    outstr += "======= ABIF FILE =======\n\n"
    outstr += headerfy_text_file(abiftext,
                                 filename=args.input_file)

    outstr += "\n======= SCORE RESULTS =======\n\n"
    outstr += pformat(score_result_from_abifmodel(jabmod))
    print(outstr)


if __name__ == "__main__":
    main()
