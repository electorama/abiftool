# St. Louis CVR to ABIF Conversion Design

## Overview

Design document for adding St. Louis Cast Vote Record (CVR) support to abiftool, enabling conversion of Hart Verity XML ballot data to ABIF format for analysis with abiflib.

Current status: fetchmgr now downloads the official zip and can emit stub ABIF files (metadata only) for the target contests. Full XML parsing and conversion will follow in `abiflib`/`abiftool.py`.

## St. Louis 2025 Election Data

### Available Elections
- **Mayor**: 34,945 ballots, 4 candidates (Mike Butler, Tishaura Jones, Cara Spencer, Andrew Jones)
- **Comptroller**: 33,667 ballots, 3 candidates (Donna Baringer, Darlene Green, Celeste Metcalf)
- **Ward 3 Alderman**: 1,624 ballots, 3 candidates (Dallas Adams, Shane Cohn, Inez Bordeaux)
- **Ward 11 Alderman**: 1,152 ballots, 3 candidates (Melinda Long, Rebecca McCloud, Laura Keys)

### CVR Data Format

**Source**: Hart Verity XML files in `CVRExport-8-27-2025.zip`
*** See https://github.com/fsargent/approval-vote/raw/refs/heads/main/st-louis-cvr/data/CVRExport-8-27-2025.zip
**File naming**: `{batch}_{cvr-guid}.xml` (e.g., `1_00025c89-7b62-498d-b583-fac94790fd84.xml`)

## XML Structure Analysis

### Individual Ballot XML Schema
```xml
<CastVoteRecord xmlns="http://tempuri.org/CVRDesign.xsd">
  <CvrGuid>00025c89-7b62-498d-b583-fac94790fd84</CvrGuid>
  <BatchSequence>1</BatchSequence>
  <SheetNumber>123</SheetNumber>
  <IsBlank>false</IsBlank>
  <PrecinctSplit>
    <Name>Ward 03 Precinct 05</Name>
    <Id>030005</Id>
  </PrecinctSplit>
  <Contests>
    <Contest>
      <Name>MAYOR</Name>
      <Id>001</Id>
      <Undervotes>0</Undervotes>
      <Options>
        <Option>
          <Name>CARA SPENCER</Name>
          <Id>001001</Id>
          <Value>1</Value>
        </Option>
        <Option>
          <Name>TISHAURA O. JONES</Name>
          <Id>001002</Id>
          <Value>1</Value>
        </Option>
      </Options>
    </Contest>
    <Contest>
      <Name>COMPTROLLER</Name>
      <Id>002</Id>
      <!-- ... -->
    </Contest>
  </Contests>
</CastVoteRecord>
```

### Key Data Elements
- **Ballot ID**: `CvrGuid` (unique ballot identifier)
- **Location**: `PrecinctSplit/Name` (e.g., "Ward 03 Precinct 05")
- **Contest**: `Contest/Name` ("MAYOR", "COMPTROLLER", etc.)
- **Candidates**: `Option/Name` (candidate name)
- **Selection**: `Option/Value` (1 = approved, 0 = not selected)

## ABIF Conversion Design

### Data Transformation Flow

```
Hart Verity XML → jabmod (internal abiflib model) → ABIF (output)
```

Note: abiflib should parse and normalize the St. Louis CVR directly into jabmod (the internal JSON ABIF model). ABIF should be produced only as an output representation by calling `convert_jabmod_to_abif`, keeping jabmod as the authoritative in-memory structure for downstream analyses and report generation.

### 0. Fetch + Stub Creation

- Fetchspec: `abiftool/fetchspecs/stl-elections-2025.fetchspec.json` (one web entry per contest; mirrors SF specs)
- Running `fetchmgr.py` downloads the zip and writes placeholder ABIF files with metadata (no ballots yet): `localabif/stlouis/*.abif`.
- These stubs include `source_zip`, `contestid`, `contestslug`, `contest_name`, and `description` where provided.

### 1. XML Parser Module (planned)

```python
class StLouisCvrParser:
    def parse_zip_file(self, zip_path: str) -> Iterator[Ballot]:
        """Extract and parse all XML files from CVR zip."""

    def parse_xml_file(self, xml_content: str) -> Ballot:
        """Parse single XML file to Ballot object."""

    def normalize_contest_name(self, contest_name: str) -> str:
        """Convert 'MAYOR' → 'mayor', 'ALDERMAN - WARD 3' → 'alderman-ward3'"""
```

### 2. Ballot Data Model (planned)

```python
@dataclass
class Ballot:
    ballot_id: str              # CvrGuid
    precinct: str              # PrecinctSplit/Name
    contests: Dict[str, Contest] # contest_name → Contest

@dataclass
class Contest:
    contest_name: str          # Normalized name
    contest_id: str            # Hart Verity ID
    candidates: List[str]      # Approved candidate names
    undervotes: int            # Number of undervotes
```

## Data Quality Considerations

### Challenges
1. **Multi-contest ballots**: Each XML contains multiple contests
2. **Name normalization**: "CARA SPENCER" vs "Cara Spencer"
3. **Contest mapping**: "MAYOR" → "mayor", "ALDERMAN - WARD 3" → "alderman-ward3"
4. **Undervotes**: Handle ballots with no selections in a contest

### Validation Points
- Total ballot counts match between CVR and aggregated data
- Candidate vote totals match per contest
- Co-approval patterns consistent with matrix data

## Expected Outputs

### ABIF Files Generated
- Stub phase (in place now): files are created with metadata only (no ballots)
  - `stl-2025-mayor.abif`
  - `stl-2025-comptroller.abif`
  - `stl-2025-alderman-ward3.abif`
  - `stl-2025-alderman-ward11.abif`
- Full conversion phase (planned): same filenames populated with full ballots and candidate lists

### Metadata Preservation
- Precinct information for geographic analysis
- Ballot sequence numbers for audit trails
- Undervote counts for completion analysis

## Technical Requirements

### Dependencies
- For fetch/stub phase: existing `fetchmgr.py` (uses `requests`), no parser required
- For full conversion phase:
  - `lxml` or `xml.etree.ElementTree` for XML parsing
  - `abiflib` for ABIF format handling
  - `click` for CLI interface
  - `tqdm` for progress tracking
