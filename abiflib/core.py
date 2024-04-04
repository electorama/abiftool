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
from pprint import pprint
import copy
import json
import re
import sys
import urllib.parse

ABIF_VERSION = "0.1"
LOOPLIMIT = 400
ABIF_MODEL_LIMIT = 2500

# "DEBUGARRAY" is a generic array to put debug strings in to get
# printed if there's an exception or other debugging situations
DEBUGARRAY = []

class ABIFVotelineException(Exception):
    """Raised when votelines are missing from ABIF."""
    def __init__(self, value, message="ABIFVotelineException glares at you"):
        global DEBUGARRAY
        self.value = value
        self.message = message
        self.debugarray = DEBUGARRAY
        super().__init__(self.message)


class ABIFInputFormatException(Exception):
    """Raised when votelines are missing from ABIF."""
    def __init__(self, value, message="ABIFInputFormatException glares at you"):
        global DEBUGARRAY
        self.value = value
        self.message = message
        self.debugarray = DEBUGARRAY
        super().__init__(self.message)


class ABIFLoopLimitException(Exception):
    """Raised when the LOOPLIMIT is exceeded."""
    def __init__(self, value, message="ABIFLoopLimitException gets upset"):
        global DEBUGARRAY
        self.value = value
        self.message = message
        self.debugarray = DEBUGARRAY
        super().__init__(self.message)


class ABIFGenericError(Exception):
    """Raised when the LOOPLIMIT is exceeded."""
    def __init__(self, value, message="ABIFLoopLimitException gets upset"):
        global DEBUGARRAY
        self.value = value
        self.message = message
        self.debugarray = DEBUGARRAY
        super().__init__(self.message)


def convert_jabmod_to_abif(abifmodel, add_ratings=False):
    """Converts electowidget JSON (widj) to a .abif string."""
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
    for (i, voteline) in enumerate(abifmodel["votelines"]):
        try:
            is_ordered = voteline["orderedlist"]
        except KeyError:
            is_ordered = False

        abif_chunk = _get_prefstr_from_voteline(voteline)
        abif_string += abif_chunk

    return abif_string


def convert_abif_to_jabmod(inputstr, cleanws=False, add_ratings=False):
    abifmodel = {
        'metadata': {
            'ballotcount': 0
        },
        'candidates': {},
        'votelines': []
    }
    global COMMENT_REGEX, METADATA_REGEX
    global CANDLINE_REGEX, VOTELINE_REGEX
    commentregexp = re.compile(COMMENT_REGEX, re.VERBOSE)
    metadataregexp = re.compile(METADATA_REGEX, re.VERBOSE)
    candlineregexp = re.compile(CANDLINE_REGEX, re.VERBOSE)
    votelineregexp = re.compile(VOTELINE_REGEX, re.VERBOSE)

    abifmodel['metadata']['comments'] = []

    if len(inputstr) == 0:
        msg = f'Empty ABIF string..'
        raise ABIFVotelineException(value=inputstr, message=msg)

    for i, fullline in enumerate(inputstr.splitlines()):
        matchgroup = None
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
        abifmodel = _process_abif_comment_line(abifmodelin=abifmodel,
                                               linecomment=linecomment,
                                               linenum=i)

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
        else:
            matchgroup = 'empty'

    if len(abifmodel['votelines']) == 0:
        if len(inputstr) > 20:
            msg = f'No votelines in "{inputstr[:20]}...". '
        else:
            msg = f'No votelines in "{inputstr}". '
        msg += "Votelines (like '20:A>B>C') are required in valid ABIF files."
        raise ABIFVotelineException(value=inputstr, message=msg)

    # Dive down and find if ranks are provided.  If not, calculate
    # ranks based on ratings.
    firstprefs = abifmodel['votelines'][0]['prefs']
    firstk, firstv = list(firstprefs.items())[0]
    if not firstv['rank']:
        abifmodel = _add_ranks_to_jabmod_votelines(abifmodel)

    # Add in Borda-ish scores if ratings are not provided
    if not firstv.get('rating') and add_ratings:
        abifmodel = _add_ratings_to_jabmod_votelines(abifmodel)

    cleaned_lines = _cleanup_jabmod_votelines(abifmodel["votelines"])
    abifmodel["votelines"] = cleaned_lines

    slist = sorted(abifmodel["votelines"], key=lambda x: x['qty'],
                   reverse=True)
    abifmodel["votelines"] = slist

    return abifmodel


def ranklist_from_jabmod_voteline(voteline):
    """Construct list of candtoks in order of ranking"""
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


def _add_ranks_to_jabmod_votelines(inmod):
    ''' Calculate rankings from scores '''
    outmod = copy.deepcopy(inmod)
    for vl in outmod['votelines']:
        ratingvalset = set()
        for k, v in vl['prefs'].items():
            ratingvalset.add(v['rating'])
        rlist = sorted(ratingvalset, key=lambda x: int(x),
                       reverse=True)
        lookup = {rating: i + 1 for i, rating in enumerate(rlist)}
        for k, v in vl['prefs'].items():
            v['rank'] = lookup[v['rating']]
    return outmod


def _add_ratings_to_jabmod_votelines(inmod):
    ''' Calculate Borda-like ratings in lieu of explicit ratings '''
    numcands = len(inmod['candidates'])
    outmod = copy.deepcopy(inmod)
    for vl in outmod['votelines']:
        for k, v in vl['prefs'].items():
            v['rating'] = numcands - v['rank']
    return outmod


def _cleanup_jabmod_votelines(votelines):
    """Deduplicate votelines."""
    cln_votelines = {}
    for (i, voteline) in enumerate(votelines):
        try:
            is_ordered = voteline["orderedlist"]
        except KeyError:
            is_ordered = False

        try:
            prefitems = sorted(voteline['prefs'].items(),
                               key=lambda item: (-int(item[1].get('rating')),
                                                 item[0])
                               )
            has_full_ratings = True
        except TypeError:
            prefitems = voteline['prefs'].items()
            has_full_ratings = False

        if has_full_ratings:
            prefstr = _prefstr_from_ratings(prefitems)
        else:
            prefstr = _prefstr_from_ranked_line(prefitems)
        if prefstr in cln_votelines.keys():
            cln_votelines[prefstr]['qty'] += voteline['qty']
        else:
            cln_votelines[prefstr] = {}
            cln_votelines[prefstr]['qty'] = voteline['qty']
            cln_votelines[prefstr]['prefs'] = voteline['prefs']
            if 'comment' in voteline.keys():
                cln_votelines[prefstr]['comment'] = voteline['comment']
            if 'orderedlist' in voteline.keys():
                cln_votelines[prefstr]['orderedlist'] = voteline['orderedlist']
    retval = []
    for k, v in cln_votelines.items():
        retval.append(v)
    return retval


def _abif_token_quote(candtoken):
    quotedcand = urllib.parse.quote_plus(candtoken)
    if quotedcand == candtoken:
        candtoken = candtoken
    else:
        candtoken = f"[{candtoken}]"
    return candtoken


def _prefstr_from_ranked_line(sortedprefs):
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


def _get_prefstr_from_voteline(ballot):
    local_abif_str = ""

    try:
        prefitems = sorted(ballot['prefs'].items(),
                           key=lambda item: (-int(item[1].get('rating')),
                                             item[0])
                           )
        has_full_ratings = True
    except TypeError:
        prefitems = ballot['prefs'].items()
        has_full_ratings = False

    if has_full_ratings:
        prefstr = _prefstr_from_ratings(prefitems)
    else:
        prefstr = _prefstr_from_ranked_line(prefitems)

    local_abif_str += f"{ballot['qty']}:{prefstr}\n"
    return local_abif_str


def _process_abif_comment_line(abifmodelin={},
                               linecomment="",
                               linenum=0):
    commenttuple = (linenum, linecomment)
    if linecomment:
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
    '''(DEPRECATED) Tokenize the voter pref portion for a prefline

    Break up the prefstr on a prefline into a series of tokens for
    further processing as part of _process_abif_prefline.

    This function is deprecated in favor of _tokenize_abif_prefstr,
    and will probably be removed soon (as of April 2024).  There's a
    lot of debug cruft that was added back when the author thought it
    might be possible to incrementally improve his code.
    '''
    global LOOPLIMIT, DEBUGARRAY
    retval = []

    pref_range_candpart_regexp = VOTELINE_PREFPART_REGEX
    candpart_robj = re.compile(pref_range_candpart_regexp,
                               re.VERBOSE)

    remainingtext = prefstr
    loop_prefs = bool(re.fullmatch(candpart_robj, remainingtext))
    killcounter = 0
    raiseexception = False

    # 'prevlength' is an arbitrarily large number used for
    # detecting when parsing is stuck in a loop.
    prevlength = 999
    while loop_prefs:
        dbgmsg = f'{killcounter=} ({LOOPLIMIT=})\n'
        dbgmsg += f'{loop_prefs=}\n'
        dbgmsg += f'{prefstr=}\n'
        dbgmsg += f'{prevlength=}\n'
        dbgmsg += f'{remainingtext=} ({len(remainingtext)=})\n'
        dbgmsg += "\n".join(DEBUGARRAY) + "\n"
        dbgmsg += json.dumps(retval, indent=4)

        # if killcounter > LOOPLIMIT:
        if killcounter > LOOPLIMIT:
            raise ABIFVotelineException(value=prefstr, message=dbgmsg)
        if len(remainingtext) == prevlength or raiseexception:
            raise ABIFLoopLimitException(value=prefstr, message=dbgmsg)

        prevlength = len(remainingtext)
        killcounter += 1

        if loop_prefs:
            mt = re.fullmatch(candpart_robj, remainingtext)
            matches_new = mt
            loopsquare = False
        else:
            break
        if not matches_new or matches_new.group(0) == '':
            break
        candplusrate = matches_new.group('candplusrate')
        canddict = matches_new.groupdict()
        if 'candbare' in canddict.keys():
            cand = matches_new.group('candbare')
        elif 'candplusrate' in canddict.keys():
            cand = matches_new.group('candplusrate')
        elif 'candsqr' in canddict.keys():
            cand = matches_new.group('candsqr')
        elif remainingtext.startswith(('"')):
            DEBUGARRAY.append(f"FIXMEstart: {remainingtext=}\n")
            start_index = None
            quoted_text = ""
            end_index = 999
            for i, char in enumerate(remainingtext):
                if char == '"' and start_index is None:
                    start_index = i
                elif char == '"' and start_index is not None:
                    quoted_text += remainingtext[start_index + 1:i]
                    start_index = None
                    end_index = i + 1
            cand = quoted_text
            retval.append({'cand': cand})
            restofline = remainingtext[end_index:]
            DEBUGARRAY.append(f"FIXMEloop: {restofline=}\n")
            remainingtext = restofline
            ratingregexp = \
                r'\s*/\s*(?P<rating>\d+)\s*\b(?P<restofline>.*)$'
            if ratemat := re.fullmatch(ratingregexp, remainingtext):
                DEBUGARRAY.append(f"{ratemat=}")
                DEBUGARRAY.append(f"{ratemat.group('rating')=}")
                rating = matches_new.group('rating')
                retval.append({'rating': rating})
                restofline = matches_new.group('restofline')
                remainingtext = restofline
        else:
            raise


        retval.append({'cand': cand})
        rating = matches_new.group('rating')
        retval.append({'rating': rating})
        restofline = matches_new.group('restofline')
        remainingtext = restofline.lstrip()
        if remainingtext.startswith((">", "=", ",")):
            delimiter = remainingtext[0]
            retval.append({'delim': delimiter})
            remainingtext = remainingtext[1:]
        DEBUGARRAY.append(f"{matches_new=}")
    return retval


def _tokenize_abif_prefstr(prefstr):
    '''Tokenize the voter pref portion for a prefline

    This breaks up the prefstr portion of a prefline into a series of
    tokens.  The _process_abif_prefline function uses the tokens to
    give semantic structure to the prefstr.  It uses a stupidly
    complicated regex to do it, but it's not NEARLY as complicated
    (and buggy) as the code it replaced (the old
    _tokenize_abif_prefline function)

    '''

    pattern = re.compile(
        r'(\[[^\]]+\]|"[^"]+"|[\w\-]+)(?:/(\d+))?|([>,=])'
    )
    tokens = []
    for match in pattern.finditer(prefstr):
        cand, rating, delim = match.groups()
        if cand:
            cand = cand.strip('"[]')
            tokens.append({"cand": cand})
        if rating:
            tokens.append({"rating": rating})
        if delim:
            tokens.append({"delim": delim})

    return tokens


def _process_abif_prefline(qty,
                           prefstr,
                           abifmodel,
                           linecomment=None):
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
    linepair['prefstr'] = prefstr.rstrip()

    abifmodel['votelines'].append(linepair)
    abifmodel['votelines'][-1]['tokens'] = []
    prefs = {}
    candrank = 1
    votelineorder = 1
    ratingarray = {}
    orderedlist = None
    prefline_toks = _tokenize_abif_prefstr(prefstr)
    candnum = 0
    for tok in prefline_toks:
        abifmodel['votelines'][-1]['tokens'].append(tok)
        if 'cand' in tok:
            candnum += 1
            thiscand = tok['cand']
            prefs[thiscand] = {}
            if not thiscand in abifmodel['candidates']:
                abifmodel['candidates'][thiscand] = thiscand
        if 'rating' in tok:
            thisrating = tok['rating']
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
            elif thisdelim == '=':
                prefs[thiscand]['rank'] = candrank
            elif thisdelim == ",":
                # FIXME - use ratings when comma is delimiter
                prefs[thiscand]['rank'] = None
    prefs[thiscand]['rank'] = candrank
    abifmodel['votelines'][-1]['prefs'] = prefs
    return abifmodel


def main():
    """Test core functions of abiflib

    TODO: make this useful for testing more than
    _tokenize_abif_prefstr"""
    parser = argparse.ArgumentParser(
        description='Test core functions of abiflib')
    parser.add_argument('prefstr', help='The "prefstr" portion of an ABIF file')
    args = parser.parse_args()

    parseout = _tokenize_abif_prefstr(args.prefstr)
    print(f"{parseout=}")


if __name__ == "__main__":
    main()
