#!/usr/bin/env python3
'''abiflib/util.py - misc ABIF-related functions'''

# Copyright (C) 2023, 2024, 2025 Rob Lanphier
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

def convert_text_to_abif(fromfmt, inputblobs, cleanws=False, add_ratings=False, metadata={}):
    if (fromfmt == 'abif'):
        try:
            abifmodel = convert_abif_to_jabmod(inputblobs[0],
                                               cleanws=cleanws,
                                               add_ratings=add_ratings)
        except ABIFVotelineException as e:
            print(f"ERROR: {e.message}")
            sys.exit()
    elif (fromfmt == 'debtally'):
        rawabifstr = convert_debtally_to_abif(inputblobs[0], metadata=metadata)
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (fromfmt == 'jabmod'):
        abifmodel = json.loads(inputblobs[0])
    elif (fromfmt == 'preflib'):
        rawabifstr = convert_preflib_str_to_abif(inputblobs[0])
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (fromfmt == 'sftxt'):
        abifmodel = convert_sftxt_to_jabmod(inputblobs[0], inputblobs[1])
    elif (fromfmt == 'widj'):
        abifmodel = convert_widj_to_jabmod(inputblobs[0])
    else:
        raise ABIFVotelineException(value=inputblobs[0],
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


def utf8_string_to_abif_token(longstring, max_length=20, add_sha1=False):
    '''Convert a name into a short token for use in abif'''
    # TODO: replace _short_token in sftxt.py with this
    # TDOO: make this more sophisticated, replacing candidate names with something
    #   recognizable as candidate names, even if there's a lot of upper ASCII in the
    #   name.
    if len(longstring) <= max_length and \
       re.match(r'^[A-Za-z0-9]+$', longstring):
        retval = longstring
    else:
        cleanstr = re.sub('[^A-Za-z0-9]+', '_', longstring)
        cleanstr = re.sub('WRITE_IN_', "wi_", cleanstr)
        retval = cleanstr[:max_length]
    return retval


