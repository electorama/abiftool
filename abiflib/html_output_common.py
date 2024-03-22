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

from abiflib import *
from abiflib.html_output import *

def get_abif_title(abifmodel):
    '''Title (or filename) from the abifmodel metadata'''
    metadata = abifmodel.get('metadata', None)
    defdesc = "(.metadata.title and .metadata.filename missing)"
    if metadata:
        retval = metadata.get('title', None)
        if not retval:
            retval = metadata.get('filename', defdesc)
    else:
        retval = defdesc
    return retval


def get_abif_desc(abifmodel):
    '''Description of the election from the abifmodel metadata'''
    metadata = abifmodel.get('metadata', None)
    cand_list_str = ', '.join(abifmodel['candidates'].values())
    default_desc = f"Candidate matchups for {cand_list_str}"
    if metadata:
        retval = metadata.get('description', default_desc)
    else:
        retval = default_desc
    return retval


def get_title_for_html(abifmodel):
    retval = f"abiflib/html_output.py Results: {get_abif_title(abifmodel)}"
    return retval


def validate_abifmodel(abifmodel):
    global ABIF_MODEL_LIMIT
    modlimit = ABIF_MODEL_LIMIT
    modsize = sys.getsizeof(abifmodel)
    err = f"Model size {modsize} exceeds modlimit {modlimit}"
    if modsize > modlimit:
        raise Exception(err)


