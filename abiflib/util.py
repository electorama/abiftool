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

def detect_ballot_type(abifmodel):
    """
    Detect the type of ballots in a jabmod structure.

    Returns one of: 'approval', 'rated', 'ranked', 'choose_one', 'unknown'

    This function is designed to eventually be moved to core.py as a
    general utility for all voting methods.
    """
    has_ratings = False
    has_ranks = False
    has_binary_ratings = False
    has_non_binary_ratings = False
    has_equal_ranks = False
    has_multiple_choices = False
    has_comma_delimited = False
    has_rank_delimited = False
    non_blank_ballots = 0
    total_ballots = 0

    for vline in abifmodel['votelines']:
        total_ballots += vline.get('qty', 1)
        ballot_rankings = []
        ballot_ratings = []
        candidates_with_ratings = 0
        total_candidates_on_ballot = len(vline['prefs'])

        # Skip blank ballots (no preferences)
        if total_candidates_on_ballot == 0:
            continue

        non_blank_ballots += vline.get('qty', 1)

        for cand, prefs in vline['prefs'].items():
            # Check for ratings
            if 'rating' in prefs:
                has_ratings = True
                candidates_with_ratings += 1
                rating = prefs['rating']
                ballot_ratings.append(rating)

                # Check for binary ratings (0 or 1)
                if rating in [0, 1]:
                    has_binary_ratings = True
                else:
                    has_non_binary_ratings = True

            # Check for rankings
            if 'rank' in prefs:
                has_ranks = True
                rank = prefs['rank']
                ballot_rankings.append(rank)

        # Check for equal rankings (ties)
        if ballot_rankings:
            unique_ranks = set(ballot_rankings)
            if len(unique_ranks) < len(ballot_rankings):
                has_equal_ranks = True

        # Check if ballot has multiple choices
        if total_candidates_on_ballot > 1:
            has_multiple_choices = True

        # Detect delimiter patterns from original prefstr if available
        if 'prefstr' in vline:
            prefstr = vline['prefstr']
            if ',' in prefstr and '>' not in prefstr and '=' not in prefstr:
                has_comma_delimited = True
            if '>' in prefstr or '=' in prefstr:
                has_rank_delimited = True

    # If we have no non-blank ballots, we can't determine the type
    if non_blank_ballots == 0:
        return 'unknown'

    # Decision logic for ballot type

    # If we have comma-delimited format, it's not ranked
    if has_comma_delimited and not has_rank_delimited:
        if has_binary_ratings and not has_non_binary_ratings:
            return 'approval'
        elif has_non_binary_ratings:
            return 'rated'
        elif not has_ratings and has_multiple_choices:
            return 'unknown'  # Comma-delimited without ratings is ambiguous
        else:
            return 'choose_one'

    # Binary ratings or equal ranks with ratings = approval
    if has_binary_ratings and not has_non_binary_ratings:
        if has_equal_ranks or not has_ranks:
            return 'approval'

    # Non-binary ratings = rated (if all candidates have ratings)
    if has_non_binary_ratings:
        return 'rated'

    # Pure rankings without ratings
    if has_ranks and not has_ratings:
        if has_multiple_choices:
            return 'ranked'
        else:
            return 'choose_one'

    # Mixed ratings and rankings
    if has_ratings and has_ranks:
        if has_binary_ratings and not has_non_binary_ratings:
            return 'approval'
        elif has_non_binary_ratings:
            return 'rated'
        else:
            return 'unknown'

    # No clear pattern detected
    if has_multiple_choices:
        return 'unknown'
    else:
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

    # 3. Give up
    raise FileNotFoundError(
        "abiftool.py not found in {parent_dir} or {real_parent}.")


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

