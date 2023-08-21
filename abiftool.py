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

import json
import re
import sys
import argparse
import json

CONV_FORMATS = ('abif', 'jabmod', 'widj')

PRUNED_METADATA_FIELDS = ["display_parameters", "display_results",
                          "display_ballots", "allow_voting",
                          "ballot_type", "max_rating", "min_rating",
                          "count_subpage_ballots", "count_inline_ballots",
                          "election_methods", "inline_ballot_type",
                          "candidates", "inline_ballots"]
ABIF_VERSION = "0.1"


def convert_widgetjson_to_abifmodel(widgetjson):
    """Converts electowidget JSON to the ABIF JSON model."""

    abifmodel = {}
    abifmodel["metadata"] = {}
    abifmodel["metadata"]["version"] = ABIF_VERSION
    abifmodel["candidates"] = {}

    # Fill in abifmodel["metadata"]
    for field in widgetjson:
        if field not in PRUNED_METADATA_FIELDS:
            abifmodel["metadata"][field] = widgetjson[field]

    # Fill in abifmodel["candidates"]
    for candtoken, candidate_info in widgetjson["candidates"].items():
        abifmodel["candidates"][candtoken] = candidate_info["display_name"]

    # Fill in abifmodel["votelines"]
    abifmodel["votelines"] = _convert_widget_ballots(widgetjson)
    _add_prefstr_and_rating_fields(abifmodel["votelines"])

    return abifmodel


def convert_abifmodel_to_abifstr(abifmodel, add_ratings=True):
    """Converts electowidget JSON to a .abif string."""
    abif_string = ""

    for field, value in abifmodel["metadata"].items():
        abif_string += f'{{{field}: {json.dumps(value)}}}\n'

    abif_string += "#-----------------------\n"

    # Convert candidate declarations to abif.
    for candtoken in abifmodel["candidates"]:
        abif_string += f"={candtoken}:"
        abif_string += f"[{abifmodel['candidates'][candtoken]}]\n"

    abif_string += "#-----------------------\n"

    for ballot in abifmodel["votelines"]:
        abif_string += f"{ballot['qty']}:{ballot['prefstr']}\n"

    return abif_string


def _convert_widget_ballots(widgetjson):
    """Converts the electowidget ballots to abif voteline objects"""

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


def process_metadata(mkey, mvalue, abifmodel):
    '''Simple key-value translation of metadata lines

    This function handles the metadata lines that begin with "{".
    Each metadata line should look vaguely like a line from a "JSON
    Lines" file.

    '''
    if not 'metadata' in abifmodel:
        abifmodel['metadata'] = {mkey: mvalue}
    else:
        abifmodel['metadata'][mkey] = mvalue
    return abifmodel


def process_candline(candtoken, canddesc, abifmodel):
    '''process_candline maps candtokens to full candidate names'''
    if not 'candidates' in abifmodel:
        abifmodel['candidates'] = {candtoken: canddesc}
    else:
        abifmodel['candidates'][candtoken] = canddesc
    return abifmodel


def tokenize_prefs(prefstr):
    '''Tokenize the voter pref portion for a prefline

    Break up the prefstr on a prefline into a series of tokens for
    further processing by process_prefline
    '''
    # The following regex matches one of two clusters:
    #
    # 1. Match the cand token (\w+), and then optionally match the
    #    rating ("/" then a number)
    # 2. Match the seperator ([>=,]
    regex = r"(\w+)(?:/(\d+))?|([>=,])"
    matches = re.finditer(regex, prefstr)

    retval = []
    candidate = None
    rating = None

    for match in matches:
        # If the this is a candidate/rating pair
        if match.group(1) is not None:
            candidate = match.group(1)
            rating = match.group(2)
            candpref = {}
            if rating is not None:
                candpref['type'] = 'c'
                candpref['cand'] = candidate
                candpref['slash'] = '/'
                candpref['rat'] = rating
            else:
                candpref['cand'] = candidate
            retval.append(candpref)
        # ..else this must be a delimiter
        else:
            delim = match.group(3)
            if delim is not None:
                retval.append({'delim': delim,
                               'type': 'd'})

    return retval


def process_prefline(qty, prefstr, abifmodel, debuginfo=False):
    '''process vote bundles

    preflines are the heart of ABIF.  Each line describes batch of
    ballots in the following form:

    <qty>: <cand1>(/<rating1>) ">"/"="/"," <cand2>(/<rating2>) [...]

    '''
    abifmodel['metadata']['ballotcount'] += int(qty)
    linepair = {}
    linepair['qty'] = int(qty)
    linepair['prefs'] = {}
    linepair['prefstr'] = prefstr

    abifmodel['votelines'].append(linepair)
    if debuginfo:
        abifmodel['votelines'][-1]['tokens'] = []
    prefs = {}
    candrank = 1
    votelineorder = 1
    toprating = 0
    ratingarray = {}
    orderedlist = None
    for tok in tokenize_prefs(prefstr):
        if debuginfo:
            abifmodel['votelines'][-1]['tokens'].append(tok)
        if 'cand' in tok:
            thiscand = tok['cand']
            prefs[thiscand] = {}
        if 'rat' in tok:
            thisrating = tok['rat']
            prefs[thiscand]['rating'] = thisrating
            if len(ratingarray) == 0:
                ratingarray = {candrank: thisrating}
            else:
                ratingarray[candrank] = thisrating
        if 'delim' in tok:
            prefs[thiscand]['rank'] = candrank
            thisdelim = tok['delim']
            prefs[thiscand]['nextdelim'] = thisdelim
            if thisdelim == '>':
                candrank += 1
                orderedlist = True
            elif thisdelim == '=':
                orderedlist = True
            elif thisdelim == ",":
                orderedlist = False
    prefs[thiscand]['rank'] = candrank
    abifmodel['votelines'][-1]['prefs'] = prefs
    if orderedlist is not None:
        abifmodel['votelines'][-1]['orderedlist'] = orderedlist
    return abifmodel


def convert_abif_file_to_json(filename):
    abifmodel = {
        'metadata': {
            'ballotcount': 0
        },
        'candidates': {},
        'votelines': []
    }

    with open(filename) as file:
        for line in file:
            line = line.strip()
            if not line:
                break

            candlineregexp = re.compile(r'^\=([^:]*):\[([^\]]*)\]$')
            votelineregexp = re.compile(r'^(\d+):(.*)$')

            metadataregexp = re.compile(
                r'^\{\s*[\'\"]?([\w\s]+)\s*[\'\"]?\s*:\s*[\'\"]?([\w\s\.]+)\s*[\'\"]?\s*\}$')

            if (match := candlineregexp.match(line)):
                candtoken, canddesc = match.groups()
                abifmodel = process_candline(candtoken,
                                             canddesc,
                                             abifmodel)
            elif (match := metadataregexp.match(line)):
                mkey, mvalue = match.groups()
                abifmodel = process_metadata(mkey, mvalue, abifmodel)
            elif (match := votelineregexp.match(line)):
                qty, prefstr = match.groups()
                abifmodel = process_prefline(qty,
                                             prefstr,
                                             abifmodel)
            else:
                continue
    return abifmodel


def main():
    """Convert .abif files to JSON ABIF model."""

    parser = argparse.ArgumentParser(
        description='Convert between .abif and JSON formats')
    parser.add_argument('input_file', help='Input file to convert')
    parser.add_argument('-t', '--to', choices=CONV_FORMATS,
                        required=True, help='Output format')
    parser.add_argument('-f', '--fromfmt', choices=CONV_FORMATS,
                        help='Input format (overrides file extension)')

    args = parser.parse_args()

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
        print(f"Error: Unsupported input format '{output_format}'")
        return

    # CONV_FORMATS = ('abif', 'jabmod', 'widj')
    # old formats: ('abif', 'jsonabifmodel', 'electowidgetjson')
    if (input_format == 'abif' and output_format == 'jabmod'):
        # Convert .abif to JSON-based model (.jabmod)
        abifmodel = convert_abif_file_to_json(args.input_file)
        try:
            outstr = json.dumps(abifmodel, indent=4)
        except:
            outstr = "NOT JSON SERIALIZABLE"
            outstr += pprint.pformat(abifmodel)
    elif (input_format == 'jabmod' and output_format == 'abif'):
        # Convert from JSON ABIF model (.jabmod) to .abif
        add_ratings = True

        with open(args.input_file) as f:
            abifmodel = json.load(f)
        outstr = convert_abifmodel_to_abifstr(abifmodel,
                                              add_ratings)
    elif (input_format == 'widj' and output_format == 'abif'):
        # Convert from electowidget (.widj) to .abif
        add_ratings = True
        with open(args.input_file) as f:
            widgetjson = json.load(f)
            abifmodel = convert_widgetjson_to_abifmodel(widgetjson)
        outstr = convert_abifmodel_to_abifstr(abifmodel,
                                              add_ratings)
    elif (input_format == 'widj' and output_format == 'jabmod'):
        # Convert from electowidget (.widj) to .abif
        with open(args.input_file) as f:
            widgetjson = json.load(f)
            abifmodel = convert_widgetjson_to_abifmodel(widgetjson)
        outstr = json.dumps(abifmodel, indent=2)
    else:
        outstr = \
            f"Cannot convert from {input_format} to {output_format} yet."

    print(outstr)


if __name__ == "__main__":
    main()
