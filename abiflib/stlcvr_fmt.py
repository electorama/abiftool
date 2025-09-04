#!/usr/bin/env python3
'''abiflib/stlcvr_fmt.py - St. Louis (Hart Verity XML) CVR support'''

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

import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional

from abiflib.core import get_emptyish_abifmodel
from abiflib.util import utf8_string_to_abif_token as _short_token


NS = '{http://tempuri.org/CVRDesign.xsd}'


def _slugify_contest(name: str) -> str:
    s = (name or '').strip().lower()
    # Normalize common patterns first
    s = s.replace('–', '-').replace('—', '-').replace('  ', ' ')
    s = s.replace('alderman - ward', 'alderman-ward')
    s = s.replace('precinct', 'precinct')
    # Collapse multiple spaces
    while '  ' in s:
        s = s.replace('  ', ' ')
    # Remove spaces around hyphens
    s = s.replace(' - ', '-')
    # Ward numbers: remove leading zero
    s = s.replace('ward 01', 'ward 1')
    s = s.replace('ward 02', 'ward 2')
    s = s.replace('ward 03', 'ward 3')
    s = s.replace('ward 04', 'ward 4')
    s = s.replace('ward 05', 'ward 5')
    s = s.replace('ward 06', 'ward 6')
    s = s.replace('ward 07', 'ward 7')
    s = s.replace('ward 08', 'ward 8')
    s = s.replace('ward 09', 'ward 9')
    # Final replacements
    s = s.replace(' ', '-')
    # Keep alnum and hyphens only
    cleaned = []
    for ch in s:
        if ch.isalnum() or ch == '-':
            cleaned.append(ch)
    return ''.join(cleaned)


def _normalize_candidate(name: str) -> str:
    # Title Case with preservation of apostrophes/dots typical of initials
    try:
        return ' '.join([w[:1].upper() + w[1:].lower() for w in name.strip().split()])
    except Exception:
        return name.strip()


def _iter_xml_members(zf: zipfile.ZipFile):
    # Deterministic order for repeatable discovery and selection
    for fn in sorted(zf.namelist()):
        if fn.lower().endswith('.xml'):
            yield fn


def _maybe_set_event_metadata(abifmodel: dict, root: ET.Element):
    """Attempt to set high-level election metadata from a CVR file's root.

    Hart Verity CVR XML may include optional fields; probe several likely tags.
    This function is opportunistic and safe to call repeatedly.
    """
    def _get(tagname: str) -> Optional[str]:
        txt = root.findtext(f'{NS}{tagname}')
        if txt is not None:
            txt = txt.strip()
        return txt or None

    # Only set if not already present
    if not abifmodel['metadata'].get('election_name'):
        val = _get('ElectionName') or _get('ElectionTitle') or _get('Election')
        if val:
            abifmodel['metadata']['election_name'] = val
    if not abifmodel['metadata'].get('election_date'):
        val = _get('ElectionDate') or _get('Date')
        if val:
            abifmodel['metadata']['election_date'] = val
    if not abifmodel['metadata'].get('jurisdiction'):
        # Some datasets include County/Authority fields
        val = _get('County') or _get('CountyName') or _get('Authority') or _get('Jurisdiction')
        if val:
            abifmodel['metadata']['jurisdiction'] = val


def list_contests(zip_path: str, sample_limit: int = 200):
    """Print a list of contests discovered in the zip.

    Mirrors the behavior of sfjson_fmt.list_contests (prints to stdout).
    """
    contests = get_contest_list(zip_path, sample_limit=sample_limit)
    for c in contests:
        print(f"Contest {c['pos']}: {c['name']} (slug: {c.get('slug')})")

def get_contest_list(zip_path: str, sample_limit: int = 200):
    """Return a list of contest dicts for JSON listing and selection.

    Each dict includes: pos (1-based), name, slug, native_id (string), candidates_sample (small set).
    """
    contests: OrderedDict[str, Dict] = OrderedDict()
    count = 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for fn in _iter_xml_members(zf):
            with zf.open(fn) as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()
                except ET.ParseError:
                    continue
            contests_el = root.find(f'{NS}Contests')
            if contests_el is None:
                continue
            for c in contests_el.findall(f'{NS}Contest'):
                cname = (c.findtext(f'{NS}Name') or '').strip()
                cid = (c.findtext(f'{NS}Id') or '').strip()  # native Hart contest id, if present
                if not cname:
                    continue
                slug = _slugify_contest(cname)
                if slug not in contests:
                    contests[slug] = {
                        'name': cname,
                        'slug': slug,
                        'native_id': cid or None,
                        'candidates_sample': set(),
                    }
                # Sample a few candidates
                opts = c.find(f'{NS}Options')
                if opts is not None:
                    for opt in opts.findall(f'{NS}Option'):
                        oname = _normalize_candidate(opt.findtext(f'{NS}Name') or '')
                        if oname and len(contests[slug]['candidates_sample']) < 6:
                            contests[slug]['candidates_sample'].add(oname)
            count += 1
            if count >= sample_limit:
                break

    # Convert to list with stable positional index
    out = []
    for i, (slug, info) in enumerate(contests.items(), start=1):
        out.append({
            'pos': i,
            'name': info['name'],
            'slug': slug,
            'native_id': info.get('native_id'),
            'candidates_sample': sorted(list(info['candidates_sample']))
        })
    return out


def _select_contest_slug(zip_path: str, contestid: Optional[int]) -> Tuple[str, Dict]:
    """Derive a stable mapping of discovered contests and return selected slug.

    Uses the same discovery order as list_contests.
    """
    contests: OrderedDict[str, Dict] = OrderedDict()
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for fn in _iter_xml_members(zf):
            with zf.open(fn) as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()
                except ET.ParseError:
                    continue
            contests_el = root.find(f'{NS}Contests')
            if contests_el is None:
                continue
            for c in contests_el.findall(f'{NS}Contest'):
                cname = (c.findtext(f'{NS}Name') or '').strip()
                if not cname:
                    continue
                slug = _slugify_contest(cname)
                if slug not in contests:
                    contests[slug] = {
                        'name': cname,
                        'slug': slug,
                    }
    if not contests:
        raise ValueError('No contests found in container')
    # If no contestid provided, choose first
    if not contestid or contestid < 1 or contestid > len(contests):
        contestid = 1
    # Convert OrderedDict to list to index
    slugs = list(contests.keys())
    chosen_slug = slugs[contestid - 1]
    return chosen_slug, contests[chosen_slug]


def convert_stlcvr_to_jabmod(zip_path: str,
                             contestid: Optional[int] = None,
                             extra_metadata: Optional[Dict] = None) -> dict:
    """Convert St. Louis Hart Verity XML CVR zip to jabmod for a selected contest.

    - Emits approval-style ballots by setting rating=1 for approved candidates.
    - Tracks ballotcount and emptyballotcount in metadata.
    """
    target_slug, contest_meta = _select_contest_slug(zip_path, contestid)
    contest_name_local = contest_meta.get('name')

    abifmodel = get_emptyish_abifmodel()
    abifmodel['metadata']['ballotcount'] = 0
    abifmodel['metadata']['emptyballotcount'] = 0
    # Do not persist contest_slug or contest_name in metadata
    # Explicitly indicate approval-style ballots and cap rating at 1
    abifmodel['metadata']['ballot_type'] = 'choose_many'
    abifmodel['metadata']['max_rating'] = 1
    # Title is set later once we may have election_name available
    abifmodel['votelines'] = []

    # token map for stable candidate tokens
    cand_tokens: Dict[str, str] = {}

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for fn in _iter_xml_members(zf):
            with zf.open(fn) as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()
                except ET.ParseError:
                    continue

            # Opportunistically set event-level metadata once
            _maybe_set_event_metadata(abifmodel, root)

            contests_el = root.find(f'{NS}Contests')
            if contests_el is None:
                continue

            # Find target contest on this ballot
            target_contest_el = None
            for c in contests_el.findall(f'{NS}Contest'):
                cname = (c.findtext(f'{NS}Name') or '').strip()
                if _slugify_contest(cname) == target_slug:
                    target_contest_el = c
                    break

            # Count this ballot even if target contest is missing (treat as empty for this contest)
            abifmodel['metadata']['ballotcount'] += 1

            if target_contest_el is None:
                abifmodel['metadata']['emptyballotcount'] += 1
                continue

            # Build approval prefs from Options with Value==1 and capture native contest id
            opts = target_contest_el.find(f'{NS}Options')
            approvals: List[str] = []
            native_cid = (target_contest_el.findtext(f'{NS}Id') or '').strip()
            if native_cid and not abifmodel['metadata'].get('contest_native_id'):
                abifmodel['metadata']['contest_native_id'] = native_cid
            if opts is not None:
                for opt in opts.findall(f'{NS}Option'):
                    valtxt = (opt.findtext(f'{NS}Value') or '').strip()
                    try:
                        val = int(valtxt)
                    except Exception:
                        val = 0
                    if val == 1:
                        oname = _normalize_candidate(opt.findtext(f'{NS}Name') or '')
                        if oname:
                            approvals.append(oname)

            if not approvals:
                abifmodel['metadata']['emptyballotcount'] += 1
                continue

            # Create/update tokens and jabmod structures
            prefs: Dict[str, dict] = {}
            for full_name in approvals:
                # create token if needed
                if full_name not in cand_tokens:
                    tok = _short_token(full_name)
                    # resolve rare collisions by appending digits
                    base = tok
                    suffix = 2
                    while tok in abifmodel['candidates']:
                        tok = f"{base}{suffix}"
                        suffix += 1
                    cand_tokens[full_name] = tok
                    abifmodel['candidates'][tok] = full_name
                tok = cand_tokens[full_name]
                prefs[tok] = {'rating': 1}

            abifmodel['votelines'].append({'qty': 1, 'prefs': prefs})

    # Merge any extra metadata provided by caller (e.g., URLs)
    if extra_metadata and isinstance(extra_metadata, dict):
        for k, v in extra_metadata.items():
            # Shallow merge is sufficient for flat metadata
            if k == 'ext_urls' and isinstance(v, list):
                # Ensure list type and preserve order
                abifmodel['metadata'][k] = list(v)
            else:
                abifmodel['metadata'][k] = v

    # Compose title after merging extra metadata, preserving original casing
    if not abifmodel['metadata'].get('title'):
        cname = contest_name_local
        ename = abifmodel['metadata'].get('election_name')
        edate = abifmodel['metadata'].get('election_date')
        if ename and edate and cname:
            abifmodel['metadata']['title'] = f"{ename} ({edate}; {cname})"
        else:
            if ename and cname:
                abifmodel['metadata']['title'] = f"{ename}: {cname}"
            elif cname:
                abifmodel['metadata']['title'] = cname
            elif ename:
                abifmodel['metadata']['title'] = ename

    return abifmodel
