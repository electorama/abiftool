#!/usr/bin/env python3
'''abiflib/core.py - core ABIF<=>jabmod conversion functions '''

# Copyright (c) 2023, 2024, 2025 Rob Lanphier
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


# --- Move these to the top so all functions can reference them ---
class ABIFVotelineException(Exception):
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
    #abiflib_test_log(f"{tag}: {abiflib_callstackstr(start=2, end=6)}")
    return {'tag': tag}


try:
    from line_profiler import profile
except ImportError:
    def profile(func):
        return func


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




# Compile all regexes at module scope for performance
from abiflib.abifregex import COMMENT_REGEX, METADATA_REGEX, CANDLINE_REGEX, VOTELINE_REGEX, VOTERID_REGEX
commentregexp = re.compile(COMMENT_REGEX, re.VERBOSE)
metadataregexp = re.compile(METADATA_REGEX, re.VERBOSE)
candlineregexp = re.compile(CANDLINE_REGEX, re.VERBOSE)
votelineregexp = re.compile(VOTELINE_REGEX, re.VERBOSE)
voteridregexp = re.compile(VOTERID_REGEX, re.VERBOSE)
# Precompile candidate preference pattern used in _extract_candprefs_from_prefstr
CANDPREF_PATTERN = re.compile(r'\[([^\]]+)\](?:/(\d+))?|"([^\"]+)"(?:/(\d+))?|([^\[\]",=>/]+)(?:/(\d+))?')

# Fast-path ballot parsing for simple cases (no brackets, quotes, or ratings)
def _extract_candprefs_from_prefstr(prefstr):
    '''Extract candidate tokens from prefstr portion of line'''
    # Fast path: no brackets, quotes, or ratings
    if not any(x in prefstr for x in '["=/'):
        # Split on '>' and filter out empty tokens
        return [(cand, None) for cand in (c.strip() for c in prefstr.split('>')) if cand]
    # Fallback to full regex for complex cases
    initval = corefunc_init(tag="f08a")
    retval = []
    for m in CANDPREF_PATTERN.finditer(prefstr):
        # Avoid .strip() if regex already excludes whitespace
        if m.group(1):
            ccand = m.group(1)
            if ccand:
                rating = int(m.group(2)) if m.group(2) else None
                retval.append((ccand, rating))
        elif m.group(3):
            ccand = m.group(3)
            if ccand:
                rating = int(m.group(4)) if m.group(4) else None
                retval.append((ccand, rating))
        elif m.group(5):
            ccand = m.group(5)
            if ccand:
                rating = int(m.group(6)) if m.group(6) else None
                retval.append((ccand, rating))
    return retval


########################
# Functions for parsing/reading abif into jabmod....
#

def _process_abif_comment_line(abifmodel=None,
                               linecomment="",
                               linenum=0,
                               storecomments=False):
    '''Store abif comments in jabmod metadata'''
    initval = corefunc_init(tag="f02")
    if not abifmodel:
        abifmodel = get_emptyish_abifmodel()
    commenttuple = (linenum, linecomment)
    if linecomment and storecomments:
        if not 'comments' in abifmodel['metadata']:
            abifmodel['metadata']['comments'] = []
        abifmodel['metadata']['comments'].append(commenttuple)
    return abifmodel
@profile
def convert_abif_to_jabmod(inputstr,
                           cleanws=False,
                           add_ratings=False,
                           extradata=None,
                           storecomments=False):
    """Converts an .abif string to JSON/jabmod

    'jabmod' stands for 'JSON ABIF Model', and is the internal abiflib
    data structure which is used throughout abiflib.
    """

    debug = os.environ.get('ABIFTOOL_DEBUG')
    if debug:
        print(f"DEBUG: Entered convert_abif_to_jabmod with inputstr of length {len(inputstr)}")
    lines = inputstr.splitlines()
    if debug:
        print(f"DEBUG: Number of lines in input: {len(lines)}")
        for idx, line in enumerate(lines[:5]):
            print(f"DEBUG: Line {idx}: '{line}'")

    abifmodel = get_emptyish_abifmodel()
    v = 0
    for i, fullline in enumerate(lines):
        matchgroup = None
        linecomment = None
        cparts = None
        # if "--cleanws" flag is given, strip leading whitespace
        if cleanws:
            fullline = re.sub(r"^\s+", "", fullline)
        # Quick skip: if line is empty or starts with '#' (comment), skip regexes
        if not fullline or fullline.lstrip().startswith('#'):
            abifmodel = _process_abif_comment_line(abifmodel=abifmodel,
                                                   linecomment=fullline,
                                                   linenum=i,
                                                   storecomments=storecomments)
            continue
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
        abifmodel = _process_abif_comment_line(abifmodel=abifmodel,
                                               linecomment=linecomment,
                                               linenum=i,
                                               storecomments=storecomments)

        # now to deal with the substance
        if debug:
            print(f"DEBUG: Processing line {i}: '{strpdline}'")
        # Quick skip: check first char to avoid unnecessary regexes
        firstchar = strpdline[:1]
        if firstchar == '=':
            candline_match = candlineregexp.match(strpdline)
            if candline_match:
                if debug:
                    print(f"DEBUG: candlineregexp matched: '{strpdline}' -> {candline_match.groups()}")
                matchgroup = 'candlineregexp'
                candtoken, canddesc = candline_match.groups()
                abifmodel = _process_abif_candline(candtoken,
                                                   canddesc,
                                                   abifmodel,
                                                   linecomment)
                continue
        elif firstchar == '@':
            match = metadataregexp.match(strpdline)
            if match:
                matchgroup = 'metadataregexp'
                mkey, mvalue = match.groups()
                abifmodel = _process_abif_metadata(
                    mkey, mvalue, abifmodel, linecomment)
                continue
        elif firstchar.isdigit():
            match = votelineregexp.match(strpdline)
            if match:
                matchgroup = 'votelineregexp'
                qty, prefstr = match.groups()
                abifmodel = _process_abif_prefline(qty,
                                                   prefstr,
                                                   abifmodel,
                                                   linecomment)
                v += 1
                continue
        # Fallback: try all regexes if not caught by above
        candline_match = candlineregexp.match(strpdline)
        if candline_match:
            if debug:
                print(f"DEBUG: candlineregexp matched: '{strpdline}' -> {candline_match.groups()}")
            matchgroup = 'candlineregexp'
            candtoken, canddesc = candline_match.groups()
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
            if debug:
                if ':' in strpdline:
                    print(f"DEBUG: Line contains colon but did not match candlineregexp: '{strpdline}'")
                print(f"DEBUG: No regex matched for: '{strpdline}'")
            matchgroup = 'empty'

    # Add in Borda-ish score if requested by calling function
    if add_ratings:
        abifmodel = add_ratings_to_jabmod_votelines(abifmodel)

    slist = sorted(abifmodel.get("votelines", []), key=lambda x: x['qty'],
                   reverse=True)
    abifmodel["votelines"] = slist
    if extradata:
        abiflib_test_log(f"Ignoring {extradata=}")

    return abifmodel
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


def get_emptyish_abifmodel():
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
    # Only assign ranks if at least one candidate has a rating but no rank
    needs_ranking = False
    for v in inprefjab.values():
        if v.get("rating") is not None and v.get("rank") is None:
            needs_ranking = True
            break
    if not needs_ranking:
        return inprefjab

    retval = inprefjab.copy()
    # Sort cands by rating (descending order)
    cands = sorted(retval,
                   key=lambda x: int(retval[x].get("rating", 0)),
                   reverse=True)

    # Assign ranks
    prevrate = None
    thisrank = 0
    for i, c in enumerate(cands):
        thisrate = int(retval[c].get("rating", 0))
        if i == 0:
            thisrank = 1
        elif thisrate < prevrate:
            thisrank += 1
        elif thisrate == prevrate:
            thisrank = prevrank
        else:
            raise ABIFVotelineException(message=f"Error: {i=} {c=} {thisrank=}")
        if retval[c].get("rank") is None:
            retval[c]["rank"] = thisrank
        prevrate = thisrate
        prevrank = thisrank
    return retval


def add_ratings_to_jabmod_votelines(inmod, add_ratings=True):
    ''' Calculate Borda-like ratings in lieu of explicit ratings '''
    # Detect if the rating key is in inmod anywhere.  Only add Borda
    # style ratings if there are no ratings anywhere in inmod.
    initval = corefunc_init(tag="f07")

    inmod_has_rating = False

    for voteline in inmod['votelines']:
        for k, v in voteline['prefs'].items():
            if "rating" in v:
                inmod_has_rating = True

    numcands = len(inmod['candidates'])
    # Custom shallow copy: copy top-level dict, and make a new votelines list with copied prefs dicts
    outmod = dict(inmod)
    outmod['votelines'] = []
    for vl in inmod['votelines']:
        new_vl = dict(vl)
        new_prefs = {}
        for k, v in vl['prefs'].items():
            new_pref = dict(v)
            # The ratings that get added should depend on whether
            # inmod has ratings.  If it has ratings for some entries,
            # then assume a default of zero for the entries that don't
            # have ratings.  If there are no ratings throughout, then
            # assume the ratings to be added are Borda-ish.
            if not new_pref.get('rating'):
                if inmod_has_rating:
                    new_pref['rating'] = 0
                elif add_ratings:
                    if numcands == 1:
                        new_pref['rating'] = 1
                    else:
                        new_pref['rating'] = numcands - new_pref['rank']
                    # Ensure metadata exists and is a dict
                    if 'metadata' not in outmod or not isinstance(outmod['metadata'], dict):
                        outmod['metadata'] = {}
                    outmod['metadata']['is_ranking_to_rating'] = True
            new_prefs[k] = new_pref
        new_vl['prefs'] = new_prefs
        outmod['votelines'].append(new_vl)
    return outmod


@profile
def _extract_candprefs_from_prefstr(prefstr):
    '''Extract candidate tokens from prefstr portion of line'''
    initval = corefunc_init(tag="f08a")
    retval = []
    # Use precompiled regex for candidate tokens
    for m in CANDPREF_PATTERN.finditer(prefstr):
        if m.group(1):  # [Name] or [Name]/N
            ccand = m.group(1).strip()
            if ccand:
                rating = int(m.group(2)) if m.group(2) else None
                retval.append((ccand, rating))
        elif m.group(3):  # "Name" or "Name"/N
            ccand = m.group(3).strip()
            if ccand:
                rating = int(m.group(4)) if m.group(4) else None
                retval.append((ccand, rating))
        elif m.group(5):  # Name or Name/N
            ccand = m.group(5).strip()
            if ccand:
                rating = int(m.group(6)) if m.group(6) else None
                retval.append((ccand, rating))
    return retval


def _determine_rank_or_rate(prefstr):
    '''Determine if a prefstr represents a ranking, a set of ratings,
       or just one candidate'''
    # replace all square-bracketed candidates with a placeholder
    subbedstr, num_of_bracketed_tok = re.subn(r'\[[^]]*\]', '[PLACEHOLDER]', prefstr)
    delimeters = [char for char in subbedstr if char in ">,="]
    if delimeters and delimeters[0] in '>=':
        rank_or_rate = "rank"
    elif delimeters and delimeters[0] == ",":
        rank_or_rate = "rate"
    else:
        rank_or_rate = "rankone"
    return rank_or_rate, delimeters


@profile
def _parse_prefstr_to_dict(prefstr, qty=0,
                           abifmodel=None, linecomment=None):
    '''Convert prefstr portion of .abif voteline to jabvoteline
    structure.'''
    initval = corefunc_init(tag="f08b")
    prefs = {}
    rank = 1

    if not abifmodel:
        abifmodel = get_emptyish_abifmodel()

    rank_or_rate, delimeters = _determine_rank_or_rate(prefstr)
    candpreflist = _extract_candprefs_from_prefstr(prefstr)
    candkeys = []
    n = len(candpreflist)
    for i in range(n):
        cand, candrating = candpreflist[i]
        candkeys.append(cand)
        prefs_cand = {}
        if candrating is not None:
            prefs_cand["rating"] = candrating
        if rank_or_rate == "rankone":
            prefs_cand["rank"] = 1
        elif rank_or_rate == "rank":
            prefs_cand["rank"] = rank
            if i < n - 1 and delimeters[i] == ">":
                rank += 1
                prefs_cand["nextdelim"] = delimeters[i]
        if i < n - 1:
            prefs_cand["nextdelim"] = delimeters[i]
        prefs[cand] = prefs_cand

    prefs = _add_ranks_to_prefjab_by_rating(inprefjab=prefs)

    if candkeys:
        firstcandprefs = prefs.get(candkeys[0], {})
        if firstcandprefs.get('rating') is not None and not firstcandprefs.get('rank'):
            prefs = _add_ranks_to_prefjab_by_rating(inprefjab=prefs)
    else:
        prefs = {}
    prefstrdict = {"prefs": prefs, "cands": candkeys}
    return prefstrdict

    prefstrdict = {"prefs": prefs, "cands": candkeys}
    return prefstrdict


@profile
def _process_abif_prefline(qty, prefstr,
                           abifmodel=None, linecomment=None):
    '''Add prefline with qty to the provided abifmodel/jabmod'''
    initval = corefunc_init(tag="f09")
    voterid = None
    if linecomment is not None:
        match = voteridregexp.match(linecomment)
        if match:
            voterid = match.groupdict()['voterid']

    if not abifmodel:
        abifmodel = get_emptyish_abifmodel()

    abifmodel_metadata = abifmodel['metadata']
    abifmodel_candidates = abifmodel['candidates']
    abifmodel_votelines = abifmodel['votelines']
    abifmodel_metadata['ballotcount'] += int(qty)

    prefstrdict = _parse_prefstr_to_dict(prefstr,
                                         qty=qty,
                                         abifmodel=abifmodel,
                                         linecomment=linecomment)
    linepair = {'qty': int(qty), 'prefs': prefstrdict['prefs'], 'prefstr': prefstr.rstrip()}
    if linecomment is not None:
        linepair['comment'] = linecomment
    if voterid is not None:
        linepair['voterid'] = voterid
    abifmodel_votelines.append(linepair)
    # merge candidate list into abifmodel['candidates']
    for x in prefstrdict['cands']:
        if x not in abifmodel_candidates:
            abifmodel_candidates[x] = x
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
    if quotedcand == candtoken and not candtoken.isdecimal():
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
    lastrank = 1
    add_delim = False

    for i, (name, data) in enumerate(sortedprefs):
        if 'rank' in data:
            rank = data['rank']

        prefstrfromranks += _abif_token_quote(name)
        # Only emit /rating if it was present in the input (not defaulted to 0)
        if 'rating' in data and data['rating'] is not None:
            # Only emit if not zero, or if it was explicitly present as zero
            if data['rating'] != 0 and data['rating'] != '0':
                prefstrfromranks += f"/{data['rating']}"
        if i < len(sortedprefs) - 1:
            nextrank = sortedprefs[i+1][1]['rank']
            if rank < nextrank:
                delim = '>'
            elif rank == nextrank:
                delim = '='
            else:
                raise(ValueError(f"Ranks don't make sense: {sortedprefs=}"))
            prefstrfromranks += delim
        lastrank = rank
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
        except (TypeError, ValueError, KeyError):
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
                rating = thistier[ckey].get('rating', None)
                # Only emit /rating if not None and not zero
                if rating is not None and rating != 0 and rating != '0':
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
        prefstr = _prefstr_from_ranked_line(sorted(prefitems,
                                                   key=lambda x: x[1]['rank']))
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


def consolidate_jabmod_voteline_objects(jabmod):
    retval_votelines = []
    prefs_to_voteline = {}

    for voteline in jabmod["votelines"]:
        prefs = json.dumps(voteline["prefs"], sort_keys=True)
        if prefs not in prefs_to_voteline:
            prefs_to_voteline[prefs] = {"prefs": voteline["prefs"], "qty": 0}
        prefs_to_voteline[prefs]["qty"] += voteline["qty"]

    retval_votelines.extend(prefs_to_voteline.values())
    retval_votelines.sort(key=lambda x: x['qty'], reverse=True)
    jabmod["votelines"] = retval_votelines
    return jabmod


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
                                 'process_abif_prefline',
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
    elif args.func == 'process_abif_prefline':
        if not args.string:
            parser.error("process_abif_prefline requires prefline as string[0]")
        parseout = _process_abif_prefline(0, f"{args.string[0]}")
        print(json.dumps(parseout, indent=4))
    elif args.func == 'emptyish':
        emptyish = get_emptyish_abifmodel()
        print(json.dumps(emptyish, indent=4))
    elif args.func == 'modify_jabmod':
        if not args.string:
            parser.error("modify_jabmod requires filename as string[0]")
        else:
            print(f"FIXME: need to load jabmod file {args.string}")


if __name__ == "__main__":
    main()
