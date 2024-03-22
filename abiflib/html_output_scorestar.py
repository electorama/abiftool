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
from abiflib.scorestar import *
from abiflib.html_output import *
import argparse
import json
import sys
try:
    from bs4 import BeautifulSoup
except:
    pass

import html

def html_score_and_star(abifmodel):
    content = STAR_report(abifmodel)
    escaped_content = [html.escape(line) for line in content]
    soup = BeautifulSoup('', 'html.parser')
    
    pre_tag = soup.new_tag('pre')
    pre_tag.string = ''.join(escaped_content)
    
    soup.append(pre_tag)
    retval = str(soup)
    return retval


def main():
    """Convert jabmod to html-formatted STAR results"""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('input_file', help='Input jabmod')

    args = parser.parse_args()

    with open(args.input_file, "r") as f:
        abifmodel = json.load(f)

    abifmodel['metadata']['filename'] = args.input_file
    outstr = ""
    outstr += html_score_and_star(abifmodel)
    print(outstr)


if __name__ == "__main__":
    main()
