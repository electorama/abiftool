#!/usr/bin/env python3
# abiftool.py - conversion to/from .abif to other electoral expressions
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
import argparse
import json
import os
import re
import sys
import urllib.parse

INPUT_FORMATS = [
    {'abif': 'ABIF format'},
    {'debtally': 'Election output format used by the Debian Project'},
    {'jabmod': 'Internal JSON ABIF model (Json ABIF MODel)'},
    {'preflib': 'Files downloaded from preflib.org'},
    {'widj': 'Legacy format from Electowidget'}
]

OUTPUT_FORMATS = [
    {'abif': 'ABIF format'},
    {'dot': 'Graphviz DOT format showing pairwise matchups'},
    {'html': 'Full HTML output from <html> to </html>'},
    {'html_snippet': 'HTML snippet that does not includes the <head> elements'},
    {'jabmod': 'Internal JSON ABIF model (Json ABIF MODel)'},
    {'paircountjson': 'Pairwise ballot counts'},
    {'svg': 'SVG output showing pairwise matchups and Copeland wins/losses/ties'},
    {'text': 'Text table showing pairwise matchups and Copeland wins/losses/ties'},
    {'winlosstiejson': 'JSON format representing win, loss, and tie counts'}
]

MODIFIERS = [
    {'nopairwise': 'Remove any pairwise tables if possible'},
    {'nowinlosstie': 'Remove win-loss-tie info if possible'},
    {'score': 'Provide score results'},
    {'STAR': 'Provide STAR results'},
    {'Copeland': 'Show Copeland winner'},
    {'svg': 'Add SVG to the output if avaiable'},
    {'winlosstie': 'Add win-loss-tie info if possible (default)'}
]

ABIF_VERSION = "0.1"
ABIFMODEL_LIMIT = 2500
LOOPLIMIT = 400

def gen_epilog():
    ''' Generate format list for --help '''
    def help_text(caption='XX', bullet='* ',
                  dictlist=None):
        retval = f"{caption}:\n"
        for fmtdicts in dictlist:
            for fkey, fdesc in fmtdicts.items():
                retval += f"{bullet} {fkey}: {fdesc}\n"
        return retval
    retval = ''
    retval += help_text(caption="Input formats", bullet="--from",
                        dictlist=INPUT_FORMATS)
    retval += f"\n"
    retval += help_text(caption="Output formats", bullet="--to",
                        dictlist=OUTPUT_FORMATS)
    retval += f"\n"
    retval += help_text(caption="Modifiers (preface with 'no' to remove)",
                        bullet="--modifier", dictlist=MODIFIERS)
    return retval

def get_keys_from_dict_list(dictlist):
    retval = [key for d in dictlist for key in d]
    return retval

def main():
    """Convert between .abif-adjacent formats."""
    parser = argparse.ArgumentParser(
        description='Convert between .abif and JSON formats',
        epilog=gen_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    validinfmts = get_keys_from_dict_list(INPUT_FORMATS)
    validoutfmts = get_keys_from_dict_list(OUTPUT_FORMATS)
    validmod = get_keys_from_dict_list(MODIFIERS)
    parser.add_argument('input_file', help='Input file to convert (--help for list of options)')
    parser.add_argument('-f', '--fromfmt', choices=validinfmts,
                        help='Input format (overrides file extension)')
    parser.add_argument('-t', '--to', choices=validoutfmts,
                        required=True, help='Output format (--help for list of options)')
    parser.add_argument("-m", "--modifier", default=['winlosstie'], action='append',
                        choices=validmod, help='Catch-all for modified output specifiers.')
    parser.add_argument('--cleanws', action="store_true",
                        help='Clean whitespace in ABIF file')
    parser.add_argument('--add-scores', action="store_true",
                        help='Add scores to votelines when only rankings are provided')

    args = parser.parse_args()
    modifiers = set(args.modifier)

    # Determine input format based on file extension or override from
    # the "-f/--fromfmt" option
    if args.fromfmt:
        input_format = args.fromfmt
    elif args.input_file == '-':
        parser.error("The -f parameter is required with '-'")
    else:
        _, file_extension = args.input_file.rsplit('.', 1)
        input_format = file_extension
    if input_format not in validinfmts:
        print(f"Error: Unsupported input format '{input_format}'")
        return

    inputstr = ""
    if args.input_file == '-':
        inputstr = sys.stdin.read()
    elif not os.path.exists(args.input_file):
        print(f"The file '{args.input_file}' doesn't exist.")
        sys.exit()
    else:
        with open(args.input_file, "r") as f:
            inputstr = f.read()

    add_STAR = 'STAR' in modifiers
    add_scores = 'scores' in modifiers
    add_ratings = args.add_scores or add_STAR or add_scores
    if (input_format == 'abif'):
        try:
            abifmodel = convert_abif_to_jabmod(inputstr,
                                               cleanws=args.cleanws,
                                               add_ratings=add_ratings)
        except ABIFVotelineException as e:
            print(f"ERROR: {e.message}")
            sys.exit()
    elif (input_format == 'debtally'):
        rawabifstr = convert_debtally_to_abif(inputstr)
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (input_format == 'jabmod'):
        abifmodel = json.loads(inputstr)
    elif (input_format == 'preflib'):
        rawabifstr = convert_preflib_str_to_abif(inputstr)
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (input_format == 'widj'):
        abifmodel = convert_widj_to_jabmod(inputstr)
    else:
        outstr = f"Cannot convert from {input_format} yet."
        print(outstr)
        sys.exit()

    # the "-t/--to" option
    output_format = args.to
    if output_format not in validoutfmts:
        print(f"Error: Unsupported output format '{output_format}'")
        return

    outstr = ''
    copecount = full_copecount_from_abifmodel(abifmodel)
    if (output_format == 'abif'):
        outstr += convert_jabmod_to_abif(abifmodel)
    elif (output_format == 'dot'):
        outstr += copecount_diagram(copecount, outformat='dot')
    elif (output_format == 'html'):
        outstr += htmltable_pairwise_and_winlosstie(abifmodel)
    elif (output_format == 'html_snippet'):
        if 'svg' in modifiers:
            svg_text = copecount_diagram(copecount, outformat='svg')
        else:
            svg_text = None
        outstr = htmltable_pairwise_and_winlosstie(abifmodel,
                                                   snippet = True,
                                                   validate = True,
                                                   modlimit = ABIFMODEL_LIMIT,
                                                   svg_text = svg_text,
                                                   modifiers = modifiers)
    elif (output_format == 'jabmod'):
        outstr += json.dumps(abifmodel, indent=4)
    elif (output_format == 'paircountjson'):
        pairdict = pairwise_count_dict(abifmodel)
        outstr += json.dumps(pairdict, indent=4)
    elif (output_format == 'svg'):
        outstr += copecount_diagram(copecount, outformat='svg')
    elif (output_format == 'text'):
        if 'nopairwise' in modifiers:
            pass
        elif 'nowinlosstie' in modifiers:
            pairdict = pairwise_count_dict(abifmodel)
            outstr += textgrid_for_2D_dict(
                twodimdict=pairdict,
                tablelabel='   Loser ->\nv Winner')
        else:
            outstr += texttable_pairwise_and_winlosstie(abifmodel)
        if 'score' in modifiers:
            outstr += score_report(abifmodel)
        if 'STAR' in modifiers:
            outstr += STAR_report(abifmodel)
        if 'Copeland' in modifiers:
            outstr += Copeland_report(abifmodel['candidates'], copecount)
    elif (output_format == 'winlosstiejson'):
        pairdict = pairwise_count_dict(abifmodel)
        wltdict = winlosstie_dict_from_pairdict(abifmodel['candidates'],
                                                pairdict)
        outstr += json.dumps(wltdict, indent=4)
    else:
        outstr += f"Cannot convert to {output_format} yet."

    print(outstr)


if __name__ == "__main__":
    main()
