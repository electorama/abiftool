#!/usr/bin/env python3
''' abiflib/sftxt.py - conversion functions for election results published by SF '''

# Copyright (C) 2018, 2024 Rob Lanphier
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


"""
Parse the ballot image files provided by the City of San Francisco:
https://sfelections.sfgov.org/results
"""

BALLOTIMAGE_FIELDSPEC = """fieldname,lastchar,length
Contest_Id,7,7
Pref_Voter_Id,16,9
Serial_Number,23,7
Tally_Type_Id,26,3
Precinct_Id,33,7
Vote_Rank,36,3
Candidate_Id,43,7
Over_Vote,44,1
Under_Vote,45,1
"""

MASTERLOOKUP_FIELDSPEC = """fieldname,lastchar,length
Record_Type,10,10
Id,17,7
Description,67,50
List_Order,74,7
Candidates_Contest_Id,81,7
Is_WriteIn,82,1
Is_Provisional,83,1
"""


from abiflib import *
import argparse
from collections import OrderedDict
 
import csv
import fileinput
from io import StringIO
import json
import re
import sys
import urllib.parse


def sftxt_read_fieldspec(fieldspec_string):
    """
    The image files and the master lookup (among others) provided in
    SF elections are fixed-width text fields.  This function:
    1.  ...reads the CSV file that specifies field names and the
        position of the last character of each field.
    2.  ...build a regex which can be used to read the fixed width
        fields
    """
    # 1. read the csv spec into a list of dicts
    list_of_rows = []
    csvfile = StringIO(fieldspec_string)
    reader = csv.DictReader(csvfile)
    for row in reader:
        list_of_rows.append(row)

    # 2. build regex from list_of_rows
    regex = r'^'
    fieldnames = []
    pos = 0
    for field in list_of_rows:
        lastchar = field['lastchar']
        regex += r'(.{'
        regex += str(int(lastchar) - pos)
        regex += r'})'
        pos = int(lastchar)
        fieldnames.append(field['fieldname'])
        if (int(lastchar) - pos) == int(field['length']):
            raise ValueError(
                "Length mismatch in {1}".format(field['fieldname']))
    return(regex, fieldnames)


def read_sftxt_file(fieldspec, datafile=None, datastr=None):
    """
    This function uses a regex (created in sftxt_read_fieldspec) to convert
    each line of an SF election ballot image file into a Python
    OrderedDict suitable for output as JSON or YAML.
    """
    (regex, fields) = sftxt_read_fieldspec(fieldspec)

    if datafile:
        sfballots = fileinput.input(datafile)
    elif datastr:
        sfballots = datastr.splitlines()
    else:
        raise ValueError("Either 'datafile' or 'datastr' must be provided.")

    for line in sfballots:
        regmatch = re.match(regex, line)
        if regmatch:
            rowdict = OrderedDict()
            for i, field in enumerate(fields):
                rowdict[field] = regmatch.group(i + 1)
            yield(rowdict)
        else:
            raise ValueError('generated regex does not match datafile')

def read_sftxt_blob(fieldspec, datablob):
    """
    This function uses a regex (created in sftxt_read_fieldspec) to convert
    each line of an SF election ballot image file into a Python
    OrderedDict suitable for output as JSON or YAML.
    """
    (regex, fields) = sftxt_read_fieldspec(fieldspec)

    for line in datablob.splitlines():
        regmatch = re.match(regex, line)
        if regmatch:
            rowdict = OrderedDict()
            for i, field in enumerate(fields):
                rowdict[field] = regmatch.group(i + 1)
            yield(rowdict)
        else:
            raise ValueError('generated regex does not match datablob')


def _sftxt_lookuplines2candpool(lookuplines, contestid=None):
    # build up dict to look up candidate names from id
    candpool = OrderedDict()
    candpool['0000000'] = None

    for lookupline in lookuplines:
        if lookupline['Record_Type'].strip() == 'Candidate':
            candpool[lookupline['Id']] = \
                lookupline['Description'].strip()
        if lookupline['Record_Type'].strip() == 'Contest':
            # default contestid will be the first one listed
            if not contestid:
                contestid = lookupline['Id']
    return candpool, contestid


def _sftxt_convert_to_ballots(imagelines, candpool, contestid=None):
    """
    Each line of the ballot image file contains just one of many
    possible candidate preferences expressed on a given ballot.  For
    example, in the 2018 SF Mayoral race, voters could choose up to 3
    preferences for mayor.  Each preference expressed would have its own
    line in the image file.  This function aggregates all of the
    preferences expressed on a ballot into a single hierarchical data
    structure, with one set of ballotfields per ballot, and many sets
    of votefields (one set per candidate chosen)
    """
    ballotfields = [
        'Contest_Id',
        'Pref_Voter_Id',
        'Serial_Number',
        'Tally_Type_Id',
        'Precinct_Id'
    ]

    # create an empty ballot with proper field order to deepcopy when
    # needed
    emptyballot = OrderedDict()
    for field in ballotfields:
        emptyballot[field] = None

    thisballot = emptyballot.copy()
    lastballot = thisballot
    for imageline in imagelines:
        # skip over all imagelines that aren't associated with the
        # contestid passed in
        if not imageline['Contest_Id'] == contestid:
            continue

        # each ballot may result in 3 image lines (one for each
        # preference the voter marks).  See if this line is the same
        # voter/ballot as the previous line
        if(thisballot['Pref_Voter_Id'] != imageline['Pref_Voter_Id']):
            # if the Prev_Voter_Id doesn't line up, that means we're
            # done with a ballot.  yield it from this function, then
            # start building a new ballot from this line.
            if thisballot['Pref_Voter_Id'] != None:
                yield(thisballot)
            lastballot = thisballot
            thisballot = emptyballot.copy()
            for field in ballotfields:
                thisballot[field] = imageline[field]
            thisballot['votes'] = []
        # store the preference associated with this imageline in
        # "thisvote"
        thisvote = OrderedDict()
        thisvote['rank'] = int(imageline['Vote_Rank'])
        thisvote['candidate'] = candpool[imageline['Candidate_Id']]
        overvote = (imageline['Over_Vote'] == '1')
        undervote = (imageline['Under_Vote'] == '1')
        if(overvote and undervote):
            raise ValueError('both overvote and undervote flagged')
        elif(overvote):
            thisvote['exception'] = 'overvote'
        elif(undervote):
            thisvote['exception'] = 'undervote'
        thisballot['votes'].append(thisvote)
    # now that we're out of the loop, yield the last ballot
    yield(thisballot)


def _sftxt_dump_url_encoded(outputrecords, outfh):
    for rec in outputrecords:
        outrec = {}
        # populate the higher ranked duplicates take priority over
        # the lower rank
        outrec[rec['votes'][0]['candidate']] = rec['votes'][0]['rank']
        if not rec['votes'][1]['candidate'] in outrec:
            outrec[rec['votes'][1]['candidate']] = rec['votes'][1]['rank']
        if not rec['votes'][2]['candidate'] in outrec:
            outrec[rec['votes'][2]['candidate']] = rec['votes'][2]['rank']
        print(urllib.parse.urlencode(outrec), file=outfh)


def _sftxt_dump_csv1996fmt(candpool, outputrecords, outfh):
    """
    This was the format used by my old 1996 Perl script
    """
    candnum=0
    revcand={}
    for candid, candname in candpool.items():
        if candname:
            print("{:d}, {}".format(candnum, candname), file=outfh)
        revcand[candname]=candnum
        candnum+=1
    for rec in outputrecords:
        outrec = {}
        outstr=""
        # populate the higher ranked duplicates take priority over
        # the lower rank
        candname=rec['votes'][0]['candidate']
        outrec[candname] = rec['votes'][0]['rank']
        outstr=str(revcand[candname])

        candname=rec['votes'][1]['candidate']
        candrank=rec['votes'][1]['rank']
        if candname and not candname in outrec:
            outrec[candname] = candrank
            outstr+=">"
            outstr+=str(revcand[candname])

        candname=rec['votes'][2]['candidate']
        candrank=rec['votes'][2]['rank']
        if candname and not candname in outrec:
            outrec[candname] = candrank
            outstr+=">"
            outstr+=str(revcand[candname])

        print(outstr, file=outfh)


def _short_token(longstring, max_length=20, add_sha1=False):
    if len(longstring) <= max_length and \
       re.match(r'^[A-Za-z0-9]+$', longstring):
        retval = longstring
    else:
        cleanstr = re.sub('[^A-Za-z0-9]+', '_', longstring)
        cleanstr = re.sub('WRITE_IN_', "wi_", cleanstr)
        retval = cleanstr[:max_length]
    return retval


def convert_sftxt_to_jabmod(sftxt_master_blob, sftxt_ballot_blob, verbose=False):
    """
    convert the sftxt format to jabmod
    """

    candpool = sftxt_master_blob
    outputrecords = sftxt_ballot_blob

    retval = get_emptyish_abifmodel()

    lookuplines = list(read_sftxt_blob(MASTERLOOKUP_FIELDSPEC, sftxt_master_blob))

    (candpool, contestid)=_sftxt_lookuplines2candpool(lookuplines)
    retval['metadata']['contestid'] = contestid

    imagelines = read_sftxt_file(BALLOTIMAGE_FIELDSPEC, datastr=sftxt_ballot_blob)

    outputrecords = _sftxt_convert_to_ballots(imagelines, candpool,
                                              contestid=contestid)
    candnum=0
    revcand={}
    for candid, candname in candpool.items():
        if candname:
            candtok = _short_token(candname)
        else:
            candtok = f"cand{candnum}"
        revcand[candname] = candtok
        retval['candidates'][candtok] = candname
        candnum+=1
    for rec in outputrecords:
        outrec = {}
        vljson = {}
        if verbose:
            vljson['comment'] = ( f"Contest: {rec['Contest_Id']}; " +
                                  f"Voter: {rec['Pref_Voter_Id']}; " +
                                  f"SerialNum: {rec['Serial_Number']}; " +
                                  f"TalType: {rec['Tally_Type_Id']}; " +
                                  f"Precinct: {rec['Precinct_Id']};")
        vljson['prefs'] = {}
        vljson['qty'] = 1
        for p in rec['votes']:
            if p['candidate']:
                candtok = _short_token(p['candidate'])
            else:
                candtok = "(none)"
            if candtok != "(none)" or verbose:
                vljson['prefs'][candtok] = {}
                vljson['prefs'][candtok]['rank'] = p['rank']
        retval['metadata']['ballotcount'] += 1

        retval['votelines'].append(vljson)

    if not verbose:
        retval = consolidate_jabmod_voteline_objects(retval)

    return retval


def main(argv=None):
    # using splitlines to just get the first line
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--imagelines',
                        help='print records for imagelines',
                        action="store_true")
    parser.add_argument('lookupfile',
                        help='master lookup file for this election')
    parser.add_argument('imagefile', help='ballot image file')
    parser.add_argument('-o', '--outfile', help='output file',
                        default=None)
    parser.add_argument('--contestid', help='contest id; defaults to first found',
                        default=None)
    parser.add_argument('--outputformat',
                        help='output format: json (default), urlencoded'
                        ' (for Brian Olson\'s voteutil)', default="json")
    parser.add_argument('--consolidate',
                        help='consolidate ballots when rankings are equivalent',
                        action="store_true")

    args = parser.parse_args()

    # FIXME - read args.lookupfile and args.imagefile files once rather than twice
    lookuplines = list(read_sftxt_file(
        MASTERLOOKUP_FIELDSPEC, args.lookupfile))

    imagelines = read_sftxt_file(BALLOTIMAGE_FIELDSPEC, args.imagefile)

    (candpool, contestid)=_sftxt_lookuplines2candpool(lookuplines, contestid=args.contestid)

    if(args.imagelines):
        # TODO: filter imagelines by args.contestid
        outputrecords = imagelines
    else:
        outputrecords = _sftxt_convert_to_ballots(imagelines, candpool,
                                                  contestid=contestid)

    if args.outfile:
        outfh = open(args.outfile, 'w')
    else:
        outfh = sys.stdout

    # FIXME - either use args.lookupfile and args.imagefile reading above or the simpler
    # version below
    with open(args.lookupfile, "r") as f:
        masterblob = f.read()
    with open(args.imagefile, "r") as f:
        ballotblob = f.read()

    if args.outputformat == 'json':
        try:
            json.dump(outputrecords, outfh, indent=4)
        except TypeError:
            # convert generator to list
            json.dump(list(outputrecords), outfh, indent=4)
    elif args.outputformat == 'abif':
        jabmod = convert_sftxt_to_jabmod(masterblob, ballotblob,
                                         verbose=False)
        if args.consolidate:
            jabmod = consolidate_jabmod_voteline_objects(jabmod)
        outstr = convert_jabmod_to_abif(jabmod)
        print(outstr)
    elif args.outputformat == 'jabmod':
        jabmod = convert_sftxt_to_jabmod(masterblob, ballotblob,
                                         verbose=False)
        if args.consolidate:
            jabmod = consolidate_jabmod_voteline_objects(jabmod)
        print(json.dumps(jabmod, indent=4))
    elif args.outputformat == 'urlencoded':
        _sftxt_dump_url_encoded(outputrecords, outfh)
    elif args.outputformat == 'csv96':
        _sftxt_dump_csv1996fmt(candpool, outputrecords, outfh)
    else:
        raise ValueError(
            'args.outputformat {} not recognized'.format(args.outputformat))


if __name__ == '__main__':
    exit_status = main(sys.argv)
    sys.exit(exit_status)
