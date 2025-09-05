# abiflib Module Overview and Naming Conventions

This document summarizes the structure and naming patterns used in `abiflib/` as checked into the abiftool repository. It is intended to help contributors discover where functionality belongs and to guide future refactors toward consistent naming.

## Directory Overview

Current Python modules under `abiflib/`:

- Core and utilities
  - `core.py` — ABIF string ⇄ jabmod (JSON ABIF Model) conversion; parsing and metadata handling.
  - `util.py` — shared helpers (e.g., `find_ballot_type`, detection utilities).
  - `abifregex.py` — compiled regex constants used by `core.py`.
  - `devtools.py` — development helpers and instrumentation.
  - `__init__.py` — package aggregator.

- Tally implementations (by voting method)
  - `fptp_tally.py` — choose‑one (FPTP) tally.
  - `irv_tally.py` — IRV/RCV tally and summary wrappers.
  - `pairwise_tally.py` — pairwise/Copeland results and notices.
  - `approval_tally.py` — approval voting results and (for ranked→approval) conversion logic, notices, and reports.
  - `score_star_tally.py` — STAR/Score tallies and notices.

- Input formats / ingestion
  - `nameq_fmt.py` — Nameq ballots to ABIF.
  - `preflib_fmt.py` — PrefLib ballots to ABIF.
  - `sftxt_fmt.py` / `sfjson_fmt.py` — San Francisco RCV export formats to ABIF.
  - `stlcvr_fmt.py` — St. Louis CVR to ABIF; marks `metadata.ballot_type = 'choose_many'`.
  - `nycdem_fmt.py` — NYC Democratic primary exports to ABIF.
  - `debvote_fmt.py` — Debian vote formats to ABIF.
  - `widj_fmt.py` — WIDJ format to ABIF.

- HTML/text output helpers
  - `html_output.py`, `html_output_common.py`, `html_output_pairwise.py`, `html_output_scorestar.py` — HTML render helpers (tables, diagrams, snippets).
  - `text_output.py` — shared text rendering helpers for notices and reports.
  - `vizelect.py`, `vizelect_output.py` — visualization helpers and outputs.

- Legacy/compat shims (kept for backward compatibility; candidates for consolidation)
  - `irvtally.py` (older IRV naming; superseded by `irv_tally.py`).
  - `pairwise.py` (superseded by `pairwise_tally.py`).
  - `scorestar.py` (superseded by `score_star_tally.py`).
  - `sftxt.py` (older SF text processing; use `sftxt_fmt.py`).
  - `nameq.py`, `preflib.py` (older ingestion helpers; use `*_fmt.py`).
  - `textoutput.py` (older text helpers; use `text_output.py`).
  - `debtally.py`, `deadfuncs_debtally.py` (Debian‑specific legacy code).

## Naming Conventions

- Suffixes indicate responsibility:
  - `*_fmt.py` — input format adapters that read external data and produce ABIF/jabmod.
  - `*_tally.py` — tally logic for a single voting method (compute results, notices, and summaries).
  - `*_output*.py` — rendering helpers (HTML/text) layered on top of tallies.
- Method and format names are lower_snake_case; prefer descriptive, “expanded” names: `score_star_tally.py` over `scorestar.py`.
- Package‑internal “model” terminology:
  - “ABIF” — the line‑based source format.
  - “jabmod” — the JSON ABIF Model (Python dict) used internally and by callers.
- Discovery and metadata:
  - Input adapters should set `abifmodel['metadata']['ballot_type']` when known (`'ranked'`, `'approval'`, `'choose_many'`, `'rated'`, etc.).
  - Tallies may read `find_ballot_type(jabmod)` (from `util.py`) to adjust notices or behavior.

## Placement Guidance

- New input sources: add a `*_fmt.py` module and keep parsing concerns separate from tally code.
- New voting methods: add a `*_tally.py` module and, if needed, optional `html_output_*` helpers.
- Cross‑format ballot conversions (what‑if analysis): centralize in a single module (see “Conversions” below) rather than embedding inside tallies.

## Conversions (Cross‑format)

abiflib already performs conversions in some tally modules (e.g., strategic ranked→approval inside `approval_tally.py`). For clarity and reuse:

- Consider a dedicated module for conversions, e.g., `convert.py`, to house:
  - ranked→approval strategies (current implementation can be factored or re‑exported)
  - approval→ranked strategies (Options A–F)
  - rated⇄ranked/approval helpers
- Rationale:
  - Promotes reusability across CLI, AWT, and future tools.
  - Keeps tallies focused on tabulation, not on defining conversions.
  - Allows clean `conversion_meta` + `notices` to be attached consistently.
- Backward compatibility: tallies can import from `convert.py` without changing their external API.

## Consistency Targets (Post‑0.34)

- Prefer `*_tally.py` and `*_fmt.py` names; migrate legacy duplicates over time (e.g., remove `irvtally.py`, `textoutput.py`, `scorestar.py` once unused).
- Keep HTML/text render helpers out of core tally logic to preserve CLI/web parity.
- Document the `jabmod` schema invariants (keys used by tallies and outputs) in a separate schema note.

