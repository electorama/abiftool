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
import os
from pathlib import Path
from pprint import pprint
import re
import sys
import urllib.parse

def find_ballot_type(abifmodel):
    """
    Find the type of ballots in a jabmod structure.

    First checks for manual ballot_type in metadata, then auto-detects.
    Returns one of: 'choose_one', 'choose_many', 'rated', 'ranked', 'unknown'
    """
    # Check for manual override first
    if 'metadata' in abifmodel and 'ballot_type' in abifmodel['metadata']:
        return abifmodel['metadata']['ballot_type']

    return _detect_ballot_type_from_data(abifmodel)


def _detect_ballot_type_from_data(abifmodel):
    """
    Auto-detect ballot type by analyzing voteline data.
    Uses core.py functions for consistent parsing.
    """
    from abiflib.core import _determine_rank_or_rate, _extract_candprefs_from_prefstr

    has_ratings = False
    has_binary_ratings = False
    has_non_binary_ratings = False
    has_multiple_choices = False
    has_equal_ranks = False
    format_types = set()
    non_blank_ballots = 0

    for vline in abifmodel['votelines']:
        # Skip blank ballots (no preferences)
        if not vline.get('prefs') or len(vline['prefs']) == 0:
            continue

        non_blank_ballots += vline.get('qty', 1)

        # Use prefstr if available, otherwise analyze prefs directly
        if 'prefstr' in vline and vline['prefstr'].strip():
            # Use core.py functions for consistent analysis
            rank_or_rate, delimiters = _determine_rank_or_rate(vline['prefstr'])
            format_types.add(rank_or_rate)

            candprefs = _extract_candprefs_from_prefstr(vline['prefstr'])
            ballot_ratings = []

            for cand, rating in candprefs:
                if rating is not None:
                    has_ratings = True
                    ballot_ratings.append(rating)
                    if rating in [0, 1]:
                        has_binary_ratings = True
                    else:
                        has_non_binary_ratings = True
        else:
            # Fallback: analyze prefs directly
            ballot_rankings = []
            ballot_ratings = []

            for cand, prefs in vline['prefs'].items():
                if 'rating' in prefs and prefs['rating'] is not None:
                    has_ratings = True
                    rating = prefs['rating']
                    ballot_ratings.append(rating)
                    if rating in [0, 1]:
                        has_binary_ratings = True
                    else:
                        has_non_binary_ratings = True

                if 'rank' in prefs and prefs['rank'] is not None:
                    ballot_rankings.append(prefs['rank'])

            # Check for equal rankings (ties)
            if ballot_rankings:
                unique_ranks = set(ballot_rankings)
                if len(unique_ranks) < len(ballot_rankings):
                    has_equal_ranks = True

        # Check if ballot has multiple choices
        if len(vline['prefs']) > 1:
            has_multiple_choices = True

    # If we have no non-blank ballots, we can't determine the type
    if non_blank_ballots == 0:
        return 'unknown'

    # Decision logic for ballot type

    # Priority 1: Non-binary ratings = rated ballot type (regardless of delimiters)
    if has_non_binary_ratings:
        return 'rated'

    # Priority 2: Binary-only ratings = choose_many ballot type
    if has_binary_ratings and not has_non_binary_ratings:
        return 'choose_many'

    # Priority 3: Use format analysis from prefstr when available
    if format_types:
        if 'rate' in format_types and not ('rank' in format_types):
            return 'choose_one'  # Comma-delimited without ratings
        elif 'rank' in format_types:
            if has_multiple_choices:
                return 'ranked'
            else:
                return 'choose_one'
        elif 'rankone' in format_types:
            return 'choose_one'

    # Fallback logic when prefstr analysis isn't available
    if has_multiple_choices:
        if has_ratings:
            return 'unknown'  # Mixed case
        else:
            return 'ranked'

    return 'choose_one'


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


def get_abiftool_dir():
    """Find the abiftool directory by finding abiftool.py."""
    # TODO: replace kludge.  There has got to be a better way of
    # finding all of the abif files downloaded with fetchmgr.py

    # 1. See if abiftool.py is in the parent to util.py
    util_dir = Path(__file__).parent
    parent_dir = util_dir.parent
    abiftool_py = parent_dir / 'abiftool.py'
    if abiftool_py.is_file():
        return str(parent_dir)

    # 2. See if abiflib is a symlink to make "import abiflib" work
    real_util_dir = Path(os.path.realpath(util_dir))
    real_parent = real_util_dir.parent
    abiftool_py_real = real_parent / 'abiftool.py'
    if abiftool_py_real.is_file():
        return str(real_parent)

    # 3. If installed as a wheel with data files, testdata may live under
    #    sys.prefix/testdata. In that case, return sys.prefix so callers that
    #    append '/testdata' will resolve correctly.
    prefix_testdata = Path(sys.prefix) / 'testdata'
    if prefix_testdata.is_dir():
        return str(Path(sys.prefix))

    # 4. Give up
    raise FileNotFoundError(
        "abiftool.py not found; and no testdata under sys.prefix/testdata.")


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
