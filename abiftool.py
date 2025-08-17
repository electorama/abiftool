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
    from abiflib.sfjson_fmt import convert_sfjson_to_jabmod, list_contests
except ModuleNotFoundError as e:
    print(f"ModuleNotFoundError: {e.name}\n")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("Please install the following modules listed in abiftool/requirements.txt:\n")
    with open("requirements.txt", "r") as req_file:
        print(req_file.read())
    print("You may also run 'pip install -r requirements.txt' to install all modules.")
    sys.exit()

import argparse
from datetime import datetime, timezone
import json
import re
import urllib.parse


INPUT_FORMATS = [
    {'abif': 'ABIF format'},
    {'debtally': 'Election output format used by the Debian Project'},
    {'jabmod': 'Internal JSON ABIF model (Json ABIF MODel)'},
    {'nameq': 'Brian Olson\'s format which URL-encoded version of the raw ballots'},
    {'preflib': 'Files downloaded from preflib.org'},
    {'sfjson': 'San Francisco JSON CVR format'},
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
    {'approval': 'Show approval voting results (strategic simulation)'},
    {'candlist': 'List all candidates at the beginning of output'},
    {'Copeland': 'Show pairwise table and Copeland winner (default)'},
    {'consolidate': 'Consolidate votelines if possible'},
    {'FPTP': 'Show FPTP results'},
    {'IRV': 'Show IRV/RCV results'},
    {'IRVextra': 'Extra data for deep analysis of IRV elections'},
    {'jcomments': 'Put comments in jabmod output if available'},
    {'margins': 'Use margin-based victory measurements in pairwise summaries'},
    {'notices': 'Include notices in output (when combined with voting methods)'},
    {'pairlist': 'List all pairwise matchups with victory data'},
    {'pairwise': 'Show pairwise table (possibly without winlosstie info)'},
    {'score': 'Provide score results'},
    {'STAR': 'Provide STAR results'},
    {'svg': 'Add SVG to the output if avaiable'},
    {'winning-votes': 'Use winning-votes victory measurements in pairwise summaries'},
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

    parser.add_argument('--profile-output', help='Write cProfile output to this file')

    validinfmts = get_keys_from_dict_list(INPUT_FORMATS)
    validoutfmts = get_keys_from_dict_list(OUTPUT_FORMATS)
    validmod = get_keys_from_dict_list(MODIFIERS)
    parser.add_argument('--container',
                        help='Container file (e.g., zip, tar.gz)')
    parser.add_argument('input_file', nargs='*',
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
                        help="width when rendering output with texttable lib")
    parser.add_argument('--cleanws', action="store_true",
                        help='Clean whitespace in ABIF file')
    parser.add_argument('--add-scores', action="store_true",
                        help='Add scores to votelines when only rankings are provided')
    parser.add_argument('--contestid', type=int,
                        help='The ID of the contest to process from a container')
    parser.add_argument('-l', '--list-contests', action='store_true',
                        help='List contests in a container and exit')

    args = parser.parse_args()
    abiflib_test_log(f"cmd: {' '.join(sys.argv)}")
    pr = None
    profile_filename = None
    if os.environ.get("ABIFTOOL_DEBUG") or args.profile_output:
        import cProfile
        if args.profile_output:
            profile_filename = args.profile_output
        else:
            if not profile_filename:
                cprof_dir = 'timing'
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                if not os.path.exists(cprof_dir):
                    os.makedirs(cprof_dir)
                profile_filename = os.path.join(cprof_dir, f'c{timestamp}.cprof')
        pr = cProfile.Profile()
        pr.enable()

    if not args.input_file and not args.list_contests and not args.container:
        parser.error("Missing input file.  Please specify an input file or "
                     "container file.")
    elif args.list_contests and args.container:
        list_contests(args.container)
        sys.exit()
    elif args.list_contests and not args.container:
        print("Error: The --list-contests flag requires a --container file.")
        sys.exit()

    # Determine input format based on file extension or override from
    # the "-f/--fromfmt" option
    if args.fromfmt:
        input_format = args.fromfmt
    elif args.input_file and args.input_file[0] == '-':
        parser.error("The -f parameter is required with '-'")
    elif args.input_file and args.input_file[0].find('.') >= 0:
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
    elif type(args.input_file) is list:
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
    if 'list-contests' in modifiers:
        if args.container:
            list_contests(args.container)
            sys.exit()
        else:
            print("Error: The --list-contests modifier requires a container specified with --container.")
            sys.exit()

    if args.container:
        if input_format == 'sfjson':
            abifmodel = convert_sfjson_to_jabmod(args.container, contestid=args.contestid)
        else:
            print(f"Error: The --container flag is not supported for the '{input_format}' format yet.")
            sys.exit()
    elif (input_format == 'abif'):
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
        abifmodel = consolidate_jabmod_voteline_objects(abifmodel)

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
                                                   snippet=True,
                                                   validate=True,
                                                   modlimit=ABIFMODEL_LIMIT,
                                                   svg_text=svg_text,
                                                   modifiers=modifiers)
    elif (output_format in ['irvjson', 'json', 'paircountjson']):
        # 'irvjson' and 'paircountjson' are deprecated in favor of
        # "-t 'json'" and "-m" with desired output modifier

        if output_format == 'irvjson' or 'IRV' in modifiers:
            include_irv_extra = 'IRVextra' in modifiers
            IRV_dict = IRV_dict_from_jabmod(
                abifmodel, include_irv_extra=include_irv_extra)
            outstr += json.dumps(clean_dict(IRV_dict), indent=4)
        elif output_format == 'paircountjson' or 'pairwise' in modifiers:
            if 'notices' in modifiers:
                # Use new function that includes notices
                from abiflib.pairwise_tally import pairwise_result_from_abifmodel
                pairwise_result = pairwise_result_from_abifmodel(abifmodel)
                outstr += json.dumps(pairwise_result, indent=4)
            else:
                # Use original function for backward compatibility
                pairdict = pairwise_count_dict(abifmodel)
                outstr += json.dumps(pairdict, indent=4)
        elif 'STAR' in modifiers:
            STAR_dict = STAR_result_from_abifmodel(abifmodel)
            outstr += json.dumps(STAR_dict, indent=4)
        elif 'FPTP' in modifiers:
            FPTP_dict = FPTP_result_from_abifmodel(abifmodel)
            outstr += json.dumps(FPTP_dict, indent=4)
        elif 'approval' in modifiers:
            approval_dict = approval_result_from_abifmodel(abifmodel)
            outstr += json.dumps(approval_dict, indent=4)
        elif 'score' in modifiers:
            score_dict = enhanced_score_result_from_abifmodel(abifmodel)
            outstr += json.dumps(score_dict, indent=4)
        elif 'pairlist' in modifiers:
            # Determine victory method from modifiers
            victory_method = 'winning-votes'  # default
            if 'margins' in modifiers:
                victory_method = 'margins'

            pairdict = pairwise_count_dict(abifmodel)
            victory_data = calculate_pairwise_victory_sizes(pairdict, victory_method)

            # Convert to JSON-friendly format
            pairlist_dict = {
                'victory_method': victory_method,
                'pairwise_matchups': victory_data
            }
            outstr += json.dumps(pairlist_dict, indent=4)
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
        # Add pairwise summary at the top if pairwise methods are requested
        if 'winlosstie' in modifiers or 'pairwise' in modifiers or 'Copeland' in modifiers:
            # Determine victory method from modifiers
            victory_method = 'winning-votes'  # default
            if 'margins' in modifiers:
                victory_method = 'margins'

            # Generate and display pairwise summary
            pairdict = pairwise_count_dict(abifmodel)
            wltdict = winlosstie_dict_from_pairdict(abifmodel['candidates'], pairdict)
            victory_data = calculate_pairwise_victory_sizes(pairdict, victory_method)

            outstr += generate_pairwise_summary_text(abifmodel, wltdict, victory_data, victory_method)
            outstr += "\n"

        if 'candlist' in modifiers:
            outstr += candlist_text_from_abif(abifmodel)
        if 'winlosstie' in modifiers:
            outstr += texttable_pairwise_and_winlosstie(abifmodel)
        if 'pairwise' in modifiers:
            if 'notices' in modifiers:
                # Use new function that includes notices
                from abiflib.pairwise_tally import get_pairwise_report
                outstr += get_pairwise_report(abifmodel)
            else:
                # Use original function for backward compatibility
                pairdict = pairwise_count_dict(abifmodel)
                outstr += textgrid_for_2D_dict(twodimdict=pairdict,
                                               tablelabel='   Loser ->\nv Winner',
                                               width=args.width)
        if 'FPTP' in modifiers:
            # fptpdict = FPTP_dict_from_jabmod(abifmodel)
            outstr += get_FPTP_report(abifmodel)
        if 'approval' in modifiers:
            outstr += get_approval_report(abifmodel)
        if 'IRV' in modifiers:
            include_irv_extra = 'IRVextra' in modifiers
            irvdict = IRV_dict_from_jabmod(
                abifmodel, include_irv_extra=include_irv_extra)
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
        wltdict = winlosstie_dict_from_pairdict(abifmodel['candidates'], pairdict)
        outstr += json.dumps(wltdict, indent=4)
    else:
        outstr += f"Cannot convert to {output_format} yet."

    if pr is not None and profile_filename:
        pr.disable()
        pr.dump_stats(profile_filename)

    print(outstr)
    if args.debug:
        global DEBUGARRAY
        print(f"{DEBUGARRAY=}")


if __name__ == "__main__":
    main()
