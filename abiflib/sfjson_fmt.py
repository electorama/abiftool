#!/usr/bin/env python3
'''abiflib/sfjson_fmt.py - San Francisco JSON CVR format support'''

# Copyright (c) 2025 Rob Lanphier
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
import zipfile
from abiflib.core import get_emptyish_abifmodel
from abiflib.util import utf8_string_to_abif_token as _short_token

def list_contests(container_path):
    """Lists the contests in a San Francisco JSON CVR zip file."""
    contests = get_contest_list(container_path)
    for i, c in enumerate(contests, start=1):
        print(f"Contest {i}: {c['name']} (native_id: {c['native_id']})")

def get_contest_list(container_path):
    """Return a list of contest dicts for JSON listing and selection.

    Each dict includes: pos (1-based), name, native_id.
    """
    with zipfile.ZipFile(container_path, 'r') as zf:
        with zf.open('ContestManifest.json') as f:
            contestmanblob = json.load(f)
    contests = []
    for i, contest in enumerate(contestmanblob['List'], start=1):
        contests.append({
            'pos': i,
            'name': contest.get('Description'),
            'native_id': contest.get('Id')
        })
    return contests

def convert_sfjson_to_jabmod(container_path, contestid=None):
    """Converts a zip file of San Francisco JSON CVRs to a jabmod."""
    abifmodel = get_emptyish_abifmodel()

    with zipfile.ZipFile(container_path, 'r') as zf:
        with zf.open('CandidateManifest.json') as f:
            candblob = json.load(f)
        with zf.open('ContestManifest.json') as f:
            contestmanblob = json.load(f)
        with zf.open('ElectionEventManifest.json') as f:
            eventmanblob = json.load(f)

        abifmodel['metadata']['ballotcount'] = 0
        abifmodel['metadata']['emptyballotcount'] = 0
        eventdesc = eventmanblob['List'][0]['Description']

        abifmodel['metadata']['contestid'] = contestid
        def _contest_index_lookup(targ, cmb):
            try:
                return next((i for i, contest in enumerate(cmb["List"]) if contest["Id"] == targ))
            except:
                print(f"{targ=}")
                sys.exit()
        if contestid:
            contestindex = _contest_index_lookup(contestid, contestmanblob)
        else:
            contestindex = 0
            contestid = contestmanblob['List'][contestindex]['Id']

        # Determine ballot_type from ContestManifest fields, with robust fallback
        contest_entry = contestmanblob['List'][contestindex]
        num_ranks = contest_entry.get('NumOfRanks', None)
        vote_for = contest_entry.get('VoteFor', None)

        bt = None
        try:
            if num_ranks is not None and int(num_ranks) > 0:
                bt = 'ranked'
            elif vote_for is not None and int(vote_for) == 1:
                bt = 'choose_one'
            elif vote_for is not None and int(vote_for) > 1:
                bt = 'choose_many'
        except Exception:
            bt = None

        if bt is None:
            # Fallback: infer from CVR marks if manifest lacks clear fields
            inferred_ranked = False
            for filename in zf.namelist():
                if filename.startswith('CvrExport_') and filename.endswith('.json'):
                    with zf.open(filename) as f:
                        blob = json.load(f)
                    sessions = blob.get('Sessions', [])
                    for sess in sessions:
                        for card in sess.get('Original', {}).get('Cards', []):
                            for c in card.get('Contests', []):
                                if c.get('Id') == contestid:
                                    for m in c.get('Marks', []):
                                        try:
                                            if int(m.get('Rank', 0)) > 1:
                                                inferred_ranked = True
                                                break
                                        except Exception:
                                            pass
                            if inferred_ranked:
                                break
                        if inferred_ranked:
                            break
                if inferred_ranked:
                    break
            bt = 'ranked' if inferred_ranked else 'choose_one'

        abifmodel['metadata']['ballot_type'] = bt

        title = f"{contest_entry['Description']} ({eventdesc})"
        abifmodel['metadata']['title'] = title

        # Create a lookup map from candidate ID to token and description
        cand_map = {}
        for c in candblob['List']:
            if c['ContestId'] == contestid:
                tok = _short_token(c['Description'])
                cand_map[c['Id']] = {'tok': tok, 'name': c['Description']}

        # Add the candidates section
        abifmodel['candidates'] = {c['tok']: c['name'] for c in cand_map.values()}

        # Add the votelines section
        abifmodel['votelines'] = []
        for filename in zf.namelist():
            if filename.startswith('CvrExport_') and filename.endswith('.json'):
                with zf.open(filename) as f:
                    jsoncvr_blob = json.load(f)
                for sess in jsoncvr_blob['Sessions']:
                    for card in sess['Original']['Cards']:
                        # Check if the card has the target contest
                        has_target_contest = False
                        for contest in card['Contests']:
                            if contest['Id'] == contestid:
                                has_target_contest = True
                                break

                        if has_target_contest:
                            i = len(abifmodel['votelines'])
                            abifmodel['metadata']['ballotcount'] += 1
                            abifmodel['votelines'].append({})
                            abifmodel['votelines'][i]['prefs'] = {}
                            abifmodel['votelines'][i]['qty'] = 1
                            for contest in card['Contests']:
                                if contest['Id'] == contestid:
                                    for m in contest['Marks']:
                                        candtok = cand_map[m['CandidateId']]['tok']
                                        abifmodel['votelines'][i]['prefs'][candtok] = {}
                                        abifmodel['votelines'][i]['prefs'][candtok]['rank'] = m['Rank']
                            if abifmodel['votelines'][i]['prefs'] == {}:
                                abifmodel['metadata']['emptyballotcount'] += 1

    return abifmodel
