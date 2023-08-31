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

import argparse
import json
import re
import sys

CONV_FORMATS = ('abif', 'jabmod', 'jabmoddebug', 'widj')

PRUNED_WIDJ_FIELDS = [
    "display_parameters", "display_results",
    "display_ballots", "allow_voting",
    "ballot_type", "max_rating", "min_rating",
    "count_subpage_ballots", "count_inline_ballots",
    "election_methods", "inline_ballot_type",
    "candidates", "inline_ballots"
]
ABIF_VERSION = "0.1"
DEBUGFLAG = False
LOOPLIMIT = 400


def debugprint(str):
    global DEBUGFLAG
    if DEBUGFLAG:
        print(str)
    return


def convert_widj_to_jabmod(widgetjson):
    """Converts electowidget JSON (widj) to the JSON ABIF model (jabmod)."""

    abifmodel = {}
    abifmodel["metadata"] = {}
    abifmodel["metadata"]["version"] = ABIF_VERSION
    abifmodel["candidates"] = {}

    # Fill in abifmodel["metadata"]
    for field in widgetjson:
        if field not in PRUNED_WIDJ_FIELDS:
            abifmodel["metadata"][field] = widgetjson[field]

    # Fill in abifmodel["candidates"]
    for candtoken, candidate_info in widgetjson["candidates"].items():
        abifmodel["candidates"][candtoken] = candidate_info["display_name"]

    # Fill in abifmodel["votelines"]
    abifmodel["votelines"] = _map_widj_ballots(widgetjson)
    _add_prefstr_and_rating_fields(abifmodel["votelines"])

    return abifmodel


def convert_jabmod_to_abif(abifmodel, add_ratings=True):
    """Converts electowidget JSON (widj) to a .abif string."""
    abif_string = ""
    abif_string += "#------- metadata -------\n"

    for field, value in abifmodel["metadata"].items():
        jstr = json.dumps(value)
        abif_string += f'{{{field}: {jstr}}}\n'

    abif_string += "#------ candlines ------\n"
    for candtoken in abifmodel["candidates"]:
        abif_string += f"={candtoken}:"
        abif_string += f"[{abifmodel['candidates'][candtoken]}]\n"

    abif_string += "#------- votelines ------\n"
    for (i, voteline) in enumerate(abifmodel["votelines"]):
        try:
            is_ordered = voteline["orderedlist"]
        except KeyError:
            is_ordered = False

        if is_ordered:
            abif_chunk = _rank_passthrough(voteline)
        else:
            abif_chunk = _ratings_to_ranks(voteline)
        abif_string += abif_chunk

    return abif_string


def convert_abif_to_jabmod(filename, debuginfo=False):
    abifmodel = {
        'metadata': {
            'ballotcount': 0
        },
        'candidates': {},
        'votelines': []
    }
    if debuginfo:
        abifmodel['metadata']['comments'] = []

    with open(filename) as file:
        for i, fullline in enumerate(file):
            fullline = fullline.strip()

            commentregexp = re.compile(
                r'''
                ^                       # beginning of line
                (?P<beforesep>[^\#]*)   # before the comment separator
                (?P<comsep>\#+)         # # or ## comment separator
                (?P<whitespace>\s+)     # optional whitespace
                (?P<aftersep>.*)        # after the # separator/whitespace
                $                       # end of line
                ''', re.VERBOSE
            )
            metadataregexp = re.compile(
                r'''
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
                ([\w\s\.]+)             # METADATA VALUE
                \s*                     # more whitespace 'cuz
                [\'\"]?                 # moar quotes
                \s*                     # spaces the finals frontiers
                \}                      # look!  squirrel!!!!!
                $''', re.VERBOSE
            )
            candlineregexp = re.compile(r'^\=([^:]*):\[([^\]]*)\]$')
            votelineregexp = re.compile(r'^(\d+):(.*)$')

            matchgroup = None
            # Strip the comments out first
            if (match := commentregexp.match(fullline)):
                matchgroup = 'commentregexp'
                cparts = match.groupdict()
                strpdline = cparts['beforesep']
                linecomment = cparts['comsep'] + \
                    cparts['whitespace'] + cparts['aftersep']
            else:
                strpdline = fullline
                linecomment = None
            abifmodel = _process_abif_comment_line(abifmodelin=abifmodel,
                                                   linecomment=linecomment,
                                                   linenum=i,
                                                   debuginfo=debuginfo)

            # now to deal with the substance
            if (match := candlineregexp.match(strpdline)):
                matchgroup = 'candlineregexp'
                candtoken, canddesc = match.groups()
                abifmodel = _process_abif_candline(candtoken,
                                                   canddesc,
                                                   abifmodel,
                                                   linecomment)
            elif (match := metadataregexp.match(strpdline)):
                matchgroup = 'metadataregexp'
                mkey, mvalue = match.groups()
                abifmodel = _process_abif_metadata(
                    mkey, mvalue, abifmodel, linecomment)
            elif (match := votelineregexp.match(strpdline)):
                matchgroup = 'votelineregexp'
                qty, prefstr = match.groups()
                abifmodel = _process_abif_prefline(qty,
                                                   prefstr,
                                                   abifmodel,
                                                   linecomment,
                                                   debuginfo=debuginfo)
            else:
                matchgroup = 'empty'

    return abifmodel


def _rank_passthrough(ballot):
    local_abif_str = ""
    prefstr = ""
    for pref in ballot['prefs']:
        prefstr += pref
        if 'nextdelim' in ballot['prefs'][pref]:
            delim = ballot['prefs'][pref]['nextdelim']
            prefstr += delim
    local_abif_str += f"{ballot['qty']}:{prefstr}\n"
    return local_abif_str


def _ratings_to_ranks(ballot):
    local_abif_str = ""
    final_result = {}

    sortedprefs = sorted(ballot['prefs'].items(),
                         key=lambda item: (-int(item[1]['rating']),
                                           item[0])
                         )
    final_result["tier"] = []
    current_rating = 0
    current_tier = []
    for name, data in sortedprefs:
        rating = int(data['rating'])

        if rating != current_rating:
            if current_tier:
                final_result["tier"].append(current_tier)
            current_rating = rating
            current_tier = []

        current_tier.append({name: data})
    if current_tier:
        final_result["tier"].append(current_tier)

    prefstrfromratings = ""
    for i, tierblob in enumerate(final_result['tier']):
        rank = i + 1
        lastindexi = len(final_result["tier"]) - 1
        for j, thistier in enumerate(tierblob):
            thistiercount = len(thistier)
            for k, ckey in enumerate(thistier.keys()):
                prefstrfromratings += ckey
                rating = thistier[ckey]['rating']
                prefstrfromratings += '/'
                prefstrfromratings += str(rating)
            tierblobcount = len(tierblob) - 1
            if j < tierblobcount:
                prefstrfromratings += '='
        if i < lastindexi:
            prefstrfromratings += '>'
    local_abif_str += f"{ballot['qty']}:{prefstrfromratings}\n"
    return local_abif_str


def _map_widj_ballots(widgetjson):
    """Maps widj ballots to abif voteline objects"""

    abif_votelines = []
    for ballot in widgetjson["inline_ballots"]:
        abif_ballot = {
            "qty": ballot["qty"],
            "prefs": {},
        }
        for candtoken, rating in ballot["vote"].items():
            abif_ballot["prefs"][candtoken] = rating
        abif_votelines.append(abif_ballot)

    return abif_votelines


def _process_abif_comment_line(abifmodelin={},
                               linecomment="",
                               linenum=0,
                               debuginfo=False):
    commenttuple = (linenum, linecomment)
    if debuginfo:
        abifmodelin['metadata']['comments'].append(commenttuple)

    return abifmodelin


def _process_abif_metadata(mkey, mvalue, abifmodel, linecomment=None):
    '''Simple key-value translation of metadata lines

    This function handles the metadata lines that begin with "{".
    Each metadata line should look vaguely like a line from a "JSON
    Lines" file.

    '''
    if 'metadata' in abifmodel:
        abifmodel['metadata'][mkey] = mvalue
    else:
        abifmodel['metadata'] = {mkey: mvalue}
    return abifmodel


def _process_abif_candline(candtoken, canddesc, abifmodel, linecomment=None):
    '''_process_abif_candline maps candtokens to full candidate names'''
    if not 'candidates' in abifmodel:
        abifmodel['candidates'] = {candtoken: canddesc}
    else:
        abifmodel['candidates'][candtoken] = canddesc
    return abifmodel


def _tokenize_abif_prefline(prefstr):
    '''Tokenize the voter pref portion for a prefline

    Break up the prefstr on a prefline into a series of tokens for
    further processing by _process_abif_prefline
    '''
    global LOOPLIMIT
    retval = []

    # Regular expression patterns
    pref_range_squarebrack_regexp = re.compile(
        r'''
        ^                         # start of string
        \s*                       # Optional whitespace
        (?P<candplusrate>         # <candplusrate> begin
        [\"\[]                    # beginning quotation or square bracket
        (?P<cand>[^\"\]]*)        # <cand> (within quotes or square brackets)
        [\"\]]                    # ending quotation or square bracket
        (/                        # optional slashrating begin
        (?P<rating>\d+)           # optional <rating> (number)
        \s*)?                     # optional slashrating end
        )                         # <candplusrate> end
        (?P<restofline>.*)        # the <restofline>
        $                         # end of string
        ''', re.VERBOSE)
    pref_range_baretok_regexp = re.compile(
        r'''
        ^                         # start of string
        \s*                       # Optional whitespace
        (?P<candplusrate>         # <candplusrate> begin
        (?P<cand>[A-Za-z0-9_\-]*)   # <cand> (bare token)
        (/                        # optional slashrating begin
        (?P<rating>\d+)           # optional <rating> (number)
        \s*)?                     # optional slashrating end
        )                         # <candplusrate> end
        (?P<restofline>.*)        # the <restofline>
        $                         # end of string
        ''', re.VERBOSE)

    remainingtext = prefstr
    loopsquare = bool(re.fullmatch(
        pref_range_squarebrack_regexp, remainingtext))
    loopbare = bool(re.fullmatch(pref_range_baretok_regexp, remainingtext))
    killcounter = 0
    while loopsquare or loopbare:
        if killcounter > LOOPLIMIT:
            debugprint(f'{killcounter=} (over {LOOPLIMIT=})')
            debugprint(f'{loopsquare=} {loopbare=}')
            debugprint(f'{prefstr=}')
            debugprint(f'{remainingtext=}')
            sys.exit()
        killcounter += 1
        loopsquare = bool(re.fullmatch(
            pref_range_squarebrack_regexp, remainingtext))
        loopbare = bool(re.fullmatch(pref_range_baretok_regexp, remainingtext))
        if loopsquare:
            matches_new = re.fullmatch(
                pref_range_squarebrack_regexp, remainingtext)
            loopbare = False
        elif loopbare:
            matches_new = re.fullmatch(
                pref_range_baretok_regexp, remainingtext)
            loopsquare = False
        else:
            break
        if not matches_new or matches_new.group(0) == '':
            break
        candplusrate = matches_new.group('candplusrate')
        cand = matches_new.group('cand')
        retval.append({'cand': cand})
        rating = matches_new.group('rating')
        retval.append({'rating': rating})
        restofline = matches_new.group('restofline')
        remainingtext = restofline.lstrip()
        if remainingtext.startswith((">", "=", ",")):
            delimiter = remainingtext[0]
            retval.append({'delim': delimiter})
            remainingtext = remainingtext[1:]

    return retval


def _add_prefstr_and_rating_fields(abif_votelines, add_ratings=True):
    """Adds the prefstr and rating fields to each voteline."""

    for ballot in abif_votelines:
        prefs_list = []
        for candtoken, rating in ballot["prefs"].items():
            prefs_list.append((rating, candtoken))

        # Sort the prefs_list in descending order by rating.
        prefs_list.sort(reverse=True)

        # Create the prefstr.
        prefstr = ""
        for i, (rating, candtoken) in enumerate(prefs_list):
            if prefstr != "":
                prefstr += ">" if rating != prefs_list[i - 1][0] else "="
            if add_ratings:
                prefstr += f"{candtoken}/{rating}"
            else:
                prefstr += f"{candtoken}"

        ballot["prefstr"] = prefstr

        # Extrapolate the ranking from rating-based sort
        for i, (rating, candtoken) in enumerate(prefs_list):
            ballot["prefs"][candtoken] = {
                "rank": i + 1,
                "rating": rating,
            }


def _process_abif_prefline(qty,
                           prefstr,
                           abifmodel,
                           linecomment=None,
                           debuginfo=False):
    '''process vote bundles

    preflines are the heart of ABIF.  Each line describes batch of
    ballots in the following form:

    <qty>: <cand1>(/<rating1>) ">"/"="/"," <cand2>(/<rating2>) [...]

    '''
    abifmodel['metadata']['ballotcount'] += int(qty)
    linepair = {}
    linepair['qty'] = int(qty)
    linepair['prefs'] = {}
    linepair['comment'] = linecomment
    if debuginfo:
        linepair['prefstr'] = prefstr.rstrip()

    abifmodel['votelines'].append(linepair)
    if debuginfo:
        abifmodel['votelines'][-1]['tokens'] = []
    prefs = {}
    candrank = 1
    votelineorder = 1
    toprating = 0
    ratingarray = {}
    orderedlist = None
    prefline_toks = _tokenize_abif_prefline(prefstr)
    candnum = 0
    for tok in prefline_toks:
        if debuginfo:
            abifmodel['votelines'][-1]['tokens'].append(tok)
        if 'cand' in tok:
            candnum += 1
            thiscand = tok['cand']
            prefs[thiscand] = {}
            if not thiscand in abifmodel['candidates']:
                abifmodel['candidates'][thiscand] = thiscand
        if 'rating' in tok:
            thisrating = tok['rating']
            # debugprint(f'{thisrating=}')
            prefs[thiscand]['rating'] = thisrating
            if len(ratingarray) == 0:
                ratingarray = {candrank: thisrating}
            else:
                ratingarray[candrank] = thisrating
        if 'delim' in tok:
            thisdelim = tok['delim']
            prefs[thiscand]['nextdelim'] = thisdelim
            if thisdelim == '>':
                prefs[thiscand]['rank'] = candrank
                candrank += 1
                orderedlist = True
            elif thisdelim == '=':
                prefs[thiscand]['rank'] = candrank
                orderedlist = True
            elif thisdelim == ",":
                prefs[thiscand]['rank'] = candrank
                orderedlist = False

    prefs[thiscand]['rank'] = candrank
    debugprint(f"{prefs=}")
    debugprint(f"{abifmodel['candidates']=}")
    abifmodel['votelines'][-1]['prefs'] = prefs
    if orderedlist is None:
        abifmodel['votelines'][-1]['orderedlist'] = False
    else:
        abifmodel['votelines'][-1]['orderedlist'] = orderedlist
    return abifmodel


def main():
    """Convert between .abif-adjacent formats."""
    global DEBUGFLAG

    parser = argparse.ArgumentParser(
        description='Convert between .abif and JSON formats')
    parser.add_argument('input_file', help='Input file to convert')
    parser.add_argument('-t', '--to', choices=CONV_FORMATS,
                        required=True, help='Output format')
    parser.add_argument('-f', '--fromfmt', choices=CONV_FORMATS,
                        help='Input format (overrides file extension)')
    parser.add_argument('-d', '--debug',
                        help='Output debugging info',
                        action="store_true")

    args = parser.parse_args()

    DEBUGFLAG = args.debug
    # CONV_FORMATS = ('abif', 'jabmod', 'jabmoddebug', 'widj')

    # Determine input format based on file extension or override from
    # the "-f/--fromfmt" option
    if args.fromfmt:
        input_format = args.fromfmt
    else:
        _, file_extension = args.input_file.rsplit('.', 1)
        input_format = file_extension
    if input_format not in CONV_FORMATS:
        print(f"Error: Unsupported input format '{input_format}'")
        return

    # the "-t/--to" option
    output_format = args.to
    if output_format not in CONV_FORMATS:
        print(f"Error: Unsupported output format '{output_format}'")
        return

    if (input_format == 'abif' and output_format == 'jabmod'):
        # Convert .abif to JSON-based model (.jabmod)
        abifmodel = convert_abif_to_jabmod(args.input_file)
        try:
            outstr = json.dumps(abifmodel, indent=4)
        except BaseException:
            outstr = "NOT JSON SERIALIZABLE"
            outstr += pprint.pformat(abifmodel)
    elif (input_format == 'abif' and output_format == 'jabmoddebug'):
        # Convert .abif to JSON-based model (.jabmod) with debug info
        abifmodel = convert_abif_to_jabmod(args.input_file,
                                           debuginfo=True)
        try:
            outstr = json.dumps(abifmodel, indent=4)
        except BaseException:
            outstr = "NOT JSON SERIALIZABLE"
            outstr += pprint.pformat(abifmodel)
    elif (input_format == 'jabmod' and output_format == 'abif'):
        # Convert from JSON ABIF model (.jabmod) to .abif
        add_ratings = True

        if args.input_file == "-":
            abifmodel = json.load(sys.stdin)
        else:
            with open(args.input_file) as f:
                abifmodel = json.load(f)
        outstr = convert_jabmod_to_abif(abifmodel,
                                        add_ratings)
    elif (input_format == 'widj' and output_format == 'abif'):
        # Convert from electowidget (.widj) to .abif
        add_ratings = True
        with open(args.input_file) as f:
            widgetjson = json.load(f)
            abifmodel = convert_widj_to_jabmod(widgetjson)
        outstr = convert_jabmod_to_abif(abifmodel,
                                        add_ratings)
    elif (input_format == 'widj' and output_format == 'jabmod'):
        # Convert from electowidget (.widj) to .abif
        with open(args.input_file) as f:
            widgetjson = json.load(f)
            abifmodel = convert_widj_to_jabmod(widgetjson)
        outstr = json.dumps(abifmodel, indent=2)
    else:
        outstr = \
            f"Cannot convert from {input_format} to {output_format} yet."

    print(outstr)


if __name__ == "__main__":
    main()
