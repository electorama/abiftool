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
from abiflib.pairwise import *
import argparse
import json
import sys
try:
    from bs4 import BeautifulSoup
except:
    pass


def htmltable_pairwise_and_winlosstie(abifmodel,
                                      snippet = False,
                                      validate = False,
                                      modlimit = 50):
    '''Generate HTML summary of election as abifmodel

    The "abifmodel" is the internal data structure for abiflib,
    referred to as "jabmod" when expressed as JSON.  This function
    accepts an abifmodel, and returns HTML that tallies pairwise
    elections for the rankings expressed in the abifmodel.
    '''

    # A few functions used within htmltable_pairwise_and_winlosstie
    def wltstr(cand):
        '''String representation of the wins, losses, and ties'''
        retval = f"{wltdict[cand]['wins']}" + "-"
        retval += f"{wltdict[cand]['losses']}" + "-"
        retval += f"{wltdict[cand]['ties']}"
        return retval

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
        defdesc = f"(.metadata.description missing)"
        if metadata:
            retval = metadata.get('description', defdesc)
        else:
            retval = defdesc
        return retval

    def get_winlosstie_sorted_keys(pairdict, wltdict):
        '''Sort the candidates by win/loss/tie record'''
        # TODO, consider win-loss-tie, not just "wins"
        return sorted(pairdict.keys(),
                      key=lambda x: wltdict[x]['wins'],
                      reverse=True)

    def get_title_for_html(abifmodel):
        retval = f"abiflib/html_output.py Results: {get_abif_title(abifmodel)}"
        return retval

    def validate_abifmodel(abifmodel):
        modsize = sys.getsizeof(abifmodel)
        err = f"Model size {modsize} exceeds modlimit {modlimit}"
        if modsize > modlimit:
            raise Exception(err)

    # Initialization of key variables
    if validate:
        validate_abifmodel(abifmodel)
    retval = ""
    pairdict = pairwise_count_dict(abifmodel)
    wltdict = winlosstie_dict_from_pairdict(abifmodel['candidates'], pairdict)
    mytitle = get_title_for_html(abifmodel)
    candtoks = get_winlosstie_sorted_keys(pairdict, wltdict)
    candnames = abifmodel.get('candidates', None)

    # Soup initialization
    soup = BeautifulSoup('', 'html.parser')
    html_doc = soup.new_tag('html')

    if not snippet:
        # Soup head
        head = soup.new_tag('head')
        title = soup.new_tag('title')
        title.string = get_title_for_html(abifmodel)
        head.append(title)

        # Soup body
        body = soup.new_tag('body')
        h1 = soup.new_tag('h1')
        h1.string = get_title_for_html(abifmodel)
        body.append(h1)
    desc = soup.new_tag('p')
    desc.string = f'{get_abif_desc(abifmodel)}'
    if snippet:
        soup.append(desc)        
    else:
        body.append(desc)

    # Soup table
    table = soup.new_tag('table')
    table['border'] = "1"

    # Soup table header row init
    header_text_array = ['Candidate']
    header_text_array.extend(candtoks)

    wltcolspan = len(candtoks) + 1
    candnames = abifmodel.get('candidates', None)

    # Soup table data rows
    # ck = column key
    # rk = row key
    for i, ck in enumerate(candtoks):
        isPastDivider = False
        candrow = soup.new_tag('tr')
        candrow_label = soup.new_tag('th')
        candrow_label.string = f"{candnames[ck]}"
        if ck != candnames[ck]:
            candrow_label.string += f" [\"{ck}\"]"
        candrow.append(candrow_label)
        candrow_wlt = soup.new_tag('td')
        candrow_wlt['colspan'] = wltcolspan
        candrow_wlt.string = f"({wltstr(ck)})"
        candrow.append(candrow_wlt)
        for j, rk in enumerate(candtoks):
            thiscell = soup.new_tag('td')
            # breaking out of rendering this line if we hit
            # the blank diagonal line of the matrix where
            # candidates are matched against themselves.
            if ck == rk:
                break
            else:
                pairstr = ""
                pairstr += f"{rk}:{pairdict[rk][ck]}"
                pairstr += f" -- "
                pairstr += f"{ck}:{pairdict[ck][rk]}"
                thiscell.string = pairstr
            candrow.append(thiscell)
        candrow_loss_point = soup.new_tag('td')
        if wltdict[ck]['losses'] > 0:
            candrow_loss_point.string = f"<- {ck} losses"
        else:
            candrow_loss_point.string = f"{ck} is undefeated"
        candrow.append(candrow_loss_point)

        wltcolspan += -1
        table.append(candrow)

    # Finalize soup table
    if snippet:
        soup.append(table)
    else:
        body.append(table)
        html_doc.append(head)
        html_doc.append(body)
        soup.append(html_doc)

    retval += soup.prettify()

    return retval


def main():
    """Convert jabmod to html-formatted tally"""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('input_file', help='Input jabmod')

    args = parser.parse_args()

    with open(args.input_file, "r") as f:
        abifmodel = json.load(f)

    abifmodel['metadata']['filename'] = args.input_file
    outstr = ""
    outstr += htmltable_pairwise_and_winlosstie(abifmodel)
    print(outstr)


if __name__ == "__main__":
    main()
