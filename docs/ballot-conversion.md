# Ballot Conversion Algorithms

## Overview

This document describes algorithms for converting between different ballot formats in abiflib. Cross-format conversions enable "what-if" analysis, allowing users to explore how different voting methods would perform on the same underlying voter preferences.

## Conversion Matrix

| From → To | Status | Algorithm | Quality |
|-----------|--------|-----------|---------|
| Ranked → Approval | ✅ Implemented | Strategic Droop Simulation | High |
| Approval → Ranked | ❓ Needed | TBD (see proposals below) | Medium |
| Ranked → Rated | ✅ Implemented | Borda-like scoring | Medium |
| Rated → Approval | ✅ Trivial | Threshold-based | High |
| Rated → Ranked | ⚠️ Partial | Score-based ordering | Medium |
| Approval → Rated | ❓ Needed | Binary 0/1 assignment | Low |

## Ranked → Approval Conversion

### Algorithm: Strategic Droop Simulation
Status: Implemented in `approval_tally.py`

#### Summary
Converts ranked ballots to approval ballots by simulating strategic voting behavior. Uses iterative Droop quota analysis to determine candidate viability, then applies a strategic approval threshold.

#### Key Steps
1. **Calculate FPTP results** for viability assessment
2. **Determine viable candidates** using iterative Droop quota analysis  
3. **Calculate viable-candidate-maximum**: `floor((viable_count + 1) / 2)`
4. **Apply per-ballot strategy**: Approve candidates ranked above the lowest-ranked viable candidate among voter's top viable choices

#### Rationale
- **Viability assessment**: Weak frontrunner (low %) → many viable competitors; strong frontrunner (high %) → fewer viable competitors
- **Strategic threshold**: Balances preference expression with competitive effectiveness
- **Realistic modeling**: Simulates informed voters with strategic awareness

#### Example
If frontrunner has 26% of votes:
- Droop analysis determines 4 viable candidates  
- Each voter approves up to 2 viable candidates (`floor((4+1)/2) = 2`)
- Strategic threshold applied per ballot based on voter's ranked preferences

See `abiftool/docs/approval-voting.md` for complete implementation details.

### Alternative Approaches (Variants)
The following neutral variants can replace or complement Strategic Droop Simulation depending on goals:
- Fixed top‑m approvals: Approve the first m candidates on each ranked ballot (m may be constant or a function of total candidates). Simple, but ignores viability.
- Threshold on Borda‑like scores: Convert rankings to scores (e.g., linear Borda), then approve candidates above a global or per‑ballot threshold. More graded, but threshold choice can be contentious.
- Viability by Hare quota: Use a different viability criterion (Hare/de facto thresholds) instead of Droop; otherwise identical workflow. Sensitivity differs under multi‑candidate fields.
- Hybrid viability + personal cutoff: Determine viability globally, then approve candidates above a per‑ballot rank cutoff within the viable set (e.g., approve top 2 viable per ballot). Balances global and local signals.

## Approval → Ranked Conversion

### Problem Statement
Converting approval ballots to ranked form enables IRV/RCV "what‑if" analysis, but multiple reasonable interpretations exist. The options below outline several high‑quality approaches with differing trade‑offs in transparency, computational cost, determinism, and how faithfully they preserve the approval signal.

### Proposed Algorithms

#### Option A: Tiered Ranking with Random Tie-Breaking
**Quality**: Medium  
**Complexity**: Low

```
For each ballot:
1. All approved candidates → Rank 1 (tied)
2. All unapproved candidates → Unranked (exhausted)
3. Resolve intra-rank ties using deterministic random (seeded by ballot hash)

Example ballot: A✓ B✓ C✗ D✗
Result: Random ordering of {A, B} at rank 1, {C, D} unranked
Possible: A > B > [exhausted] or B > A > [exhausted]
```

**Pros**:
- Simple and transparent
- Preserves approval/disapproval distinction
- Deterministic with proper seeding

**Cons**:
- High exhaustion rate (all disapproved candidates lost immediately)
- Random tie-breaking may not reflect true preferences
- Produces many short ballots

#### Option B: Preference Intensity Estimation
**Quality**: Medium-High  
**Complexity**: High

```
For each ballot:
1. Approved candidates ranked by estimated preference intensity
2. Unapproved candidates ranked below approved (or unranked)
3. Use aggregate signals to estimate intensity:
   - Co-approval patterns (candidates approved together)
   - Global popularity rankings
   - Pairwise preference estimation

Example: If A+B approved together more often than A+C, 
voter who approves {A,B,C} likely prefers B over C
```

**Pros**:
- Attempts to recover preference intensity
- Lower exhaustion rates
- More realistic IRV behavior

**Cons**:
- Complex algorithm with many assumptions
- Requires analysis of full dataset per ballot
- May introduce systematic biases

#### Option C: Approval Threshold Positioning
**Quality**: Medium  
**Complexity**: Medium

```
For each ballot:
1. Estimate voter's "approval threshold" on a utility scale
2. Assign scores to all candidates based on aggregate preference data
3. Rank all candidates by estimated utility, with approval/disapproval 
   as constraint

Example: If voter approves top 2 of 4 candidates,
assume approval threshold at 50th percentile of voter's utility function
```

**Pros**:
- More complete ballots (lower exhaustion)
- Principled threshold modeling
- Could use existing rated ballot conversion techniques

**Cons**:
- Requires utility function assumptions
- Complex calibration needed
- May not reflect binary approval nature

#### Option D: Monte Carlo Ensemble
**Quality**: High  
**Complexity**: High

```
For each conversion:
1. Run multiple conversion algorithms (A, B, C above)
2. Apply different random seeds or parameters
3. Generate N different ranked ballot interpretations
4. Report IRV winner frequencies and confidence intervals

Example: "IRV winner: Candidate A in 847/1000 simulations (84.7%)"
```

**Pros**:
- Acknowledges uncertainty in conversion
- Provides confidence measures
- Most honest about conversion limitations

**Cons**:
- Computationally expensive
- Complex to explain to users
- May overwhelm casual users

#### Option E: Fractional Split (Deterministic, Low Exhaustion)
**Quality**: Medium  
**Complexity**: Medium

Idea: When a ballot approves k candidates, split its weight across a small, symmetric set of ranked orders over those approved candidates so that the total weight sums to 1. No randomness; the split set is fixed and documented. Unapproved candidates do not appear in the per‑ballot ranking (ballot exhausts once approved set is eliminated).

Examples:
- Approves A,B → 0.5 A > B; 0.5 B > A
- Approves A,B,C → 1/3 each over A > B > C, B > C > A, C > A > B (cyclic rotations)

Pros:
- Deterministic and symmetric; preserves “no internal order” by distributing weight.
- Lower exhaustion than pure single‑ranking approaches that eliminate unapproved immediately (still exhausts after approved set).

Cons:
- Uses fractional weights; requires IRV implementation to support summing floats (display rounding must be handled carefully).
- For k ≥ 4, must choose a fixed subset of permutations (documented) or the full k! set (expensive).

Notes:
- Deterministic seeding (e.g., with contest id) can be used only to pick the fixed subset globally; no per‑ballot randomness.

#### Option F: Deterministic Global Order (Least‑Approval‑First)
**Quality**: Medium  
**Complexity**: Low

Idea: Build a full ranking for each ballot deterministically, without fractions or randomness, by ordering within the approved set using a global, contest‑wide order: candidates with fewer total approvals rank higher; the approval winner ranks lowest within the approved tier. Only approved candidates appear on each voter’s ranking; unapproved do not appear (ballots exhaust after approved set).

Procedure:
1. Compute global approval totals per candidate across all ballots.
2. Define the global order as ascending by total approvals (ties broken deterministically, e.g., by token).
3. For each ballot, list its approved candidates in that global order; omit unapproved.

Pros:
- Fully deterministic; no randomness, no fractional weights.
- Fast and straightforward to implement.
- Tends to mirror IRV behavior one might expect from approval voters: elimination begins with candidates that are broadly less approved, often yielding the same winner as approval.

Cons:
- Imposes a global within‑tier order the voter didn’t specify; advantages already‑popular candidates late in the order.
- Ballots still exhaust once their approved set is eliminated (unapproved are not added).

Variant: If desired to reduce exhaustion to near zero, append unapproved candidates in a deterministic order (e.g., same global order) after the approved list. This changes the interpretation and should be clearly disclosed; default here keeps only approved candidates.

### Selection Considerations (Non‑Prescriptive)

When choosing among Options A–F, consider:
- Determinism vs. randomness tolerance
- Willingness to use fractional weights
- Appetite for computational cost (e.g., ensembles)
- Desire to minimize ballot exhaustion vs. preserve strict "approved‑only" ordering
- Transparency and explainability to end users

Any of the options A–F can be appropriate depending on context and goals.

## Implementation Guidelines

### Conversion Quality Indicators
Each conversion should include metadata indicating:
- **Source format**: Original ballot type
- **Target format**: Converted ballot type  
- **Algorithm used**: Specific conversion method
- **Quality assessment**: Expected reliability (High/Medium/Low)
- **Limitations**: Known issues or assumptions

### Notice Generation
All conversions must generate appropriate notices:
```json
{
  "notice_type": "disclaimer",
  "short": "IRV results estimated from approval ballots",
  "long": "This election used approval voting. IRV results are hypothetical, generated by [specific algorithm]. [Quality/limitation details]."
}
```

### Testing Requirements
- **Synthetic data**: Test with known preference structures
- **Roundtrip testing**: Verify ranked → approval → ranked preserves key properties
- **Boundary cases**: Empty ballots, single approvals, universal approval

## CLI Plan for abiftool.py (Modifiers + Examples)

To make “what‑if IRV” from approval ballots accessible via the CLI with minimal surface area changes, add one or two modifiers and keep behavior opt‑in.

### Proposed Modifier

- `transform-ballots`
  - When combined with `-m IRV`, if the input `ballot_type` is not `ranked`, perform an Approval → Ranked conversion before IRV using Option F (Deterministic Global Order; least‑approval‑first). This is deterministic and avoids randomness and fractional weights.
  - When not present, the current behavior remains (no conversion), and IRV will include a disclaimer notice for non‑ranked ballots.
  - Future (post‑0.34): `transform-ballots` could accept parameters to choose among Options A–F; for 0.34 it defaults to Option F.

Notes:
- Existing `-m IRV` and `-m notices` continue to work as before. The new modifiers only affect IRV when input ballots are not ranked.
- Text output should show the conversion disclaimer via `-m notices` so users see the caveat in plain text.

### Example Command Lines

Show IRV with notices for STL mayor (current behavior, no conversion):

```
python3 abiftool.py -t text -m IRV -m notices abiftool/localabif/stlouis/stl-2025-mayor.abif
```

Show IRV using Option F (Deterministic Global Order) conversion, with notices:

```
python3 abiftool.py -f abif -m IRV -t text -m transform-ballots \
  abiftool/localabif/stlouis/stl-2025-mayor.abif
```

Expected behavior for the second command:
- IRV runs on a temporary ranked view constructed via Option F (least‑approval‑first within the approved set, deterministic).
- A prominent notice is included in the text output (when `-m notices` is also used):
  “Note — ranked ballots inferred from choose‑many ballots and approval results”.
  This avoids conflating ballot types (ranked vs choose‑many) with tally methods (IRV, Approval). The conversion only changes
  the ballot representation used by the IRV tally; it does not imply the real‑world method was IRV.
- Output remains deterministic and reproducible; no random seeds are involved.
- **Comparison studies**: Validate against elections with multiple ballot formats

## Future Considerations

### Multi-Stage Conversions
Some conversions may benefit from intermediate formats:
- Approval → Rated → Ranked (using utility estimation)
- Ranked → Rated → Approval (current STAR approach)

### Preference Learning
Advanced conversions could learn from elections with multiple ballot types:
- Train conversion models on dual-format elections
- Calibrate intensity estimation from voter survey data
- Validate conversion quality against known preference structures

### User Control
Allow users to:
- Choose conversion algorithms
- Set conversion parameters (thresholds, tie-breaking methods)
- Enable/disable hypothetical analysis
- Compare multiple conversion approaches

This document provides the framework for principled ballot conversion while maintaining transparency about the limitations and assumptions involved.
