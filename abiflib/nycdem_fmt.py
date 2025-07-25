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

def convert_nycdem_to_jabmod(srcfile, contestid=None, fetchspec=None):
    """Convert NYC CVR Excel file(s) to ABIF jabmod, focusing on Mayor's race."""
    print(f"[nycdem_fmt] Reading: {srcfile}")
    
    # Check if srcfile is a ZIP file
    if srcfile.endswith('.zip'):
        return _process_zip_file(srcfile, contestid)
    else:
        return _process_excel_file(srcfile, contestid)

def _process_zip_file(zip_path, contestid=None):
    """Process a ZIP file containing multiple Excel CVR files."""
    print(f"[nycdem_fmt] Processing ZIP file: {zip_path}")
    
    # Create ABIF model
    abifmodel = get_emptyish_abifmodel()
    abifmodel['metadata']['title'] = "NYC 2025 Democratic Primary - Mayor's Race"
    abifmodel['metadata']['description'] = "Ranked-choice voting data for NYC 2025 Democratic Primary Mayor's race"
    if contestid:
        abifmodel['metadata']['contestid'] = contestid
    
    candidate_tokens = {}
    candidate_id_to_name = {}  # Map candidate IDs to real names
    all_ballot_patterns = {}
    total_valid_ballots = 0
    total_empty_ballots = 0
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        excel_files = [f for f in zf.namelist() if f.endswith('.xlsx')]
        print(f"[nycdem_fmt] Found {len(excel_files)} Excel files in ZIP")
        
        # First, load the candidacy mapping file
        candidacy_files = [f for f in excel_files if 'candidacy' in f.lower() or 'CandidacyID_To_Name' in f]
        if candidacy_files:
            candidacy_file = candidacy_files[0]
            print(f"[nycdem_fmt] Loading candidacy mapping from: {candidacy_file}")
            try:
                with zf.open(candidacy_file) as f:
                    candidacy_df = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl")
                
                print(f"[nycdem_fmt] Candidacy file columns: {list(candidacy_df.columns)}")
                
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
                    print(f"[nycdem_fmt] Using ID column '{id_col}' and name column '{name_col}'")
                    for _, row in candidacy_df.iterrows():
                        try:
                            cand_id = str(row[id_col]).strip()
                            cand_name = str(row[name_col]).strip()
                            if cand_id and cand_name and cand_id != 'nan' and cand_name != 'nan':
                                candidate_id_to_name[cand_id] = cand_name
                        except Exception as e:
                            continue
                    print(f"[nycdem_fmt] Loaded {len(candidate_id_to_name)} candidate name mappings")
                    print(f"[nycdem_fmt] Sample mappings: {dict(list(candidate_id_to_name.items())[:5])}")
                else:
                    print(f"[nycdem_fmt] Could not identify ID/name columns in candidacy file")
            except Exception as e:
                print(f"[nycdem_fmt] Error loading candidacy file: {e}")
        
        # First, scan files to find which ones have Mayor data (limit to first few from each primary)
        mayor_files = []
        tested_files = []
        
        # Check one file from each primary (P1, P2, P3, P4, P5) to find Mayor data
        for primary in ['P2', 'P3', 'P4', 'P5']:  # Skip P1 since we know it doesn't have Mayor data
            test_file = f"2025{primary}V1_ELE1.xlsx"
            if test_file in excel_files:
                tested_files.append(test_file)
                try:
                    with zf.open(test_file) as f:
                        # Just read the first few rows to check column names
                        df = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl", nrows=5)
                    
                    print(f"[nycdem_fmt] {test_file} columns (first 10): {list(df.columns)[:10]}")
                    
                    # Check for Mayor columns with different patterns
                    mayor_cols_old = [col for col in df.columns if col.startswith("Mayor_Rank")]
                    mayor_cols_nyc = [col for col in df.columns if "DEM Mayor Choice" in str(col)]
                    mayor_cols = mayor_cols_old + mayor_cols_nyc
                    
                    mayor_like_cols = [col for col in df.columns if 'mayor' in str(col).lower()]
                    
                    print(f"[nycdem_fmt] {test_file}: {len(mayor_cols)} Mayor columns ({len(mayor_cols_old)} old format, {len(mayor_cols_nyc)} NYC format)")
                    if mayor_like_cols:
                        print(f"[nycdem_fmt] Mayor-like columns: {[str(c)[:40] + '...' if len(str(c)) > 40 else str(c) for c in mayor_like_cols[:3]]}")
                    
                    if mayor_cols:
                        print(f"[nycdem_fmt] Found Mayor data in primary {primary}: {test_file} ({len(mayor_cols)} columns)")
                        # Add all files from this primary
                        primary_files = [f for f in excel_files if f.startswith(f"2025{primary}") and 'candidacy' not in f.lower()]
                        mayor_files.extend(primary_files)
                    else:
                        print(f"[nycdem_fmt] No Mayor ranking data in primary {primary}: {test_file}")
                except Exception as e:
                    print(f"[nycdem_fmt] Error scanning {test_file}: {e}")
                    continue
        
        if not mayor_files:
            print("[nycdem_fmt] No files with Mayor data found!")
            abifmodel['metadata']['ballotcount'] = 0
            abifmodel['metadata']['emptyballotcount'] = 0
            return abifmodel
        
        print(f"[nycdem_fmt] Processing {len(mayor_files)} files with Mayor data")
        
        # Now process all files that contain Mayor data
        for excel_file in mayor_files:
            print(f"[nycdem_fmt] Processing: {excel_file}")
            try:
                with zf.open(excel_file) as f:
                    df = pd.read_excel(io.BytesIO(f.read()), engine="openpyxl")
                
                # Process this Excel file, passing the candidate name mapping
                patterns, candidates, valid, empty = _process_dataframe(df, candidate_tokens, candidate_id_to_name)
                
                # Merge results
                for pattern, count in patterns.items():
                    all_ballot_patterns[pattern] = all_ballot_patterns.get(pattern, 0) + count
                
                total_valid_ballots += valid
                total_empty_ballots += empty
                
                print(f"[nycdem_fmt] {excel_file}: {valid} valid ballots, {empty} empty ballots")
                
            except Exception as e:
                print(f"[nycdem_fmt] Error processing {excel_file}: {e}")
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
    
    print(f"[nycdem_fmt] ZIP processing complete:")
    print(f"[nycdem_fmt] - {len(abifmodel['candidates'])} candidates")
    print(f"[nycdem_fmt] - {len(abifmodel['votelines'])} unique ballot patterns")
    print(f"[nycdem_fmt] - {total_valid_ballots} valid ballots, {total_empty_ballots} empty ballots")
    
    return abifmodel

def _process_excel_file(excel_path, contestid=None):
    """Process a single Excel CVR file."""
    # Read the Excel file
    df = pd.read_excel(excel_path, engine="openpyxl")
    print(f"[nycdem_fmt] Columns: {list(df.columns)}")
    print(f"[nycdem_fmt] Number of rows: {len(df)}")
    
    # Create ABIF model
    abifmodel = get_emptyish_abifmodel()
    abifmodel['metadata']['title'] = "NYC 2025 Democratic Primary - Mayor's Race"
    abifmodel['metadata']['description'] = "Ranked-choice voting data for NYC 2025 Democratic Primary Mayor's race"
    if contestid:
        abifmodel['metadata']['contestid'] = contestid
    
    candidate_tokens = {}
    patterns, candidates, valid, empty = _process_dataframe(df, candidate_tokens, {})  # No candidate name mapping for single file
    
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
    
    print(f"[nycdem_fmt] Excel processing complete:")
    print(f"[nycdem_fmt] - {len(abifmodel['candidates'])} candidates")
    print(f"[nycdem_fmt] - {len(abifmodel['votelines'])} unique ballot patterns")
    print(f"[nycdem_fmt] - {valid} valid ballots, {empty} empty ballots")
    
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

def _process_dataframe(df, candidate_tokens, candidate_id_to_name=None):
    """Process a pandas DataFrame to extract mayor's race voting patterns."""
    if candidate_id_to_name is None:
        candidate_id_to_name = {}
    
    # Find Mayor ranking columns - NYC uses pattern like "DEM Mayor Choice X of Y"
    mayor_rank_cols = []
    
    # Look for both patterns: "Mayor_Rank" and "DEM Mayor Choice"
    for col in df.columns:
        col_str = str(col)
        if col_str.startswith("Mayor_Rank") or ("DEM Mayor Choice" in col_str and "Mayor" in col_str):
            mayor_rank_cols.append(col)
    
    if not mayor_rank_cols:
        print("[nycdem_fmt] No Mayor ranking columns found in this file")
        return {}, {}, 0, len(df)
    
    # Sort ranking columns by choice number for NYC format
    def extract_choice_number(col_name):
        try:
            if "Choice" in str(col_name):
                # Extract number from "DEM Mayor Choice 1 of 5"
                parts = str(col_name).split("Choice")[1].split("of")[0].strip()
                return int(parts)
            else:
                # Extract from "Mayor_Rank1" format
                return int(str(col_name).replace("Mayor_Rank", ""))
        except:
            return 999  # Put unparseable columns at the end
    
    mayor_rank_cols = sorted(mayor_rank_cols, key=extract_choice_number)
    print(f"[nycdem_fmt] Mayor ranking columns: {[str(c)[:50] + '...' if len(str(c)) > 50 else str(c) for c in mayor_rank_cols]}")
    
    # Build candidate list from all unique values in ranking columns
    all_candidate_ids = set()
    for col in mayor_rank_cols:
        candidates_in_col = df[col].dropna().astype(str).str.strip()
        # Filter out non-candidate values
        candidates_in_col = candidates_in_col[
            ~candidates_in_col.str.lower().isin(['', 'undervote', 'overvote', 'nan'])
        ]
        all_candidate_ids.update(candidates_in_col)
    
    print(f"[nycdem_fmt] Found {len(all_candidate_ids)} unique candidate IDs: {sorted(all_candidate_ids)}")
    
    # Create candidate mapping with readable tokens
    id_to_token = {}
    for cand_id in sorted(all_candidate_ids):
        if cand_id not in id_to_token:
            # Get the candidate name if available
            cand_name = candidate_id_to_name.get(cand_id, cand_id)
            
            # Create readable token
            if cand_name != cand_id:  # We have a real name
                token = _create_readable_token(cand_name, cand_id)
                print(f"[nycdem_fmt] {cand_id} -> {cand_name} -> {token}")
            else:  # No name mapping, use ID with placeholder
                token = f"CAND{cand_id}"
                cand_name = f"Candidate {cand_id}"
                print(f"[nycdem_fmt] {cand_id} -> {token} (no name mapping)")
            
            id_to_token[cand_id] = token
            candidate_tokens[token] = cand_name
    
    print(f"[nycdem_fmt] Final candidate mapping (first 5): {dict(list(candidate_tokens.items())[:5])}")
    
    # Process ballots - count identical rankings to create votelines
    ballot_patterns = {}
    valid_ballots = 0
    empty_ballots = 0
    
    for idx, row in df.iterrows():
        # Extract rankings for this ballot
        rankings = []
        for col in mayor_rank_cols:
            val = row[col]
            if pd.isna(val):
                continue
            val_str = str(val).strip()
            if val_str.lower() in ('', 'undervote', 'overvote', 'nan'):
                continue
            # Look up the token for this candidate ID
            if val_str in id_to_token:
                rankings.append(id_to_token[val_str])
        
        # Create pattern key from rankings
        if rankings:
            pattern = tuple(rankings)
            ballot_patterns[pattern] = ballot_patterns.get(pattern, 0) + 1
            valid_ballots += 1
        else:
            empty_ballots += 1
    
    return ballot_patterns, candidate_tokens, valid_ballots, empty_ballots
