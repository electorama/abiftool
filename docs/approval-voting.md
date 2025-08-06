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

When converting ranked ballots to approval votes, use this algorithm:

1. **Calculate FPTP results** using `FPTP_result_from_abifmodel()`
2. **Determine viable candidates** using iterative Droop quota analysis
3. **Calculate per-ballot viable-candidate-maximum**: `floor((viable_count + 1) / 2)`
   This is the number of viable candidates that show up on a ballot before we assume all candidates listed are not viable.
4. **Apply approval strategy**: For each ballot, approve candidates ranked
   above the lowest-ranked viable candidate among the voter's top viable-candidate-maximum choices.

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

#### Step 3: Calculate Viable-Candidate-Maximum
```python
# Strategic approval limit per ballot
viable_candidate_maximum = (len(viable_candidates) + 1) // 2
```

#### Step 4: Per-Ballot Approval Strategy
For each ballot, apply this strategic logic:

```python
for each ballot:
    # Get voter's ranked preferences
    ranked_prefs = sort_candidates_by_rank(ballot['prefs'])

    # 1. Identify the top viable-candidate-maximum viable candidates on THIS ballot
    viable_candidate_maximum_on_ballot = []
    for candidate, rank in ranked_prefs:
        if candidate in viable_candidates:
            viable_candidate_maximum_on_ballot.append(candidate)
            if len(viable_candidate_maximum_on_ballot) == viable_candidate_maximum:
                break

    # 2. Find the lowest-ranked candidate in that specific group
    if not viable_candidate_maximum_on_ballot:
        # No viable candidates were ranked, so no approvals
        approvals = []
    else:
        # The cutoff candidate is the last one in our list
        cutoff_candidate = viable_candidate_maximum_on_ballot[-1]

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
            approvals = viable_candidate_maximum_on_ballot    # Apply approvals to vote counts
    for candidate in approvals:
        approval_counts[candidate] += ballot['qty']
```

### Algorithm Rationale

**Viability Assessment**: Uses iterative Droop quota analysis to determine how many candidates are truly competitive. A weak frontrunner (low %) indicates many viable competitors; a strong frontrunner (high %) indicates fewer viable competitors.

**Viable-Candidate-Maximum Calculation**: `floor((viable_count + 1) / 2)` ensures voters approve roughly half of viable candidates, balancing expression of preferences with strategic effectiveness.

**Strategic Threshold**: Voters identify their top viable-candidate-maximum viable candidates, then approve all candidates ranked at or above the lowest-ranked of those viable candidates. This includes both viable and non-viable candidates in the approval range, simulating rational approval behavior that maximizes utility while remaining strategically competitive.

**Example**: If frontrunner has 26% of votes:
- S=1: quota = floor(100/2) + 1 = 51. Since 26 < 51, try more candidates.
- S=2: quota = floor(100/3) + 1 = 34. Since 26 < 34, try more candidates.
- S=3: quota = floor(100/4) + 1 = 26. Since 26 ≥ 26, stop.
- Result: **4 viable candidates** (top 4 by FPTP votes)
- Viable-candidate-maximum = floor((4+1)/2) = 2 approvals per voter

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
Based on the classic Tennessee capitol selection example, with approval patterns derived from geographic proximity. This demonstrates native approval ballot parsing where voters perform a mix of bullet voting and
approving two candidates.

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

## Notes Feature Design

### Overview
To support better transparency and user understanding, abiflib will implement a standardized "notes" feature that can be applied across all voting methods. This feature provides structured explanations of data transformations, algorithm assumptions, and important caveats.

### Notes Structure
Each voting method result will include a `notes` array containing note objects with this structure:

```json
{
  "notes": [
    {
      "notice_type": "disclaimer",
      "short": "Approval counts estimated from ranked ballots",
      "long": "This uses a `reverse Droop` calculation to provide a crude estimate for the number of viable candidates:\na) Count the top preferences for the all candidates\nb) Determine the minimum number of figurative seats that would need to be filled in order for the leading candidate to exceed the Droop quota.\nFor this election, this is {viable} seats, so {viable} candidates are considered viable.\nTo then determine the number of viable candidates voters are likely to approve of, divide the number of viable candidates by two, and round up.\nIn this election, each voter approves up to {half_viable} viable candidates.\nOn these ballots, all candidates ranked at or above the lowest-ranked of each voter's viable candidates are approved."
    }
  ]
}
```

### Field Specifications

#### `notice_type`
Categorizes the type of notice for appropriate display styling:
- `"disclaimer"`: Important caveats about data transformation or algorithm assumptions
- `"warning"`: Potential issues with data quality or interpretation
- `"info"`: General informational notes about methodology
- `"debug"`: Technical details for developers (may be filtered in production)

#### `short`
- **Length limit**: ~120 characters
- **Purpose**: Brief, actionable summary suitable for UI tooltips, summary lists, or mobile displays
- **Style**: Sentence fragment or single sentence, no period unless multiple sentences

#### `long`
- **Length limit**: Unlimited, but typically 200-800 characters
- **Purpose**: Detailed technical explanation sufficient for another developer to independently implement the same algorithm
- **Style**: Complete sentences with technical precision
- **Content**: Should include specific parameter values, decision points, and algorithmic steps

### Implementation in approval_tally.py

#### Modified Function Signatures
```python
def approval_result_from_abifmodel(abifmodel, method='auto'):
    """Calculate approval voting results from jabmod."""
    # Returns dictionary including 'notes' array
    return {
        'approval_counts': {...},
        'winners': [...],
        'total_approvals': int,
        'ballot_type': str,
        'notes': [...]  # New notes array
    }

def get_approval_report(abifmodel, method='auto'):
    """Generate human-readable approval voting report."""
    # Text report will include notes section at bottom
```

#### Notes Generation Logic
[21~```python
def _generate_approval_notes(method, ballot_type, viable_candidates=None, viable_candidate_maximum=None):
    """Generate appropriate notes based on approval calculation method."""
    notes = []

    if method == 'simulate':
        # Add strategic simulation disclaimer
        short_text = "Approval counts estimated from ranked ballots using strategic threshold method"

        long_text = (
            f"Strategic approval simulation algorithm: For each ballot, calculate the Droop quota "
            f"(total_votes / (seats + 1) + 1, where seats=1 for single-winner elections). "
            f"Sort candidates by their first-preference vote totals in descending order. "
            f"Determine {len(viable_candidates) if viable_candidates else 'N'} viable candidates based on cumulative FPTP analysis. "
            f"Set viable-candidate-maximum to {viable_candidate_maximum if viable_candidate_maximum else 'floor((viable_count + 1) / 2)'}. "
            f"For each ballot, identify the top viable-candidate-maximum viable candidates ranked by the voter, "
            f"then approve all candidates ranked at or above the lowest-ranked of those viable candidates. "
            f"This simulates strategic voters who approve all candidates they prefer over the likely winner, "
            f"based on first-preference polling data. The algorithm assumes voters have perfect information "
            f"about first-preference vote shares and vote strategically to maximize their utility while "
            f"avoiding the spoiler effect."
        )

        notes.append({
            "notice_type": "disclaimer",
            "short": short_text,
            "long": long_text
        })

    elif method == 'native' and ballot_type != 'approval':
        # Warn about potential ballot type mismatch
        notes.append({
            "notice_type": "warning",
            "short": f"Native approval calculation applied to {ballot_type} ballot format",
            "long": f"The ballot format was detected as '{ballot_type}' but native approval calculation was explicitly requested. Results may not reflect voter intent if ballots contain ranking or rating data that was ignored during approval extraction."
        })

    return notes
```

### Text Report Integration
The `get_approval_report()` function will append notes to the text output:

```python
def get_approval_report(abifmodel, method='auto'):
    """Generate human-readable approval voting report."""
    results = approval_result_from_abifmodel(abifmodel, method)

    # ... build main report sections ...

    # Add notes section if present
    if results.get('notes'):
        report += "\n" + "="*50 + "\n"
        report += "NOTES\n"
        report += "="*50 + "\n"

        for note in results['notes']:
            notice_type = note.get('notice_type', 'info').upper()
            report += f"\n[{notice_type}] {note['short']}\n"

            if note.get('long'):
                # Word wrap the long note at 78 characters
                import textwrap
                wrapped = textwrap.fill(note['long'], width=76,
                                      initial_indent='  ',
                                      subsequent_indent='  ')
                report += f"\n{wrapped}\n"

    return report
```

### JSON Output Integration
When abiftool generates JSON output (`-t json`), the notes array will be included at the top level:

```json
{
  "approval_counts": {"Nash": 50, "Memph": 42, "Chat": 36, "Knox": 21},
  "winners": ["Nash"],
  "total_approvals": 148,
  "ballot_type": "ranked",
  "notes": [
    {
      "notice_type": "disclaimer",
      "short": "Approval counts estimated from ranked ballots using strategic threshold method",
      "long": "Strategic approval simulation algorithm: For each ballot, calculate the Droop quota..."
    }
  ]
}
```

### AWT Integration Pattern
The notes feature provides a standard pattern for awt.py to display method-specific disclaimers:

```python
# In conduits.py
def update_approval_result(self, jabmod) -> "ResultConduit":
    """Add approval voting result to resblob"""
    approval_result = approval_result_from_abifmodel(jabmod)
    self.resblob['approval_result'] = approval_result
    self.resblob['approval_text'] = get_approval_report(jabmod)
    self.resblob['approval_notes'] = approval_result.get('notes', [])
    return self
```

```html
<!-- In results template -->
{% if approval_result.notes %}
<div class="method-notes">
  {% for note in approval_result.notes %}
    <div class="note note-{{ note.notice_type }}">
      <strong>{{ note.notice_type|title }}:</strong> {{ note.short }}
      {% if note.long %}
        <details>
          <summary>Technical details</summary>
          <p>{{ note.long }}</p>
        </details>
      {% endif %}
    </div>
  {% endfor %}
</div>
{% endif %}
```

### Future Extension to Other Methods
This notes structure is designed to be adopted by other voting methods:

```python
# STAR method could add:
{
  "notice_type": "disclaimer",
  "short": "Star ratings estimated from ranked ballots using Borda-like formula",
  "long": "Since ratings or stars are not present in the provided ballots, allocated stars are estimated using a Borda-like formula where the top-ranked candidate receives the maximum stars, second-ranked receives maximum-1 stars, etc."
}

# IRV method could add:
{
  "notice_type": "warning",
  "short": "Ballot contains equal rankings that may affect elimination order",
  "long": "This election contains ballots with tied rankings (e.g., A=B>C). The IRV algorithm handles ties by [specific tie-breaking method], which may not reflect all voters' true preferences in ambiguous cases."
}
```

This standardized approach ensures consistent user experience across all voting methods while maintaining the flexibility for method-specific explanations.
