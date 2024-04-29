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
from abiflib.html_output import *
import argparse
import json
import sys
try:
    from bs4 import BeautifulSoup
except:
    pass

def htmltable_pairwise_and_winlosstie(abifmodel,
                                      add_desc = True,
                                      snippet = False,
                                      validate = False,
                                      clean = False,
                                      modlimit = 50,
                                      svg_text = None,
                                      modifiers = set()):
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


    def get_winlosstie_sorted_keys(pairdict, wltdict):
        '''Sort the candidates by win/loss/tie record'''
        # TODO, consider win-loss-tie, not just "wins"
        return sorted(pairdict.keys(),
                      key=lambda x: wltdict[x]['wins'],
                      reverse=True)

    # Initialization of key variables
    if validate:
        validate_abifmodel(abifmodel)
    retval = ""
    pairdict = pairwise_count_dict(abifmodel)
    wltdict = winlosstie_dict_from_pairdict(abifmodel['candidates'], pairdict)
    try:
        mytitle = get_title_for_html(abifmodel)
    except:
        global_namespace = globals()
        global_functions = [name for name, obj in global_namespace.items() if callable(obj)]
        print(global_functions) 
        raise
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
    if add_desc:
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
    has_ties_or_cycles = False

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
        candrow_wlt = soup.new_tag('td', attrs={'style': 'padding-right: 3em;'})
        candrow_wlt['colspan'] = wltcolspan
        candrow_wlt.string = f"({wltstr(ck)})"
        wincaption = \
            soup.new_tag('td', attrs={'style': 'text-align: center;'})
        if wltdict[ck]['wins'] > 0:
            appendme = soup.new_tag('div')
            appendme.string = f"{ck} victories"
            wincaption.append(appendme)
            #appendme = soup.new_tag('div',
            #                        style="float: center; white-space: nowrap;")
            #appendme.string = "victories"
            #wincaption.append(appendme)
            appendme = soup.new_tag('div', style="float: center;")
            appendme.string = "↓"
            wincaption.append(appendme)
        else:
            candrow_wlt['colspan'] += 1

        candrow.append(candrow_wlt)
        if wltdict[ck]['wins'] > 0:
            candrow.append(wincaption)

        for j, rk in enumerate(reversed(candtoks)):
            thiscell = soup.new_tag('td', style='justify-content: center;')
            # breaking out of rendering this line if we hit
            # the blank diagonal line of the matrix where
            # candidates are matched against themselves.
            if ck == rk:
                pass
            elif candtoks.index(ck) < candtoks.index(rk):
                pass
            else:
                rkscore = pairdict[rk][ck]
                ckscore = pairdict[ck][rk]
                scorespan = \
                    soup.new_tag('div', style='text-align: right;')
                winspan = \
                    soup.new_tag('div', style='white-space: nowrap;')
                winspan.string = f"{rk}: {rkscore}"
                scorespan.append(winspan)
                #breakspan = soup.new_tag('div')
                #breakspan.string = " — "
                #thiscell.append(breakspan)
                lossspan = soup.new_tag('div', style ='white-space: nowrap;')
                lossspan.string = f"{ck}: {ckscore}"
                if not rkscore > ckscore:
                    dagspan = soup.new_tag('sup')
                    dagspan.string = "†"
                    has_ties_or_cycles = True
                    lossspan.append(dagspan)
                scorespan.append(lossspan)
                thiscell.append(scorespan)
                candrow.append(thiscell)
        candrow_loss_point = soup.new_tag('td')
        if wltdict[ck]['losses'] > 0:
            candrow_loss_point.string = f"← {ck} losses"
        else:
            candrow_loss_point.string = f"{ck} is undefeated"
        candrow.append(candrow_loss_point)

        wltcolspan += -1
        table.append(candrow)

    results_div = soup.new_tag("div")
    if svg_text:
        svg_diagram = BeautifulSoup(svg_text, 'xml')
        svg_scroll = soup.new_tag("div",
                                  attrs={"class": "hscroll"})
        svg_scroll.append(svg_diagram)
        results_div.append(svg_scroll)
    table_scroll = soup.new_tag("div",
                                attrs={"class": "hscroll"})
    table_scroll.append(table)
    results_div.append(table_scroll)
    if has_ties_or_cycles:
        results_div.append(dagspan)
        results_div.append("\"Victories\" and \"losses\" sometimes aren't " +
                           "displayed in the expected location when there " +
                           "are ties and/or cycles in the results, but the " +
                           "numbers provided should be accurate.")
    if snippet:
        soup.append(results_div)
    else:
        body.append(results_div)
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
