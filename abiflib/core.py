#!/usr/bin/env python3
# abiflib/core.py - core ABIF<=>jabmod conversion functions
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
from pprint import pprint, pformat
import copy
import csv
import inspect
import io
import json
import os
import re
import sys
import urllib.parse

ABIF_VERSION = "0.1"
ABIF_MODEL_LIMIT = 2500


class ABIFVotelineException(Exception):
    """Raised when votelines are missing from ABIF."""

    def __init__(self, value, message="ABIFVotelineException glares at you"):
        global DEBUGARRAY
        self.value = value
        self.message = message
        self.debugarray = DEBUGARRAY
        super().__init__(self.message)


def corefunc_init(tag="unmarked"):
    '''Initialization for all abiflib/core.py functions

    This function was added as a place to aggregate logging
    functionality for all functions in abiflib/core.py

    '''
    # abiflib_test_log(f"{tag}: {abiflib_callstackstr(start=2, end=6)}")
    return {'tag': tag}


########################
# Functions for parsing/reading abif into jabmod....
#

def convert_abif_to_jabmod(inputstr,
                           cleanws=False,
                           add_ratings=False,
                           extradata=None,
                           storecomments=False):
    """Converts an .abif string to JSON/jabmod

    'jabmod' stands for 'JSON ABIF Model', and is the internal abiflib
    data structure which is used throughout abiflib.
    """
    initval = corefunc_init(tag="f01")
    global COMMENT_REGEX, METADATA_REGEX
    global CANDLINE_REGEX, VOTELINE_REGEX
    commentregexp = re.compile(COMMENT_REGEX, re.VERBOSE)
    metadataregexp = re.compile(METADATA_REGEX, re.VERBOSE)
    candlineregexp = re.compile(CANDLINE_REGEX, re.VERBOSE)
    votelineregexp = re.compile(VOTELINE_REGEX, re.VERBOSE)

    newmodel = _get_emptyish_abifmodel()

    if len(inputstr) == 0:
        msg = f'Empty ABIF string..'
        raise ABIFVotelineException(value=inputstr, message=msg)
    # 'v' is the voteline number
    v = 0
    for i, fullline in enumerate(inputstr.splitlines()):
        matchgroup = None
        linecomment = None
        cparts = None
        # if "--cleanws" flag is given, strip leading whitespace
        if cleanws:
            fullline = re.sub(r"^\s+", "", fullline)
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
        abifmodel = _process_abif_comment_line(abifmodel=newmodel,
                                               linecomment=linecomment,
                                               linenum=i,
                                               storecomments=storecomments)

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
                                               linecomment)
            v += 1
        else:
            matchgroup = 'empty'

    if len(abifmodel['votelines']) == 0:
        if len(inputstr) > 20:
            msg = f'No votelines in "{inputstr[:20]}...". '
        else:
            msg = f'No votelines in "{inputstr}". '
        msg += "Votelines (like '20:A>B>C') are required in valid ABIF files."
        raise ABIFVotelineException(value=inputstr, message=msg)

    # Add in Borda-ish score if ratings are not provided
    firstprefs = abifmodel['votelines'][0]['prefs']
    firstk, firstv = list(firstprefs.items())[0]
    if not firstv.get('rating') and add_ratings:
        abifmodel = _add_ratings_to_jabmod_votelines(abifmodel)

    slist = sorted(abifmodel["votelines"], key=lambda x: x['qty'],
                   reverse=True)
    abifmodel["votelines"] = slist
    if extradata:
        abiflib_test_log(f"Ignoring {extradata=}")

    return abifmodel


def _process_abif_comment_line(abifmodel=None,
                               linecomment="",
                               linenum=0,
                               storecomments=False):
    '''Store abif comments in jabmod metadata'''
    initval = corefunc_init(tag="f02")
    if not abifmodel:
        abifmodel = _get_emptyish_abifmodel()
    commenttuple = (linenum, linecomment)
    if linecomment and storecomments:
        if not 'comments' in abifmodel['metadata']:
            abifmodel['metadata']['comments'] = []
        abifmodel['metadata']['comments'].append(commenttuple)
    return abifmodel


def _process_abif_metadata(mkey, mvalue, abifmodel, linecomment=None):
    '''Simple key-value translation of metadata lines

    This function handles the metadata lines that begin with "{".
    Each metadata line should look vaguely like a line from a "JSON
    Lines" file.

    '''
    initval = corefunc_init(tag="f03")
    # Rename ballotcount that is passed in, since this tool is going
    # to recount the ballots.
    if mkey == 'ballotcount':
        mkey = 'ballotcount_abif_metadata'
    if 'metadata' in abifmodel:
        abifmodel['metadata'][mkey] = mvalue
    else:
        abifmodel['metadata'] = {mkey: mvalue}
    return abifmodel


def _process_abif_candline(candtoken, canddesc, abifmodel, linecomment=None):
    '''_process_abif_candline maps candtokens to full candidate names'''
    initval = corefunc_init(tag="f04")
    if not 'candidates' in abifmodel:
        abifmodel['candidates'] = {candtoken: canddesc}
    else:
        abifmodel['candidates'][candtoken] = canddesc
    return abifmodel


def _get_emptyish_abifmodel():
    '''Provide initialized jabmod/abifmodel'''
    initval = corefunc_init(tag="f05")
    retval = {}
    retval['candidates'] = {}
    retval['metadata'] = {}
    retval['metadata']['ballotcount'] = 0
    retval['votelines'] = []
    return retval


def _add_ranks_to_prefjab_by_rating(inprefjab):
    '''Use candidate ratings to provide rankings'''
    initval = corefunc_init(tag="f06")
    retval = inprefjab.copy()

    # Sort cands by rating (descending order)
    cands = sorted(retval,
                   key=lambda x: int(retval[x].get("rating", 0)),
                   reverse=True)
    if not inprefjab.get(cands[0]).get('rating'):
        msg = f"Invalid call to _add_ranks_to_prefjab_by_rating"
        raise ABIFVotelineException(value=inprefjab, message=msg)

    # Assign ranks
    prevrating = None
    thisrank = 0
    for i, c in enumerate(cands):
        if i == 0:
            thisrank = 1
        elif int(retval[c].get("rating", 0)) < prevrating:
            thisrank += 1
        retval[c]["rank"] = thisrank
        prevrating = int(retval[c].get("rating", 0))
    return retval


def _add_ratings_to_jabmod_votelines(inmod):
    ''' Calculate Borda-like ratings in lieu of explicit ratings '''
    initval = corefunc_init(tag="f07")
    numcands = len(inmod['candidates'])
    outmod = copy.deepcopy(inmod)
    for vl in outmod['votelines']:
        for k, v in vl['prefs'].items():
            v['rating'] = numcands - v['rank']
    return outmod


def _parse_prefstr_to_dict(prefstr, qty=0,
                           abifmodel=None, linecomment=None):
    '''Convert prefstr portion of .abif voteline to jabvoteline
    structure.'''
    initval = corefunc_init(tag="f08")
    prefs = {}
    rank = 1

    if not abifmodel:
        abifmodel = _get_emptyish_abifmodel()

    # Split the string by commas or ranking symbols
    candidates = re.split(r",|>|=", prefstr)
    delimeters = [char for char in prefstr if char in ">,="]
    if delimeters and delimeters[0] in '>=':
        rank_or_rate = "rank"
    elif delimeters and delimeters[0] == ",":
        rank_or_rate = "rate"
    else:
        rank_or_rate = "rankone"
    candkeys = []
    for (i, candpref) in enumerate(candidates):
        candpref = candpref.strip()
        if not candpref:
            continue

        parts = candpref.split("/")
        candidate = parts[0].strip("[]\"")
        candkeys.append(candidate)
        if candidate not in abifmodel['candidates']:
            abifmodel['candidates'][candidate] = candidate

        prefs[candidate] = {}
        if i < len(candidates) - 1:
            prefs[candidate]["nextdelim"] = delimeters[i]
        if rank_or_rate == "rankone":
            rank = 1
            prefs[candidate]["rank"] = rank
        elif rank_or_rate == "rank":
            prefs[candidate]["rank"] = rank
            if i < len(candidates) - 1 and delimeters[i] == ">":
                rank += 1

        if len(parts) > 1:
            prefs[candidate]["rating"] = parts[1]
    firstcandprefs = prefs.get(candkeys[0])
    if firstcandprefs.get('rating') and not firstcandprefs.get('rank'):
        prefs = _add_ranks_to_prefjab_by_rating(inprefjab=prefs)
    return {"prefs": prefs}


def _process_abif_prefline(qty, prefstr,
                           abifmodel=None, linecomment=None):
    '''Add prefline with qty to the provided abifmodel/jabmod'''
    voteridregexp = re.compile(VOTERID_REGEX, re.VERBOSE)
    voterid = None
    if linecomment is not None:
        if (match := voteridregexp.match(linecomment)):
            cparts = match.groupdict()
            voterid = cparts['voterid']

    initval = corefunc_init(tag="f09")
    if not abifmodel:
        abifmodel = _get_emptyish_abifmodel()

    try:
        abifmodel['metadata']['ballotcount'] += int(qty)
    except:
        print(f"{abifmodel['metadata']['ballotcount']=} ")
        raise
    linepair = {}
    linepair['qty'] = int(qty)
    linepair['prefs'] = \
        _parse_prefstr_to_dict(prefstr,
                               qty=qty,
                               abifmodel=abifmodel,
                               linecomment=linecomment)['prefs']
    linepair['comment'] = linecomment
    linepair['prefstr'] = prefstr.rstrip()
    if voterid is not None:
        linepair['voterid'] = voterid
    abifmodel['votelines'].append(linepair)
    return abifmodel

########################
# Functions for converting jabmod into abif....
#


def convert_jabmod_to_abif(abifmodel, add_ratings=False):
    """Converts 'jabmod' to an .abif string.

    'jabmod' stands for 'JSON ABIF Model', and is the internal abiflib
    data structure which is used throughout abiflib.
    """
    initval = corefunc_init(tag="f10")
    abif_string = ""
    abif_string += "#------- metadata -------\n"

    for field, value in abifmodel["metadata"].items():
        jstr = json.dumps(value)
        abif_string += f'{{{field}: {jstr}}}\n'

    abif_string += "#------ candlines ------\n"
    for candtoken in abifmodel["candidates"]:
        candqtoken = _abif_token_quote(candtoken)
        abif_string += f"={candqtoken}:"
        abif_string += f"[{abifmodel['candidates'][candtoken]}]\n"

    abif_string += "#------- votelines ------\n"
    for (i, jabvoteline) in enumerate(abifmodel["votelines"]):
        try:
            is_ordered = jabvoteline["orderedlist"]
        except KeyError:
            is_ordered = False

        abif_chunk = _get_votelinestr_from_jabvoteline(jabvoteline)
        abif_string += abif_chunk

    return abif_string


def _abif_token_quote(candtoken):
    '''Add square brackets to a candidate token if necessary'''
    initval = corefunc_init(tag="f11")
    quotedcand = urllib.parse.quote_plus(candtoken)
    if quotedcand == candtoken:
        candtoken = candtoken
    else:
        candtoken = f"[{candtoken}]"
    return candtoken


def ranklist_from_jabmod_voteline(voteline):
    """Construct list of candtoks in order of ranking"""
    initval = corefunc_init(tag="f12")
    orderedcands = []
    toklist = list(voteline['prefs'].keys())
    firstcand = toklist[0]
    firstrank = voteline['prefs'][firstcand].get('rank', None)
    firstrating = voteline['prefs'][firstcand].get('rating', None)
    if firstrank:
        orderedcands = toklist.copy()
        orderedcands.sort(
            key=lambda x: voteline['prefs'][x]['rank'], reverse=False)
    elif firstrating:
        orderedcands = toklist.copy()
        orderedcands.sort(
            key=lambda x: voteline['prefs'][x]['rating'], reverse=True)
    else:
        orderedcands = toklist
    return orderedcands


def _prefstr_from_ranked_line(sortedprefs):
    '''provide .abif string from prefs in jabmod form'''
    initval = corefunc_init(tag="f13")
    prefstrfromranks = ""
    rank = 1

    for name, data in sortedprefs:
        prefstrfromranks += _abif_token_quote(name)
        if 'rating' in data and data['rating'] is not None:
            prefstrfromranks += f"/{data['rating']}"
        if 'nextdelim' in data:
            if data['nextdelim'] == '>':
                rank += 1
            prefstrfromranks += data['nextdelim']
    return prefstrfromranks


def _prefstr_from_ratings(sortedprefs):
    '''provide .abif string from ratings in jabmod form'''
    initval = corefunc_init(tag="f14")
    tiered_cands = []
    current_rating = 0
    current_tier = []
    for name, data in sortedprefs:
        try:
            rating = int(data['rating'])
        except TypeError:
            rating = None

        if rating != current_rating:
            if current_tier:
                tiered_cands.append(current_tier)
            current_rating = rating
            current_tier = []
        current_tier.append({name: data})
    if current_tier:
        tiered_cands.append(current_tier)

    prefstrfromratings = ""
    for i, tierblob in enumerate(tiered_cands):
        rank = i + 1
        lastindexi = len(tiered_cands) - 1
        for j, thistier in enumerate(tierblob):
            thistiercount = len(thistier)
            for k, ckey in enumerate(thistier.keys()):
                candqtoken = _abif_token_quote(ckey)
                prefstrfromratings += candqtoken
                rating = thistier[ckey]['rating']
                prefstrfromratings += f'/{rating}'
            tierblobcount = len(tierblob) - 1
            if j < tierblobcount:
                prefstrfromratings += '='
        if i < lastindexi:
            prefstrfromratings += '>'
    return prefstrfromratings


def _get_votelinestr_from_jabvoteline(jabvoteline):
    '''Convert voteline data structure to abif string for voteline

    "jabvoteline" is the jabmod/JSON structure for a voteline
    "votelinestr" is the .abif string representation of a voteline
    '''
    initval = corefunc_init(tag="f15")
    local_abif_str = ""

    try:
        prefitems = sorted(jabvoteline['prefs'].items(),
                           key=lambda item: (-int(item[1].get('rating')),
                                             item[0])
                           )
        has_full_ratings = True
    except TypeError:
        prefitems = jabvoteline['prefs'].items()
        has_full_ratings = False

    if has_full_ratings:
        prefstr = _prefstr_from_ratings(prefitems)
    else:
        prefstr = _prefstr_from_ranked_line(prefitems)

    local_abif_str += f"{jabvoteline['qty']}:{prefstr}\n"
    #abiflib_test_log(f"func13: {local_abif_str=}")
    return local_abif_str


def _modify_jabmod(jabmod, modtuple):
    """Modify jabmod structure with list of tuples

    The tuples provided provide two things:
    1) A list which represents the path to the value being modified
    2) The new value for this key/index/whatever.
    """
    def _modify_jabmod_internal(this_jabmod, path):
        if len(path) == 1:
            this_jabmod[path[0]] = new_value
        else:
            next_key = path[0]
            _modify_jabmod_internal(this_jabmod[next_key], path[1:])

    path, new_value = modtuple
    _modify_jabmod_internal(jabmod, path)


########################
#  Misc functions for data cleaning and conversion
#


def clean_dict(data):
    '''Recursive function for converting sets to lists in a dict

    This function makes is intended to make it easier to convert
    arbitrary Python datastructures to something that works for JSON
    output.  As of June 2024, it only converts sets to lists.
    '''
    if isinstance(data, set):
        return list(data)
    elif isinstance(data, dict):
        return {k: clean_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_dict(item) for item in data]
    else:
        return data


def get_ranking_output_csv(abifmodel):
    # Use keys as field names
    outputhandle = io.StringIO()
    fieldnames = ['voterid']
    fieldnames.extend(abifmodel['candidates'])
    csvwriter = csv.DictWriter(outputhandle, fieldnames=fieldnames)
    csvwriter.writeheader()
    i = 0
    for y, vln in enumerate(abifmodel['votelines']):
        if vln['qty'] > 0:
            for z in range(vln['qty']):
                i += 1
                rlinedict = {ckey:
                             vln['prefs'][ckey]['rank']
                             for ckey in vln['prefs'].keys()}
                if vln.get('voterid'):
                    rlinedict['voterid'] = vln['voterid']
                else:
                    rlinedict['voterid'] = f"voter{i:06d}"
                csvwriter.writerow(rlinedict)
        else:
            msg = f"Invalid voteline: {vln}\n"
            raise ABIFVotelineException(value=vln, message=msg)
    retval = outputhandle.getvalue()
    return retval


def main():
    """core functions of abiflib

    This script allows for testing of core functions of abiflib"""
    initval = corefunc_init(tag="main")
    parser = argparse.ArgumentParser(
        description='Core functions of abiflib (and some cli stuff)')
    parser.add_argument('-f', '--func',
                        help='stub function to run',
                        default='pref_to_dict',
                        choices=['pref_to_dict',
                                 'emptyish',
                                 'modify_jabmod'])
    parser.add_argument('string', help='string(s) to pass to function',
                        default=None, nargs='+')
    args = parser.parse_args()

    if args.func == 'pref_to_dict':
        if not args.string:
            parser.error("pref_to_dict requires prefline as string[0]")
        parseout = _parse_prefstr_to_dict(f"{args.string[0]}")
        print(json.dumps(parseout, indent=4))
    elif args.func == 'emptyish':
        emptyish = _get_emptyish_abifmodel()
        print(json.dumps(emptyish, indent=4))
    elif args.func == 'modify_jabmod':
        if not args.string:
            parser.error("modify_jabmod requires filename as string[0]")
        else:
            print(f"FIXME: need to load jabmod file {args.string}")


if __name__ == "__main__":
    main()
