#!/usr/bin/env python3
# abiflib/core.py - core ABIF<=>jabmod conversion functions
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
import copy
import json
from pprint import pprint
import re
import sys
import urllib.parse

def convert_text_to_abif(fromfmt, inputstr, cleanws=False, add_ratings=False, metadata={}):

    if (fromfmt == 'abif'):
        try:
            abifmodel = convert_abif_to_jabmod(inputstr,
                                               cleanws=cleanws,
                                               add_ratings=add_ratings)
        except ABIFVotelineException as e:
            print(f"ERROR: {e.message}")
            sys.exit()
    elif (fromfmt == 'debtally'):
        rawabifstr = convert_debtally_to_abif(inputstr, metadata=metadata)
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (fromfmt == 'jabmod'):
        abifmodel = json.loads(inputstr)
    elif (fromfmt == 'preflib'):
        rawabifstr = convert_preflib_str_to_abif(inputstr)
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (fromfmt == 'widj'):
        abifmodel = convert_widj_to_jabmod(inputstr)
    else:
        raise ABIFVotelineException(value=inputstr,
                                    message=f"Cannot convert from {fromfmt} yet.")
    retval = convert_jabmod_to_abif(abifmodel, add_ratings=False)
    return retval


def candlist_text_from_abif(jabmod):
    canddict = jabmod['candidates']
    output = ""
    output += "Candidates:\n"
    for k, v in sorted(canddict.items()):
        output += f"  {k}: {v}\n"
    return output
