#!/usr/bin/env python3
''' textoutput.py - Utility functions for structured data '''

# Copyright (C) 2023, 2025 Rob Lanphier
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
from abiflib.pairwise_tally import pairwise_count_dict, winlosstie_dict_from_pairdict
from itertools import zip_longest
import re
import textwrap

try:
    from texttable import Texttable
except ModuleNotFoundError as exc:
    if exc.name != 'texttable':
        raise
    Texttable = None


def _plain_text_table(rows, width):
    cells = [[str(value).split('\n') for value in row] for row in rows]
    widths = [max(1, max(len(line) for cell in column for line in cell))
              for column in zip(*cells)]
    padding = 3 * len(widths) + 1
    if width and sum(widths) + padding > width:
        limit = max(1, (width - padding) // len(widths))
        widths = [min(size, limit) for size in widths]

    separator = '+' + '+'.join('-' * (size + 2) for size in widths) + '+'
    lines = [separator]
    for index, row in enumerate(cells):
        wrapped = [
            [part for line in cell for part in (textwrap.wrap(line, size) or [''])]
            for cell, size in zip(row, widths)
        ]
        for parts in zip_longest(*wrapped, fillvalue=''):
            values = [part.ljust(size) for part, size in zip(parts, widths)]
            lines.append('| ' + ' | '.join(values) + ' |')
        lines.append(separator if index else separator.replace('-', '='))
    return '\n'.join(lines) + '\n\n'


def _render_text_table(rows, width=None):
    if Texttable is None:
        return _plain_text_table(rows, width)

    table = Texttable() if width is None else Texttable(max_width=width)
    for row in rows:
        table.add_row(row)

    lines = table.draw().splitlines()
    # Distinguish the header separator and the row-label column.
    lines[3] = lines[3].replace('-', '=')
    for index, line in enumerate(lines):
        formatted, count = re.subn(r'\|', '+', line, count=2)
        if count > 1:
            lines[index] = formatted
    return '\n'.join(lines) + '\n\n'


def textgrid_for_2D_dict(twodimdict, tablelabel='   Loser ->\nv Winner', width=160):
    rows = [[tablelabel, *twodimdict]]
    for cand, inner_dict in twodimdict.items():
        rows.append([cand, *inner_dict.values()])
    return _render_text_table(rows, width)


def texttable_pairwise_and_winlosstie(abifmodel):
    pairdict = pairwise_count_dict(abifmodel)
    wltdict = winlosstie_dict_from_pairdict(abifmodel['candidates'], pairdict)
    candkeys = sorted(pairdict, key=lambda key: wltdict[key]['wins'], reverse=True)
    rows = [['   Loser ->\nv Winner', *candkeys]]
    for key in candkeys:
        result = wltdict[key]
        record = f"{result['wins']}-{result['losses']}-{result['ties']}"
        rows.append([f'{key} ({record})', *(pairdict[key][other] for other in candkeys)])
    return _render_text_table(rows)


def headerfy_text_file(filetext, filename="???"):
    retval = ""
    retval += "============================\n"
    retval += f"{filename}\n"
    retval += "-------------------------\n"
    retval += filetext
    return retval


def format_notices_for_text_output(notices):
    """Format notices array into text output with consistent formatting.

    Args:
        notices: List of notice dictionaries with 'notice_type', 'short', and 'long' keys

    Returns:
        String with formatted notices, or empty string if no notices
    """
    if not notices:
        return ""

    result = ""
    for notice in notices:
        notice_type = notice.get('notice_type', 'info').upper()
        result += f"\n[{notice_type}] {notice['short']}\n"

        if notice.get('long'):
            # Handle paragraph breaks by processing each paragraph separately
            paragraphs = notice['long'].split('\n\n')
            wrapped_paragraphs = []
            for paragraph in paragraphs:
                if paragraph.strip():  # Skip empty paragraphs
                    wrapped = textwrap.fill(paragraph.strip(), width=76,
                                            initial_indent='  ',
                                            subsequent_indent='  ')
                    wrapped_paragraphs.append(wrapped)

            if wrapped_paragraphs:
                result += "\n" + "\n\n".join(wrapped_paragraphs) + "\n"

    return result


if __name__ == "__main__":
    main()
