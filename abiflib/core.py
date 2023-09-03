#!/usr/bin/env python3
# abiflib/__init.py - conversion to/from .abif to other electoral expressions
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
import urllib.parse

ABIF_VERSION = "0.1"
DEBUGFLAG = False
LOOPLIMIT = 400

CONV_FORMATS = ('abif', 'jabmod', 'jabmoddebug', 'widj')


def debugprint(str):
    global DEBUGFLAG
    if DEBUGFLAG:
        print(str)
    return


def convert_jabmod_to_abif(abifmodel, add_ratings=True):
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


def convert_abif_to_jabmod(filename, debuginfo=False):
    debugprint(f"convert_abif_to_jabmod({filename=}, {debuginfo=})")
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
            candlineregexp = re.compile(
                r'''
                ^\=                     # the first character of candlines: "="
                \s*                     # whitespace
                ["\[]?                  # optional '[' or '"' prior to candtoken
                ([^:\"\]]*)             # candtoken; disallowed: " or ] or :
                ["\[]?                  # optional '[' or '"' after candtoken
                :                       # separator
                \[?                     # optional '[' prior to canddesc
                ([^\]]*)                # canddesc
                \]?                     # optional ']' after canddesc
                $                       # That's all, folks!
                ''', re.VERBOSE)
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
                           key=lambda item: (-int(item[1]['rating']),
                                             item[0])
                           )
        has_full_ratings = True
    except TypeError:
        #debugprint("I hope ballot['prefs'] is sorted already")
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
    # debugprint(f"{prefs=}")
    # debugprint(f"{abifmodel['candidates']=}")
    abifmodel['votelines'][-1]['prefs'] = prefs
    if orderedlist is None:
        abifmodel['votelines'][-1]['orderedlist'] = False
    else:
        abifmodel['votelines'][-1]['orderedlist'] = orderedlist
    return abifmodel
