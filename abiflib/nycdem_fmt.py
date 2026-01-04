#!/usr/bin/env python3
'''abiflib/nycdem_fmt.py - New York City Democratic primary CVR format support'''

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

import pandas as pd
import os
import json
import zipfile
import io
from abiflib.core import get_emptyish_abifmodel
from abiflib.debvote_fmt import _short_token
import re
import abiflib


def _env_flag(name: str) -> bool:
    return str(os.environ.get(name, "")).lower() in {"1", "true", "yes", "on"}


_DEBUG_HEADERS = _env_flag("ABIFLIB_DEBUG_HEADERS")


def set_debug_headers(enabled: bool) -> None:
    """Enable or disable detailed NYC header debug logging."""

    global _DEBUG_HEADERS
    _DEBUG_HEADERS = bool(enabled)


def _log(message: str, *, debug: bool = False) -> None:
    """Central logging helper that gates debug output."""

    if debug and not _DEBUG_HEADERS:
        return
    print(message)


def _match_contest_rank_columns(columns, contest_string):
    """Return ranking columns for the desired contest using shared heuristics."""

    contest_str = str(contest_string or "")
    contest_lower = contest_str.lower()
    matches = [col for col in columns if contest_lower in str(col).lower()]
    district_match = re.search(r"district\s*(\d+)", contest_str, flags=re.IGNORECASE)
    district_num = int(district_match.group(1)) if district_match else None

    if not matches and district_num is not None and re.search(r"council\s*member", contest_str, flags=re.IGNORECASE):
        pattern = rf"council\s*member.*(?<!\d)0*{district_num}(?:st|nd|rd|th)\b\s*council\s*district"
        strict_matches = [col for col in columns if re.search(pattern, str(col), flags=re.IGNORECASE)]
        if strict_matches:
            matches = strict_matches
            sample = [str(c) for c in matches[:3]]
            _log(f"[nycdem_fmt] District {district_num} matched headers: {sample}", debug=True)
        else:
            _log(f"[nycdem_fmt] No strict district header matches found for district {district_num}", debug=True)

    if not matches and re.search(r"council\s*member", contest_str, flags=re.IGNORECASE):
        if district_num is not None:
            _log("[nycdem_fmt] Skipping base 'DEM Council Member' fallback for district-specific contest", debug=True)
        else:
            base = re.sub(r"\s*district\s*\d+", "", contest_str, flags=re.IGNORECASE).strip()
            if base and base.lower() != contest_lower:
                fallback_matches = [col for col in columns if base.lower() in str(col).lower()]
                if fallback_matches:
                    matches = fallback_matches
                    _log(
                        f"[nycdem_fmt] Using base council member fallback with {len(matches)} columns",
                        debug=True,
                    )

    return matches

def discover_headers_in_zip(zip_path, sample_rows=5):
    """Scan all non-candidacy Excel files in a NYC CVR ZIP and return a
    structured report of headers and likely matching keys.

    Returns a dict with keys:
      - zip_path
      - has_candidacy_mapping (bool)
      - files: list of { name, headers, rank_prefixes, district_cols, precinct_cols, rank_samples }
      - global_rank_prefixes: sorted list of unique prefixes across files
    """
    report = {
        'zip_path': zip_path,
        'has_candidacy_mapping': False,
        'files': [],
        'global_rank_prefixes': [],
    }
    global_prefixes = set()
    candidacy_seen = False
    with zipfile.ZipFile(zip_path, 'r') as zf:
        excel_files = [f for f in zf.namelist() if f.endswith('.xlsx')]
        candidacy_files = [f for f in excel_files if 'candidacy' in f.lower() or 'candidacyid_to_name' in f.lower()]
        if candidacy_files:
            candidacy_seen = True
        for excel_file in excel_files:
            if excel_file in candidacy_files:
                continue
            try:
                with zf.open(excel_file) as f:
                    df = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl", nrows=sample_rows)
            except Exception as e:
                report['files'].append({'name': excel_file, 'error': str(e)})
                continue
            headers = [str(c) for c in df.columns]
            # Identify ranking columns and prefixes
            rank_cols = [h for h in headers if re.search(r"\bChoice\b|\bRank\b", h, flags=re.IGNORECASE)]
            prefixes = []
            for h in rank_cols:
                m = re.split(r"\bChoice\b|\bRank\b", h, maxsplit=1, flags=re.IGNORECASE)
                if m:
                    prefixes.append(m[0].strip())
            # Candidate district/precinct column candidates
            lower_headers = [h.lower() for h in headers]
            district_cols = [h for h in headers if re.search(r"council\s*district|\bdistrict\b|\bcd\b", h, flags=re.IGNORECASE)]
            precinct_cols = [h for h in headers if re.search(r"precinct|election\s*district|\bed\b|\bad\b", h, flags=re.IGNORECASE)]
            # Sample a few values from up to 3 ranking columns
            rank_samples = {}
            for col in rank_cols[:3]:
                try:
                    vals = [str(v) for v in df[col].dropna().unique()[:5]]
                except Exception:
                    vals = []
                rank_samples[col] = vals
            global_prefixes.update(prefixes)
            report['files'].append({
                'name': excel_file,
                'headers': headers,
                'rank_prefixes': sorted(set(prefixes)),
                'district_cols': district_cols,
                'precinct_cols': precinct_cols,
                'rank_samples': rank_samples,
            })
    report['has_candidacy_mapping'] = candidacy_seen
    report['global_rank_prefixes'] = sorted(global_prefixes)
    return report


def save_header_report(path, report):
    """Write a human-friendly header report produced by discover_headers_in_zip()."""
    lines = []
    lines.append(f"NYC CVR header discovery report")
    lines.append(f"ZIP: {report.get('zip_path')}")
    lines.append(f"Candidacy mapping present: {report.get('has_candidacy_mapping')}")
    gp = report.get('global_rank_prefixes') or []
    if gp:
        lines.append("Global rank prefixes (unique):")
        for p in gp:
            lines.append(f"  - {p}")
    lines.append("")
    for f in report.get('files', []):
        lines.append(f"File: {f.get('name')}")
        if f.get('error'):
            lines.append(f"  Error: {f['error']}")
            lines.append("")
            continue
        rp = f.get('rank_prefixes') or []
        if rp:
            lines.append("  Rank prefixes:")
            for p in rp:
                lines.append(f"    - {p}")
        dc = f.get('district_cols') or []
        if dc:
            lines.append("  District-like columns:")
            for h in dc[:6]:
                lines.append(f"    - {h}")
        pc = f.get('precinct_cols') or []
        if pc:
            lines.append("  Precinct-like columns:")
            for h in pc[:6]:
                lines.append(f"    - {h}")
        rs = f.get('rank_samples') or {}
        if rs:
            lines.append("  Rank column samples:")
            for col, vals in list(rs.items())[:3]:
                sval = ", ".join(vals[:5]) if vals else "(no values in sample)"
                lines.append(f"    - {col}: {sval}")
        lines.append("")
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w') as outf:
        outf.write("\n".join(lines))

def convert_nycdem_to_jabmod(srcfile, contestid=None, fetchspec=None, contest_string="Mayor", district=None):
    """Convert NYC CVR Excel file(s) to ABIF jabmod, focusing on a given contest.

    Args:
        srcfile: Path to .xlsx or .zip containing NYC CVR spreadsheets
        contestid: Optional numeric contest id to include in metadata
        fetchspec: Unused hook for future
        contest_string: Substring used to match ranking columns (e.g., 'DEM Mayor', 'DEM Council Member')
        district: Optional district number to filter rows (e.g., 8 means Council District 8).
                  If None, will attempt to infer from contest_string like '... District 08'.
    """
    _log(f"[nycdem_fmt] Reading: {srcfile}")
    # Infer district from contest_string if not provided
    if district is None and contest_string:
        m = re.search(r"district\s*(\d+)", str(contest_string), flags=re.IGNORECASE)
        if m:
            try:
                district = int(m.group(1))
                _log(f"[nycdem_fmt] Inferred district filter from contest_string: {district}")
            except Exception:
                district = None
    
    # Check if srcfile is a ZIP file
    if srcfile.endswith('.zip'):
        return _process_zip_file(srcfile, contestid, contest_string=contest_string, district=district)
    else:
        return _process_excel_file(srcfile, contestid, contest_string=contest_string, district=district)

def _process_zip_file(zip_path, contestid=None, contest_string="Mayor", district=None):
    """Process a ZIP file containing multiple Excel CVR files."""
    _log(f"[nycdem_fmt] Processing ZIP file: {zip_path}")
    
    # Create ABIF model
    abifmodel = get_emptyish_abifmodel()
    title = f"NYC 2025 Democratic Primary - {contest_string}"
    if district is not None:
        title += f" (District {district:02d})"
    abifmodel['metadata']['title'] = title
    abifmodel['metadata']['description'] = f"Ranked-choice voting data for NYC 2025 Democratic Primary {contest_string}"
    if contestid:
        abifmodel['metadata']['contestid'] = contestid
    
    candidate_tokens = {}
    candidate_id_to_name = {}  # Map candidate IDs to real names
    all_ballot_patterns = {}
    total_valid_ballots = 0
    total_empty_ballots = 0
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        excel_files = [f for f in zf.namelist() if f.endswith('.xlsx')]
        _log(f"[nycdem_fmt] Found {len(excel_files)} Excel files in ZIP")
        
        # First, load the candidacy mapping file
        candidacy_files = [f for f in excel_files if 'candidacy' in f.lower() or 'CandidacyID_To_Name' in f]
        if candidacy_files:
            candidacy_file = candidacy_files[0]
            _log(f"[nycdem_fmt] Loading candidacy mapping from: {candidacy_file}")
            try:
                with zf.open(candidacy_file) as f:
                    candidacy_df = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl")
                
                _log(f"[nycdem_fmt] Candidacy file columns: {list(candidacy_df.columns)}", debug=True)
                
                # Look for ID and name columns
                id_col = None
                name_col = None
                for col in candidacy_df.columns:
                    col_lower = str(col).lower()
                    if ('id' in col_lower or 'candidacy' in col_lower) and id_col is None:
                        id_col = col
                    if ('name' in col_lower or 'candidate' in col_lower) and name_col is None:
                        name_col = col
                
                if id_col and name_col:
                    _log(f"[nycdem_fmt] Using ID column '{id_col}' and name column '{name_col}'")
                    for _, row in candidacy_df.iterrows():
                        try:
                            cand_id = str(row[id_col]).strip()
                            cand_name = str(row[name_col]).strip()
                            if cand_id and cand_name and cand_id != 'nan' and cand_name != 'nan':
                                candidate_id_to_name[cand_id] = cand_name
                        except Exception as e:
                            continue
                    _log(f"[nycdem_fmt] Loaded {len(candidate_id_to_name)} candidate name mappings")
                    _log(f"[nycdem_fmt] Sample mappings: {dict(list(candidate_id_to_name.items())[:5])}", debug=True)
                else:
                    _log(f"[nycdem_fmt] Could not identify ID/name columns in candidacy file")
            except Exception as e:
                _log(f"[nycdem_fmt] Error loading candidacy file: {e}")
        
        contest_files = []
        for excel_file in sorted(excel_files):
            if 'candidacy' in excel_file.lower():
                continue
            try:
                with zf.open(excel_file) as f:
                    df_probe = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl", nrows=5)
            except Exception as e:
                _log(f"[nycdem_fmt] Error probing {excel_file}: {e}", debug=True)
                continue

            contest_cols = _match_contest_rank_columns(df_probe.columns, contest_string)
            if contest_cols:
                contest_files.append(excel_file)
                _log(
                    f"[nycdem_fmt] {excel_file}: {len(contest_cols)} matching {contest_string} columns",
                    debug=True,
                )
            else:
                _log(
                    f"[nycdem_fmt] {excel_file}: no {contest_string} ranking data detected in probe",
                    debug=True,
                )

        contest_files = sorted(dict.fromkeys(contest_files))
        _log(
            f"[nycdem_fmt] Identified {len(contest_files)} files with {contest_string} data after probing",
            debug=True,
        )

        if not contest_files:
            _log(f"[nycdem_fmt] No files with {contest_string} data found!")
            abifmodel['metadata']['ballotcount'] = 0
            abifmodel['metadata']['emptyballotcount'] = 0
            return abifmodel
        
        _log(f"[nycdem_fmt] Processing {len(contest_files)} files with {contest_string} data")
        
        # Now process all files that contain contest data
        for excel_file in contest_files:
            _log(f"[nycdem_fmt] Processing: {excel_file}")
            try:
                with zf.open(excel_file) as f:
                    df = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl")
                
                # Process this Excel file, passing the candidate name mapping
                patterns, candidates, valid, empty = _process_dataframe(
                    df,
                    candidate_tokens,
                    candidate_id_to_name,
                    contest_string=contest_string,
                    district=district,
                )
                
                # Merge results
                for pattern, count in patterns.items():
                    all_ballot_patterns[pattern] = all_ballot_patterns.get(pattern, 0) + count
                
                total_valid_ballots += valid
                total_empty_ballots += empty
                
                _log(f"[nycdem_fmt] {excel_file}: {valid} valid ballots, {empty} empty ballots")
                
            except Exception as e:
                _log(f"[nycdem_fmt] Error processing {excel_file}: {e}")
                continue
    
    # Set up candidates in abifmodel
    for token, cand_name in candidate_tokens.items():
        abifmodel['candidates'][token] = cand_name
    
    # Convert ballot patterns to votelines
    for pattern, count in sorted(all_ballot_patterns.items(), key=lambda x: x[1], reverse=True):
        voteline = {
            'qty': count,
            'prefs': {},
            'orderedlist': True
        }
        
        # Add preferences with ranks
        for rank, token in enumerate(pattern, 1):
            voteline['prefs'][token] = {'rank': rank}
        
        abifmodel['votelines'].append(voteline)
    
    # Update metadata
    abifmodel['metadata']['ballotcount'] = total_valid_ballots + total_empty_ballots
    abifmodel['metadata']['emptyballotcount'] = total_empty_ballots
    
    _log(f"[nycdem_fmt] ZIP processing complete:")
    _log(f"[nycdem_fmt] - {len(abifmodel['candidates'])} candidates")
    _log(f"[nycdem_fmt] - {len(abifmodel['votelines'])} unique ballot patterns")
    _log(f"[nycdem_fmt] - {total_valid_ballots} valid ballots, {total_empty_ballots} empty ballots")
    
    return abifmodel

def _process_excel_file(excel_path, contestid=None, contest_string="Mayor", district=None):
    """Process a single Excel CVR file."""
    # Read the Excel file
    df = pd.read_excel(excel_path, engine="openpyxl")
    _log(f"[nycdem_fmt] Columns: {list(df.columns)}")
    _log(f"[nycdem_fmt] Number of rows: {len(df)}")
    
    # Create ABIF model
    abifmodel = get_emptyish_abifmodel()
    title = f"NYC 2025 Democratic Primary - {contest_string}"
    if district is not None:
        title += f" (District {district:02d})"
    abifmodel['metadata']['title'] = title
    abifmodel['metadata']['description'] = f"Ranked-choice voting data for NYC 2025 Democratic Primary {contest_string}"
    if contestid:
        abifmodel['metadata']['contestid'] = contestid
    
    candidate_tokens = {}
    patterns, candidates, valid, empty = _process_dataframe(
        df,
        candidate_tokens,
        {},
        contest_string=contest_string,
        district=district,
    )  # No candidate name mapping for single file
    
    # Set up candidates in abifmodel
    for token, cand_name in candidate_tokens.items():
        abifmodel['candidates'][token] = cand_name
    
    # Convert ballot patterns to votelines
    for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
        voteline = {
            'qty': count,
            'prefs': {},
            'orderedlist': True
        }
        
        # Add preferences with ranks
        for rank, token in enumerate(pattern, 1):
            voteline['prefs'][token] = {'rank': rank}
        
        abifmodel['votelines'].append(voteline)
    
    # Update metadata
    abifmodel['metadata']['ballotcount'] = valid + empty
    abifmodel['metadata']['emptyballotcount'] = empty
    
    _log(f"[nycdem_fmt] Excel processing complete:")
    _log(f"[nycdem_fmt] - {len(abifmodel['candidates'])} candidates")
    _log(f"[nycdem_fmt] - {len(abifmodel['votelines'])} unique ballot patterns")
    _log(f"[nycdem_fmt] - {valid} valid ballots, {empty} empty ballots")
    
    return abifmodel

def _create_readable_token(candidate_name, candidate_id):
    """Create a human-readable token from candidate name and ID."""
    # Extract initials from the candidate name
    words = candidate_name.split()
    initials = ""
    
    for word in words:
        # Skip common prefixes and suffixes
        word_clean = word.strip('.,()[]')
        if word_clean.upper() not in ['JR', 'SR', 'III', 'IV', 'MD', 'ESQ', 'PHD']:
            if word_clean and word_clean[0].isalpha():
                initials += word_clean[0].upper()
    
    # Fallback: if we can't extract good initials, use first few chars
    if not initials or len(initials) < 2:
        # Remove common words and get first letters
        name_clean = candidate_name.replace(' Jr.', '').replace(' Sr.', '').replace(' III', '')
        words = [w for w in name_clean.split() if w.lower() not in ['the', 'of', 'for']]
        initials = ''.join(w[0].upper() for w in words[:3] if w and w[0].isalpha())
    
    # Ensure we have at least 2 characters
    if len(initials) < 2:
        initials = candidate_name[:2].upper().replace(' ', '').replace('.', '')
    
    # Limit to 3-4 initials max to keep tokens reasonable
    if len(initials) > 4:
        initials = initials[:4]
    
    # Combine with candidate ID
    token = f"{initials}{candidate_id}"
    return token

def _normalize_candidate_id(val):
    """Normalize candidate identifiers from ranking values or candidacy mapping.

    - Convert numeric-like values (e.g., 1234, 1234.0, '1234.0') to '1234'
    - Strip whitespace from strings
    - Return None for empty/NaN
    """
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    s = str(val).strip()
    if s == "" or s.lower() == "nan":
        return None
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except Exception:
        pass
    return s


def _process_dataframe(df, candidate_tokens, candidate_id_to_name=None, contest_string="Mayor", district=None):
    """Process a pandas DataFrame to extract voting patterns for a given contest."""
    if candidate_id_to_name is None:
        candidate_id_to_name = {}

    contest_str = str(contest_string or "")

    # If district filtering requested, try to reduce the dataframe to that district
    # But skip this for Council Member district contests where district is in column names
    district_in_columns = False
    if district is not None and re.search(r"council\s*member.*district\s*(\d+)", contest_str, flags=re.IGNORECASE):
        # For Council Member District NN contests, district is encoded in column names, not rows
        district_in_columns = True
        _log(
            f"[nycdem_fmt] District {district} filtering handled by column selection for Council Member contest",
            debug=True,
        )

    if district is not None and not district_in_columns:
        district_cols = [c for c in df.columns if 'district' in str(c).lower()]
        # Prefer columns that explicitly mention council
        district_cols = sorted(
            district_cols,
            key=lambda c: (0 if 'council' in str(c).lower() else 1, str(c).lower()),
        )
        if district_cols:
            dcol = district_cols[0]
            try:
                # Coerce to numeric for robust comparison
                dseries = pd.to_numeric(df[dcol], errors='coerce')
                before = len(df)
                df = df[dseries == float(district)]
                after = len(df)
                _log(
                    f"[nycdem_fmt] Applied district filter {district} on column '{dcol}': {before} -> {after} rows",
                    debug=True,
                )
            except Exception as e:
                _log(f"[nycdem_fmt] Warning: could not filter by district using '{dcol}': {e}")
        else:
            _log(
                f"[nycdem_fmt] District filter requested ({district}) but no '*district*' column found; proceeding without row filter"
            )

    contest_rank_cols = _match_contest_rank_columns(df.columns, contest_str)

    if not contest_rank_cols:
        _log(
            f"[nycdem_fmt] No {contest_str} ranking columns found in this file. Columns sample: {list(df.columns)[:5]}"
        )
        return {}, {}, 0, len(df)

    # Sort ranking columns by choice number for NYC format
    def extract_choice_number(col_name):
        try:
            if "Choice" in str(col_name):
                # Extract number from "DEM {contest_string} Choice 1 of 5"
                parts = str(col_name).split("Choice")[1].split("of")[0].strip()
                return int(parts)
            else:
                # Extract from "{contest_string}_Rank1" format
                return int(str(col_name).replace(f"{contest_str}_Rank", ""))
        except:
            return 999  # Put unparseable columns at the end

    contest_rank_cols = sorted(contest_rank_cols, key=extract_choice_number)
    _log(
        f"[nycdem_fmt] {contest_str} ranking columns: {[str(c)[:50] + '...' if len(str(c)) > 50 else str(c) for c in contest_rank_cols]}",
        debug=True,
    )
    
    # Build candidate list from all unique values in ranking columns
    all_candidate_ids = set()
    for col in contest_rank_cols:
        series = df[col].dropna()
        for v in series:
            nv = _normalize_candidate_id(v)
            if nv is None:
                continue
            if nv.strip().lower() in ('', 'undervote', 'overvote', 'nan', 'no selection', 'blank', 'skipped'):
                continue
            all_candidate_ids.add(nv)
    _log(
        f"[nycdem_fmt] Found {len(all_candidate_ids)} unique candidate IDs: {sorted(list(all_candidate_ids))[:10]}{'...' if len(all_candidate_ids)>10 else ''}",
        debug=True,
    )
    
    # Create candidate mapping with readable tokens
    id_to_token = {}
    # Build a normalized mapping for candidate_id_to_name (keys normalized like ranking values)
    norm_map = {}
    try:
        if candidate_id_to_name:
            for k, v in candidate_id_to_name.items():
                nk = _normalize_candidate_id(k)
                if nk is not None:
                    norm_map[nk] = str(v)
    except Exception:
        norm_map = candidate_id_to_name or {}
    for cand_id in sorted(all_candidate_ids):
        if cand_id not in id_to_token:
            # Get the candidate name if available
            cand_name = norm_map.get(cand_id, cand_id)
            
            # Create readable token
            if cand_name != cand_id:  # We have a real name
                token = _create_readable_token(cand_name, cand_id)
                _log(f"[nycdem_fmt] {cand_id} -> {cand_name} -> {token}", debug=True)
            else:  # No name mapping, use ID with placeholder
                token = f"CAND{cand_id}"
                cand_name = f"Candidate {cand_id}"
                _log(f"[nycdem_fmt] {cand_id} -> {token} (no name mapping)", debug=True)
            
            id_to_token[cand_id] = token
            candidate_tokens[token] = cand_name
    
    _log(
        f"[nycdem_fmt] Final candidate mapping (first 5): {dict(list(candidate_tokens.items())[:5])}",
        debug=True,
    )
    
    # Process ballots - count identical rankings to create votelines
    ballot_patterns = {}
    valid_ballots = 0
    empty_ballots = 0
    
    for idx, row in df.iterrows():
        # Extract rankings for this ballot
        rankings = []
        for col in contest_rank_cols:
            val = row[col]
            nv = _normalize_candidate_id(val)
            if nv is None or nv.strip().lower() in ('', 'undervote', 'overvote', 'nan'):
                continue
            # Look up the token for this candidate ID
            tok = id_to_token.get(nv)
            if tok:
                rankings.append(tok)
        
        # Create pattern key from rankings
        if rankings:
            pattern = tuple(rankings)
            ballot_patterns[pattern] = ballot_patterns.get(pattern, 0) + 1
            valid_ballots += 1
        else:
            empty_ballots += 1
    
    # Diagnostics when nothing valid
    if not ballot_patterns and valid_ballots == 0:
        for col in contest_rank_cols[:3]:
            try:
                sample_vals = list({str(v).strip() for v in df[col].dropna().head(10)})
                _log(f"[nycdem_fmt] Sample values in {col}: {sample_vals}", debug=True)
            except Exception:
                pass
    return ballot_patterns, candidate_tokens, valid_ballots, empty_ballots


def _slugify(s: str) -> str:
    s = str(s)
    s = s.strip()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s)
    return s.strip('-').lower() or "na"


def fanout_zip_to_abif_files(zip_path, outdir, contest_string="Mayor", district=None, group_by=None):
    """Write multiple ABIF files from a NYC ZIP, segmented by Excel file or a grouping column.

    - If group_by == 'precinct', attempts to split each Excel by a column matching /precinct/i or /election\\s*district/i.
    - Otherwise, writes one ABIF per Excel file that contains matching contest columns.
    """
    os.makedirs(outdir, exist_ok=True)
    written = 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        excel_files = [f for f in zf.namelist() if f.endswith('.xlsx')]

        # Identify candidacy mapping for names
        candidate_id_to_name = {}
        candidacy_files = [f for f in excel_files if 'candidacy' in f.lower() or 'CandidacyID_To_Name' in f]
        if candidacy_files:
            try:
                with zf.open(candidacy_files[0]) as f:
                    candidacy_df = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl")
                id_col = None
                name_col = None
                for col in candidacy_df.columns:
                    cl = str(col).lower()
                    if ('id' in cl or 'candidacy' in cl) and id_col is None:
                        id_col = col
                    if ('name' in cl or 'candidate' in cl) and name_col is None:
                        name_col = col
                if id_col and name_col:
                    for _, row in candidacy_df.iterrows():
                        try:
                            cid = str(row[id_col]).strip()
                            cname = str(row[name_col]).strip()
                            if cid and cname and cid != 'nan' and cname != 'nan':
                                candidate_id_to_name[cid] = cname
                        except Exception:
                            pass
            except Exception:
                candidate_id_to_name = {}

        contest_files = []
        for excel_file in sorted(excel_files):
            if 'candidacy' in excel_file.lower():
                continue
            try:
                with zf.open(excel_file) as f:
                    df_probe = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl", nrows=5)
            except Exception as e:
                _log(f"[nycdem_fmt] Error probing {excel_file}: {e}", debug=True)
                continue

            contest_cols = _match_contest_rank_columns(df_probe.columns, contest_string)
            if contest_cols:
                contest_files.append(excel_file)
                _log(
                    f"[nycdem_fmt] {excel_file}: {len(contest_cols)} matching {contest_string} columns",
                    debug=True,
                )
            else:
                _log(
                    f"[nycdem_fmt] {excel_file}: no {contest_string} ranking data detected in probe",
                    debug=True,
                )

        contest_files = sorted(dict.fromkeys(contest_files))
        if not contest_files:
            _log(f"[nycdem_fmt] No files with {contest_string} data found; nothing to fan out")
            return 0

        # Process each file
        for excel_file in contest_files:
            try:
                with zf.open(excel_file) as f:
                    df = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl")
            except Exception as e:
                _log(f"[nycdem_fmt] Skipping {excel_file}: {e}")
                continue

            base = os.path.splitext(os.path.basename(excel_file))[0]

            # Optional group by precinct
            if group_by == 'precinct':
                # First try explicit two-column (AD, ED) grouping
                ad_cols = [c for c in df.columns if re.search(r"\bAD\b|assembly\s*district", str(c), flags=re.IGNORECASE)]
                ed_cols = [c for c in df.columns if re.search(r"\bED\b|election\s*district", str(c), flags=re.IGNORECASE)]
                # Prefer the shortest header (e.g., exact 'AD'/'ED')
                ad_cols = sorted(ad_cols, key=lambda c: len(str(c)))
                ed_cols = sorted(ed_cols, key=lambda c: len(str(c)))
                if ad_cols and ed_cols:
                    adcol, edcol = ad_cols[0], ed_cols[0]
                    pairs = df[[adcol, edcol]].dropna().drop_duplicates().values.tolist()
                    # Normalize and sort pairs for deterministic output
                    def _nz(v):
                        try:
                            if pd.isna(v):
                                return None
                        except Exception:
                            pass
                        try:
                            return int(str(v).strip())
                        except Exception:
                            return str(v).strip()
                    norm_pairs = sorted([( _nz(a), _nz(e) ) for a, e in pairs], key=lambda x: (str(x[0]), str(x[1])))
                    for adval, edval in norm_pairs:
                        try:
                            mask = (df[adcol].astype(str).str.strip() == str(adval)) & (df[edcol].astype(str).str.strip() == str(edval))
                            dfx = df[mask]
                            if dfx.empty:
                                continue
                            candidate_tokens = {}
                            patterns, _, valid, empty = _process_dataframe(
                                dfx, candidate_tokens, candidate_id_to_name,
                                contest_string=contest_string, district=district)
                            if not patterns and valid == 0 and empty == 0:
                                continue
                            abifmodel = get_emptyish_abifmodel()
                            t = f"NYC 2025 Democratic Primary - {contest_string}"
                            if district is not None:
                                t += f" (District {district:02d})"
                            t += f" [AD={adval}, ED={edval}]"
                            abifmodel['metadata']['title'] = t
                            for tok, name in candidate_tokens.items():
                                abifmodel['candidates'][tok] = name
                            for pattern, count in patterns.items():
                                voteline = {'qty': count, 'prefs': {}, 'orderedlist': True}
                                for rank, tok in enumerate(pattern, 1):
                                    voteline['prefs'][tok] = {'rank': rank}
                                abifmodel['votelines'].append(voteline)
                            abifmodel['metadata']['ballotcount'] = valid + empty
                            abifmodel['metadata']['emptyballotcount'] = empty
                            # Zero-pad AD/ED when numeric: AD=2 -> 02, ED=45 -> 045
                            def _pad(v, width):
                                try:
                                    return str(int(v)).zfill(width)
                                except Exception:
                                    return _slugify(v)
                            ad_str = _pad(adval, 2)
                            ed_str = _pad(edval, 3)
                            outname = f"{base}__precinct-ad-{ad_str}-ed-{ed_str}.abif"
                            outpath = os.path.join(outdir, outname)
                            with open(outpath, 'w') as outf:
                                outf.write(abiflib.convert_jabmod_to_abif(abifmodel))
                            written += 1
                        except Exception as e:
                            _log(f"[nycdem_fmt] AD/ED fanout error in {excel_file} for AD={adval}, ED={edval}: {e}")
                    continue  # next excel_file

                # Next try single combined precinct-like column
                precinct_cols = [c for c in df.columns if re.search(r"precinct|election\s*district", str(c), flags=re.IGNORECASE)]
                if precinct_cols:
                    pcol = precinct_cols[0]
                    values = sorted(v for v in df[pcol].dropna().unique())
                    for val in values:
                        try:
                            dfx = df[df[pcol] == val]
                            candidate_tokens = {}
                            patterns, _, valid, empty = _process_dataframe(
                                dfx, candidate_tokens, candidate_id_to_name,
                                contest_string=contest_string, district=district)
                            if not patterns and valid == 0 and empty == 0:
                                continue
                            abifmodel = get_emptyish_abifmodel()
                            t = f"NYC 2025 Democratic Primary - {contest_string}"
                            if district is not None:
                                t += f" (District {district:02d})"
                            t += f" [{pcol}={val}]"
                            abifmodel['metadata']['title'] = t
                            for tok, name in candidate_tokens.items():
                                abifmodel['candidates'][tok] = name
                            for pattern, count in patterns.items():
                                voteline = {'qty': count, 'prefs': {}, 'orderedlist': True}
                                for rank, tok in enumerate(pattern, 1):
                                    voteline['prefs'][tok] = {'rank': rank}
                                abifmodel['votelines'].append(voteline)
                            abifmodel['metadata']['ballotcount'] = valid + empty
                            abifmodel['metadata']['emptyballotcount'] = empty
                            outname = f"{base}__{_slugify(pcol)}-{_slugify(val)}.abif"
                            outpath = os.path.join(outdir, outname)
                            with open(outpath, 'w') as outf:
                                outf.write(abiflib.convert_jabmod_to_abif(abifmodel))
                            written += 1
                        except Exception as e:
                            _log(f"[nycdem_fmt] Precinct fanout error in {excel_file} for {pcol}={val}: {e}")
                    continue  # next excel_file

            # Default: one file per Excel
            candidate_tokens = {}
            patterns, _, valid, empty = _process_dataframe(
                df, candidate_tokens, candidate_id_to_name,
                contest_string=contest_string, district=district)
            if not patterns and valid == 0 and empty == 0:
                continue
            abifmodel = get_emptyish_abifmodel()
            t = f"NYC 2025 Democratic Primary - {contest_string}"
            if district is not None:
                t += f" (District {district:02d})"
            t += f" [{base}]"
            abifmodel['metadata']['title'] = t
            for tok, name in candidate_tokens.items():
                abifmodel['candidates'][tok] = name
            for pattern, count in patterns.items():
                voteline = {'qty': count, 'prefs': {}, 'orderedlist': True}
                for rank, tok in enumerate(pattern, 1):
                    voteline['prefs'][tok] = {'rank': rank}
                abifmodel['votelines'].append(voteline)
            abifmodel['metadata']['ballotcount'] = valid + empty
            abifmodel['metadata']['emptyballotcount'] = empty
            outname = f"{base}.abif"
            outpath = os.path.join(outdir, outname)
            with open(outpath, 'w') as outf:
                outf.write(abiflib.convert_jabmod_to_abif(abifmodel))
            written += 1

    _log(f"[nycdem_fmt] Fanout wrote {written} ABIF files to {outdir}")
    return written
