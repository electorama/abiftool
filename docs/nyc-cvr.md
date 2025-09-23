# NYC CVR Data Format and Processing

## Data Source: 2025_Primary_CVR_2025-07-17.zip

**Source**: NYC Board of Elections cast vote record for June 24, 2025 Democratic Primary  
**Format**: ZIP containing multiple Excel (.xlsx) files with ranked-choice voting data  
**Size**: ~140MB compressed, ~500MB uncompressed

### ZIP Contents Structure

```
2025P2V1_ELE1.xlsx           # Primary 2, Election 1 (main contests)
2025P3V1_ELE1.xlsx           # Primary 3, Election 1  
2025P4V1_ELE1.xlsx           # Primary 4, Election 1
2025P5V1_ELE1.xlsx           # Primary 5, Election 1
...                          # Additional primary/election combinations
CandidacyID_To_Name.xlsx     # Candidate ID → name mapping
```

### Excel File Structure

Each Excel file contains:
- **Ballot identification**: Columns for district, precinct, batch info
- **Contest ranking columns**: Named like `DEM Mayor Choice 1 of 5`, `DEM Mayor Choice 2 of 5`, etc.
- **Candidate data**: Numeric IDs corresponding to CandidacyID_To_Name.xlsx

### Key Contests

- **Citywide**: Mayor, Public Advocate, Comptroller
- **Borough-level**: Borough Presidents (5 boroughs)  
- **District-level**: Council Members (51 districts)

### Processing Flow (fetchmgr.py/abiflib)

1. **ZIP extraction**: Extract Excel files in memory
2. **Contest detection**: Match column patterns like `DEM {contest} Choice N of M`
3. **Candidate mapping**: Join with CandidacyID_To_Name.xlsx for readable names
4. **District filtering**: Filter rows by Council District, Election District, etc.
5. **Ballot parsing**: Convert ranking columns to ABIF preference ordering
6. **ABIF generation**: Output `.abif` files with contest metadata and vote tallies

### Performance Characteristics

- **Processing time**: ~5-30 minutes per contest (current implementation)
- **Memory usage**: ~200MB peak per Excel file
- **Bottleneck**: Redundant ZIP reads for each contest (O(N²) behavior)
- **Optimization target**: Single-pass processing for all contests