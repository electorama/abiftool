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
import argparse
import json
import os
import sys
OUTPUT_FORMATS = ['dot', 'json', 'svg']


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
    copecount = full_copecount_from_abifmodel(abifmodel)

    if args.outfmt == 'svg' or 'dot':
        print(copecount_diagram(copecount, outformat=args.outfmt))
    elif args.outfmt == 'json':
        print(json.dumps(copecount))
    else:
        print(f"wtf is {args.outfmt=}?")


if __name__ == '__main__':
    exit_status = main(sys.argv)
    sys.exit(exit_status)
