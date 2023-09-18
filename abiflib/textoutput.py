#!/usr/bin/env python3
# textoutput.py - Utility functions for structured data
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
import argparse
import json
import re
import sys
import texttable
from texttable import Texttable
import urllib.parse

DEBUGFLAG = False


def debugprint(str):
    global DEBUGFLAG
    if DEBUGFLAG:
        print(str)
    return


def textgrid_for_2D_dict(twodimdict,
                         DEBUGFLAG=DEBUGFLAG,
                         tablelabel="YYYYYYX"):
    # The first level of dict keys becomes row labels
    # The second level of dict keys becomes column labels

    retval = ""

    if DEBUGFLAG:
        retval += "=============================\n"
        retval += "textgrid_for_2D_dict:\n"

    table = Texttable()
    ctok = list(twodimdict.keys())
    table.add_row([tablelabel] + ctok)

    for cand, inner_dict in twodimdict.items():
        try:
            mylist = list(inner_dict.values())
            table.add_row([cand] + mylist)
        except AttributeError:
            print(inner_dict)
            raise

    tabletext = table.draw()
    tabletextarray = tabletext.splitlines()

    third_line = tabletextarray[2]
    new_third_line = re.sub("-", "=", third_line)
    tabletextarray[2] = new_third_line

    subarray = []
    for i, ln in enumerate(tabletextarray):
        newln, count = re.subn(r"\|", r"+", ln, count=2)
        if count > 1:
            tabletextarray[i] = newln

    retval += "\n".join(tabletextarray)
    retval += "\n\n"
    return retval


def headerfy_text_file(textfile):
    retval = ""
    retval += "============================\n"
    retval += f"{textfile=}\n"
    retval += "-------------------------\n"
    with open(textfile) as f:
        retval += f.read()
    return retval


if __name__ == "__main__":
    main()
