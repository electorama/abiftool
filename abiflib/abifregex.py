#!/usr/bin/env python3
# abiflib/abifregexp.py - Global ABIF-related variables and funcs
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

COMMENT_REGEX = r'''
    ^                       # beginning of line
    (?P<beforesep>[^\#]*)   # before the comment separator
    (?P<comsep>\#+)         # # or ## comment separator
    (?P<whitespace>\s*)     # optional whitespace
    (?P<aftersep>.*)        # after the # separator/whitespace
    $                       # end of line
    '''

VOTERID_REGEX = r'''
    (?P<vidprefix>\#\#VID:) # portion to match exactly to co-opt comment
    (?P<voterid>\S+)        # voter id (with no spaces)
'''

METADATA_REGEX = r'''
    ^\{                     # abif metadata lines always start with '{'
    \s*                     # whitespace
    [\'\"]?                 # optional quotation marks (single or double)
    ([\w\s]+)               # METADATA KEY
    \s*                     # moar whitespace!!!!
    [\'\"]?                 # ending quotation
    \s*                     # abif loves whitespace!!!!!
    :                       # COLON! Very important!
    \s*                     # moar whitesapce!!!1!
    [\'\"]?                 # abif also loves optional quotes
    ([\w\s\,\.\(\)\-\?\:\'/]+)  # METADATA VALUE
    \s*                     # more whitespace 'cuz
    [\'\"]?                 # moar quotes
    \s*                     # spaces the finals frontiers
    \}                      # look!  squirrel!!!!!
    $'''

CANDLINE_REGEX = r'''
    ^\=                     # the first character of candlines: "="
    \s*                     # whitespace
    ["\[]?                  # optional '[' or '"' prior to candtoken
    ([^:\"\]]*)             # candtoken; disallowed: " or ] or :
    ["\[]?                  # optional '[' or '"' after candtoken
    :                       # separator
    \[?                     # optional '[' prior to canddesc
    ([^\]]*)                # canddesc
    \]?                     # optional ']' after canddesc
    $                       # That's all, folks!
    '''

VOTELINE_REGEX = r'^(\d+):(.*)$'

VOTELINE_PREFPART_REGEX = r'''
    ^                         # start of string
    \s*                       # Optional whitespace
    (?P<candplusrate>         # <candplusrate> begin
    (
    (?P<candbare>[A-Za-z0-9_\-]*)   # <cand> (bare token)
    |
    [\"\[]                    # beginning quotation or square bracket
    (?P<candsqr>[^\"\]]*)     # <cand> (within quotes or square brackets)
    [\"\]]                    # ending quotation or square bracket
    )
    (/                        # optional slashrating begin
    (?P<rating>\d+)           # optional <rating> (number)
    \s*)?                     # optional slashrating end
    )                         # <candplusrate> end
    (?P<restofline>.*)        # the <restofline>
    $                         # end of string
    '''
