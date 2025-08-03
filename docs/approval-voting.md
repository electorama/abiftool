# Approval Voting in abiflib

## Design Overview

### Core Principle
Approval voting in abiflib follows the same architectural pattern as other voting methods (FPTP, IRV, STAR, etc.) by operating on the jabmod (JSON ABIF model) structure defined in `core.py`.

### Input Processing
The `approval_tally.py` module will handle two distinct scenarios:

1. **Native Approval Ballots**: When votelines contain explicit approval data:
   * Ratings of 0 or 1, indicating disapproval/approval respectively
   * Equal-ranked candidates with approval scores (using `=` delimiter)
   * Clear binary approval/disapproval patterns
2. **Simulated Approval from Ranked Ballots**: When only ranked preferences are available, convert using strategic simulation based on viability analysis

### Function Architecture
Following the pattern established by `fptp_tally.py`:

```python
def approval_result_from_abifmodel(abifmodel, method='auto'):
    """Calculate approval voting results from jabmod."""
    # Returns approval counts, winners, and metadata

def get_approval_report(abifmodel, method='auto'):
    """Generate human-readable approval voting report."""
    # Returns formatted text report
```

## Approval Ballot Format

### Native Approval Syntax
Approved candidates are listed with equal rank and score of 1:
```
3:candA=candB/1>candC/0
```
Or using the delimiter syntax:
```
3:candA=candB>candC
```

### Score-based Approval
Using explicit 0/1 scores:
```
5:candA/1>candB/1>candC/0
```

## Strategic Simulation Algorithm

When converting ranked ballots to approval votes, use the sophisticated algorithm:

1. **Calculate FPTP results** using `FPTP_result_from_abifmodel()`
2. **Determine viable candidates** using iterative Droop quota analysis
3. **Calculate per-ballot VCM** (viable-candidate-maximum): `floor((viable_count + 1) / 2)`
4. **Apply approval strategy**: For each ballot, approve candidates ranked above the lowest-ranked viable candidate among the voter's top VCM choices

### Detailed Algorithm Steps

#### Step 1: FPTP Analysis for Viability
```python
# Get first-choice vote totals for all candidates
fptp_results = FPTP_result_from_abifmodel(abifmodel)
total_valid_votes = fptp_results['total_votes_recounted']
```

#### Step 2: Determine Number of Viable Candidates
```python
# Iterative Droop quota analysis to determine viable candidate count
sorted_candidates = sorted(fptp_results['toppicks'].items(),
                          key=lambda x: x[1], reverse=True)
frontrunner_votes = sorted_candidates[0][1]  # Top candidate's vote total

# Start with hypothetical 1 seat, increment until frontrunner CAN meet quota
S = 1
number_of_viable_candidates = 1  # Default minimum

while S <= len(sorted_candidates):
    # Calculate Droop quota for S seats: floor(total_votes / (S + 1)) + 1
    quota = (total_valid_votes // (S + 1)) + 1

    if frontrunner_votes >= quota:
        # Frontrunner can win with S viable candidates
        number_of_viable_candidates = S
        break
    else:
        # Frontrunner can't win with S candidates, try more candidates
        S += 1

# Create list of top N candidates based on first-place votes
viable_candidates = []
for i in range(min(number_of_viable_candidates, len(sorted_candidates))):
    candidate, votes = sorted_candidates[i]
    if candidate is not None:
        viable_candidates.append(candidate)
```

#### Step 3: Calculate Viable-Candidate-Maximum (VCM)
```python
# Strategic approval limit per ballot
vcm = (len(viable_candidates) + 1) // 2
```

#### Step 4: Per-Ballot Approval Strategy
For each ballot, apply this strategic logic:

```python
for each ballot:
    # Get voter's ranked preferences
    ranked_prefs = sort_candidates_by_rank(ballot['prefs'])

    # 1. Identify the top VCM viable candidates on THIS ballot
    vcm_viable_candidates_on_ballot = []
    for candidate, rank in ranked_prefs:
        if candidate in viable_candidates:
            vcm_viable_candidates_on_ballot.append(candidate)
            if len(vcm_viable_candidates_on_ballot) == vcm:
                break

    # 2. Find the lowest-ranked candidate in that specific group
    if not vcm_viable_candidates_on_ballot:
        # No viable candidates were ranked, so no approvals
        approvals = []
    else:
        # The cutoff candidate is the last one in our list
        cutoff_candidate = vcm_viable_candidates_on_ballot[-1]

        # 3. Approve all candidates ranked at or above the cutoff
        approvals = []
        cutoff_found = False
        for candidate, rank in ranked_prefs:
            approvals.append(candidate)
            if candidate == cutoff_candidate:
                cutoff_found = True
                break

        if not cutoff_found:
            # This should not happen if logic is correct, but as safeguard
            approvals = vcm_viable_candidates_on_ballot

    # Apply approvals to vote counts
    for candidate in approvals:
        approval_counts[candidate] += ballot['qty']
```

### Algorithm Rationale

**Viability Assessment**: Uses iterative Droop quota analysis to determine how many candidates are truly competitive. A weak frontrunner (low %) indicates many viable competitors; a strong frontrunner (high %) indicates fewer viable competitors.

**VCM Calculation**: `floor((viable_count + 1) / 2)` ensures voters approve roughly half of viable candidates, balancing expression of preferences with strategic effectiveness.

**Strategic Threshold**: Voters identify their top VCM viable candidates, then approve all candidates ranked at or above the lowest-ranked of those VCM viable candidates. This includes both viable and non-viable candidates in the approval range, simulating rational approval behavior that maximizes utility while remaining strategically competitive.

**Example**: If frontrunner has 26% of votes:
- S=1: quota = floor(100/2) + 1 = 51. Since 26 < 51, try more candidates.
- S=2: quota = floor(100/3) + 1 = 34. Since 26 < 34, try more candidates.
- S=3: quota = floor(100/4) + 1 = 26. Since 26 ≥ 26, stop.
- Result: **4 viable candidates** (top 4 by FPTP votes)
- VCM = floor((4+1)/2) = 2 approvals per voter

## Method Parameter
The `method` parameter controls behavior:
- `'auto'`: Detect native approval vs. ranked ballots automatically
- `'native'`: Treat as native approval ballots only
- `'simulate'`: Force strategic simulation from ranked ballots
- `'droop_strategic'`: Use Droop quota strategic simulation (default for simulate)

## Detection Logic
```python
def has_approval_data(abifmodel):
    """Detect if jabmod contains native approval data."""
    # Check for binary 0/1 scores, equal rankings with approval indicators
    # Look for patterns like: candA=candB/1>candC/0

def has_only_rankings(abifmodel):
    """Detect if jabmod contains only ranked preferences."""
    # Check for rank-only data without scores or binary patterns

def detect_approval_method(abifmodel):
    """Auto-detect appropriate approval calculation method."""
    # Returns 'native' or 'simulate' based on ballot content
```

## Tennessee Example - Native Approval Election

### Background
Based on the classic Tennessee capitol selection example, with approval patterns derived from geographic proximity. This demonstrates native approval ballot parsing where voters strategically approve candidates within reasonable distance.

### Voter Distribution
Uses the same geographic population distribution as other Tennessee examples:
- 42 voters total (21+21+13+13+8+4+3+9+8 from different regions)
- Approval decisions based on distance/accessibility to each city

### ABIF Format (from tennessee-example-approval.abif)
```
{"version":"0.1"}
{"title":"Capitol of Tennessee Mock Approval Election"}
{"description": "Hypothetical example of selecting capitol of Tennessee..."}
{"max_rating": 1}
{"min_rating": 0}
=Memph:[Memphis, TN]
=Nash:[Nashville, TN]
=Chat:[Chattanooga, TN]
=Knox:[Knoxville, TN]
# -------------------------
21:Memph/1
21:Memph/1=Nash/1
13:Nash/1
13:Nash/1=Chat/1
8:Chat/1
4:Chat/1=Knox/1
3:Chat/1=Nash/1
9:Knox/1
8:Knox/1=Chat/1
```

### Expected Results
Manual calculation of approval totals:
- **Memphis**: 42 approvals (21+21)
- **Nashville**: 50 approvals (21+13+13+3)
- **Chattanooga**: 36 approvals (13+4+3+8+8)
- **Knoxville**: 21 approvals (4+9+8)

**Winner**: Nashville with 50 approvals (50/100 = 50% approval rate)

## Integration Points

### abiftool Integration
Add `approval` modifier to `abiftool.py`:
```bash
abiftool --modifier approval testdata/mock-elections/tennessee-example-approval.abif
```

### awt Integration
Add approval results to the web interface by:
1. Adding approval calculation to `conduits.py`
2. Creating approval HTML snippet template
3. Adding 'approval' to result types in `awt.py`

## File Structure
```
abiflib/
├── approval_tally.py          # New approval voting module
├── fptp_tally.py             # Used for strategic simulation
├── core.py                   # jabmod foundation (unchanged)
└── __init__.py               # Add approval_tally import

testdata/mock-elections/
└── tennessee-example-approval.abif   # Native approval test case

docs/
└── approval-voting.md        # This document
```

## Dependencies
- `fptp_tally.py`: For FPTP results in strategic simulation
- `core.py`: For jabmod structure and utilities
- Standard abiflib utilities for output formatting

This design maintains architectural consistency while properly handling both native approval ballots and strategic simulation scenarios.
