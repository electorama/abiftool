#!/usr/bin/env python3
# abiftool.py - conversion to/from .abif to other electoral expressions
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
import re
import sys
import urllib.parse

CONV_FORMATS = ('abif', 'jabmod', 'jabmodextra', 'widj')

PRUNED_WIDJ_FIELDS = [
    "display_parameters", "display_results",
    "display_ballots", "allow_voting",
    "ballot_type", "max_rating", "min_rating",
    "count_subpage_ballots", "count_inline_ballots",
    "election_methods", "inline_ballot_type",
    "candidates", "inline_ballots"
]
ABIF_VERSION = "0.1"
DEBUGFLAG = False
LOOPLIMIT = 400


def debugprint(str):
    global DEBUGFLAG
    if DEBUGFLAG:
        print(str)
    return


def main():
    """Convert between .abif-adjacent formats."""
    global DEBUGFLAG

    parser = argparse.ArgumentParser(
        description='Convert between .abif and JSON formats')
    parser.add_argument('input_file', help='Input file to convert')
    parser.add_argument('-t', '--to', choices=CONV_FORMATS,
                        required=True, help='Output format')
    parser.add_argument('-f', '--fromfmt', choices=CONV_FORMATS,
                        help='Input format (overrides file extension)')
    parser.add_argument('-d', '--debug',
                        help='Output debugging info',
                        action="store_true")

    args = parser.parse_args()

    DEBUGFLAG = args.debug
    debugprint(f"{DEBUGFLAG=}")

    # CONV_FORMATS = ('abif', 'jabmod', 'jabmodextra', 'widj')

    # Determine input format based on file extension or override from
    # the "-f/--fromfmt" option
    if args.fromfmt:
        input_format = args.fromfmt
    else:
        _, file_extension = args.input_file.rsplit('.', 1)
        input_format = file_extension
    if input_format not in CONV_FORMATS:
        print(f"Error: Unsupported input format '{input_format}'")
        return

    # the "-t/--to" option
    output_format = args.to
    if output_format not in CONV_FORMATS:
        print(f"Error: Unsupported output format '{output_format}'")
        return

    if (input_format == 'abif' and output_format == 'jabmod'):
        # Convert .abif to JSON-based model (.jabmod)
        abifmodel = convert_abif_to_jabmod(args.input_file,
                                           debugflag=DEBUGFLAG,
                                           extrainfo=False)
        try:
            outstr = json.dumps(abifmodel, indent=4)
        except BaseException:
            outstr = "NOT JSON SERIALIZABLE"
            outstr += pprint.pformat(abifmodel)
    elif (input_format == 'abif' and output_format == 'jabmodextra'):
        # Convert .abif to JSON-based model (.jabmod) with debug info
        abifmodel = convert_abif_to_jabmod(args.input_file,
                                           debugflag=DEBUGFLAG,
                                           extrainfo=True)
        try:
            outstr = json.dumps(abifmodel, indent=4)
        except BaseException:
            outstr = "NOT JSON SERIALIZABLE"
            outstr += pprint.pformat(abifmodel)
    elif (input_format == 'jabmod' and output_format == 'abif'):
        # Convert from JSON ABIF model (.jabmod) to .abif
        add_ratings = True

        if args.input_file == "-":
            abifmodel = json.load(sys.stdin)
        else:
            with open(args.input_file) as f:
                abifmodel = json.load(f)
        outstr = convert_jabmod_to_abif(abifmodel,
                                        add_ratings)
    elif (input_format == 'abif' and output_format == 'abif'):
        add_ratings = True
        abifmodel = convert_abif_to_jabmod(args.input_file,
                                           debugflag=DEBUGFLAG,
                                           extrainfo=False)
        outstr = convert_jabmod_to_abif(abifmodel,
                                        add_ratings)
    elif (input_format == 'widj' and output_format == 'abif'):
        # Convert from electowidget (.widj) to .abif
        add_ratings = True
        with open(args.input_file) as f:
            widgetjson = json.load(f)
            abifmodel = convert_widj_to_jabmod(widgetjson)
        outstr = convert_jabmod_to_abif(abifmodel,
                                        add_ratings)
    elif (input_format == 'widj' and output_format == 'jabmod'):
        # Convert from electowidget (.widj) to .abif
        with open(args.input_file) as f:
            widgetjson = json.load(f)
            abifmodel = convert_widj_to_jabmod(widgetjson)
        outstr = json.dumps(abifmodel, indent=2)
    else:
        outstr = \
            f"Cannot convert from {input_format} to {output_format} yet."

    print(outstr)


if __name__ == "__main__":
    main()
