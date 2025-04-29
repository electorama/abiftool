#!/usr/bin/env python3
''' abiftool.py - conversion to/from .abif to other electoral expressions '''

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

import os
import sys

try:
    from abiflib import *
except ModuleNotFoundError as e:
    print(f"ModuleNotFoundError: {e.name}\n")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("Please install the following modules listed in abiftool/requirements.txt:\n")
    with open("requirements.txt", "r") as req_file:
        print(req_file.read())
    print("You may also run 'pip install -r requirements.txt' to install all modules.")
    sys.exit()

import argparse
import json
import re
import urllib.parse


INPUT_FORMATS = [
    {'abif': 'ABIF format'},
    {'debtally': 'Election output format used by the Debian Project'},
    {'jabmod': 'Internal JSON ABIF model (Json ABIF MODel)'},
    {'nameq': 'Brian Olson\'s format which URL-encoded version of the raw ballots'},
    {'preflib': 'Files downloaded from preflib.org'},
    {'sftxt': 'Text files published by the City and County of San Francisco'},
    {'widj': 'Legacy format from Electowidget'}
]

OUTPUT_FORMATS = [
    {'abif': 'ABIF format'},
    {'csvrank': 'CSV rank format used by the online RCV tool by Dan Eckam'},
    {'dot': 'Graphviz DOT format showing pairwise matchups'},
    {'html': 'Full HTML output from <html> to </html>'},
    {'html_snippet': 'HTML snippet that does not includes the <head> elements'},
    {'irvjson': 'JSON format representing IRV election results'},
    {'jabmod': 'Internal JSON ABIF model (Json ABIF MODel)'},
    {'json': 'JSON format as specified in corresponding modifier'},
    {'nameq': 'Brian Olson\'s format which URL-encoded version of the raw ballots'},
    {'paircountjson': 'Pairwise ballot counts'},
    {'svg': 'SVG output showing pairwise matchups and Copeland wins/losses/ties'},
    {'text': 'Text table showing pairwise matchups and Copeland wins/losses/ties'},
    {'winlosstiejson': 'JSON format representing win, loss, and tie counts'}
]

MODIFIERS = [
    {'candlist': 'List all candidates at the beginning of output'},
    {'Copeland': 'Show pairwise table and Copeland winner (default)'},
    {'consolidate': 'Consolidate votelines if possible'},
    {'FPTP': 'Show FPTP results'},
    {'IRV': 'Show IRV/RCV results'},
    {'jcomments': 'Put comments in jabmod output if available'},
    {'pairwise': 'Show pairwise table (possibly without winlosstie info)'},
    {'score': 'Provide score results'},
    {'STAR': 'Provide STAR results'},
    {'svg': 'Add SVG to the output if avaiable'},
    {'winlosstie': 'Provide win-loss-tie table (default)'}
]

ABIF_VERSION = "0.1"
ABIFMODEL_LIMIT = 2500

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
    retval += help_text(caption="Modifiers",
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
    parser.add_argument('input_file', nargs='+',
                        help='Input file(s) to convert (--help for list of options)')
    parser.add_argument('-d', '--debug', action="store_true",
                        help='Output debug information if available')
    parser.add_argument('-f', '--fromfmt', choices=validinfmts,
                        help='Input format (overrides file extension)')
    parser.add_argument('-t', '--to', choices=validoutfmts, default="text",
                        help='Output format (--help for list of options)')
    parser.add_argument("-m", "--modifier", action='append',
                        choices=validmod, help='Catch-all for modified output specifiers.')
    parser.add_argument("-w", "--width", type=int, default=160,
                        help="width when rendering output with texttable lib" )
    parser.add_argument('--cleanws', action="store_true",
                        help='Clean whitespace in ABIF file')
    parser.add_argument('--add-scores', action="store_true",
                        help='Add scores to votelines when only rankings are provided')

    args = parser.parse_args()
    abiflib_test_log(f"cmd: {' '.join(sys.argv)}")

    # Determine input format based on file extension or override from
    # the "-f/--fromfmt" option
    if args.fromfmt:
        input_format = args.fromfmt
    elif args.input_file == '-':
        parser.error("The -f parameter is required with '-'")
    elif args.input_file[0].find('.') >= 0:
        _, file_extension = args.input_file[0].rsplit('.', 1)
        input_format = file_extension
    else:
        input_format = 'abif'
    if input_format not in validinfmts:
        print(f"Error: Unsupported input format '{input_format}'")
        return

    inputstr = ""
    inputblobs = []
    if args.input_file == '-' or args.input_file == ['-']:
        inputstr = sys.stdin.read()
    elif type(args.input_file) == list:
        for i, infile in enumerate(args.input_file):
            if not os.path.exists(infile):
                print(f"The file '{infile}' doesn't exist.")
                sys.exit()
            with open(infile, "r") as f:
                inputstr = f.read()
            inputblobs.append(inputstr)
    elif not os.path.exists(args.input_file):
        print(f"The file '{args.input_file}' doesn't exist.")
        sys.exit()
    else:
        with open(args.input_file, "r") as f:
            inputstr = f.read()
    if args.modifier:
        modifiers = set(args.modifier)
    else:
        modifiers = set(['candlist', 'Copeland', 'winlosstie'])
    add_ratings = args.add_scores

    storecomments = 'jcomments' in modifiers
    if (input_format == 'abif'):
        try:
            abifmodel = convert_abif_to_jabmod(inputstr,
                                               cleanws=args.cleanws,
                                               add_ratings=add_ratings,
                                               storecomments=storecomments)
        except ABIFVotelineException as e:
            print(f"ERROR: {e.message}")
            raise
    elif (input_format == 'debtally'):
        rawabifstr = convert_debtally_to_abif(inputstr)
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (input_format == 'jabmod'):
        abifmodel = json.loads(inputstr)
    elif (input_format == 'nameq'):
        abifmodel = convert_nameq_to_jabmod(inputstr)
    elif (input_format == 'preflib'):
        rawabifstr = convert_preflib_str_to_abif(inputstr)
        abifmodel = convert_abif_to_jabmod(rawabifstr)
    elif (input_format == 'sftxt'):
        abifmodel = convert_sftxt_to_jabmod(inputblobs[0], inputblobs[1])
    elif (input_format == 'widj'):
        abifmodel = convert_widj_to_jabmod(inputstr)
    else:
        outstr = f"Cannot convert from {input_format} yet."
        print(outstr)
        sys.exit()

    # global modifiers
    if 'consolidate' in modifiers:
        abifmodel =  consolidate_jabmod_voteline_objects(abifmodel)

    # the "-t/--to" option
    output_format = args.to
    if output_format not in validoutfmts:
        print(f"Error: Unsupported output format '{output_format}'")
        return

    outstr = ''
    if (output_format == 'abif'):
        outstr += convert_jabmod_to_abif(abifmodel)
    elif (output_format == 'csvrank'):
        outstr += get_ranking_output_csv(abifmodel)
    elif (output_format == 'dot'):
        copecount = full_copecount_from_abifmodel(abifmodel)
        outstr += copecount_diagram(copecount, outformat='dot')
    elif (output_format == 'html'):
        outstr += htmltable_pairwise_and_winlosstie(abifmodel)
    elif (output_format == 'html_snippet'):
        copecount = full_copecount_from_abifmodel(abifmodel)
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
    elif (output_format in ['irvjson', 'json', 'paircountjson']):
        # 'irvjson' and 'paircountjson' are deprecated in favor of
        # "-t 'json'" and "-m" with desired output modifier

        if output_format == 'irvjson' or 'IRV' in modifiers:
            IRV_dict = IRV_dict_from_jabmod(abifmodel)
            outstr += json.dumps(clean_dict(IRV_dict), indent=4)
        elif output_format == 'paircountjson' or 'pairwise' in modifiers:
            pairdict = pairwise_count_dict(abifmodel)
            outstr += json.dumps(pairdict, indent=4)
        elif 'STAR' in modifiers:
            STAR_dict = STAR_result_from_abifmodel(abifmodel)
            outstr += json.dumps(STAR_dict, indent=4)
        elif 'FPTP' in modifiers:
            FPTP_dict = FPTP_result_from_abifmodel(abifmodel)
            outstr += json.dumps(FPTP_dict, indent=4)
        else:
            outstr += "Please specify modifier or choose 'jabmod' output format"
    elif (output_format == 'jabmod'):
        outstr += json.dumps(abifmodel, indent=4)
    elif (output_format == 'nameq'):
        outstr += convert_jabmod_to_nameq(abifmodel)
    elif (output_format == 'svg'):
        copecount = full_copecount_from_abifmodel(abifmodel)
        outstr += copecount_diagram(copecount, outformat='svg')
    elif (output_format == 'text'):
        if 'candlist' in modifiers:
            outstr += candlist_text_from_abif(abifmodel)
        if 'winlosstie' in modifiers:
            outstr += texttable_pairwise_and_winlosstie(abifmodel)
        if 'pairwise' in modifiers:
            pairdict = pairwise_count_dict(abifmodel)
            outstr += textgrid_for_2D_dict(twodimdict=pairdict,
                                           tablelabel='   Loser ->\nv Winner',
                                           width=args.width
            )
        if 'FPTP' in modifiers:
            #fptpdict = FPTP_dict_from_jabmod(abifmodel)
            outstr += get_FPTP_report(abifmodel)
        if 'IRV' in modifiers:
            irvdict = IRV_dict_from_jabmod(abifmodel)
            outstr += get_IRV_report(irvdict)
        if 'score' in modifiers:
            outstr += score_report(abifmodel)
        if 'STAR' in modifiers:
            # check if the first voteline candidate has a rating
            if abifmodel_has_ratings(abifmodel):
                outstr += STAR_report(abifmodel)
            else:
                outstr += "No stars/scores available."
                outstr += "  Please use --add-scores to extrapolate score from ranks."
        if 'Copeland' in modifiers:
            copecount = full_copecount_from_abifmodel(abifmodel)
            outstr += Copeland_report(abifmodel['candidates'], copecount)
    elif (output_format == 'winlosstiejson'):
        pairdict = pairwise_count_dict(abifmodel)
        wltdict = winlosstie_dict_from_pairdict(abifmodel['candidates'],
                                                pairdict)
        outstr += json.dumps(wltdict, indent=4)
    else:
        outstr += f"Cannot convert to {output_format} yet."

    print(outstr)
    if args.debug:
        global DEBUGARRAY
        print(f"{DEBUGARRAY=}")


if __name__ == "__main__":
    main()
