# CR014 Implementation Plan: Prompt Architecture Simplification & Constraint/Judgment Separation

**Created**: March 27, 2026
**Status**: Implemented
**CR Reference**: `3. ChangeLog/CR014 - Prompt Architecture Simplification & Constraint or Judgment Separation.md`

---

## Summary

The strategy prompt was conflating two concerns: hard constraint enforcement and judgment guidance. This caused the LLM to pattern-match framework steps rather than genuinely reason, and exposed the user to math errors (LLM-calculated sequential cash flows).

CR014 separates the concerns:
- Python pre-computes all hard constraint facts and cash flows before the prompt
- The LLM receives a pre-computed `SITUATION SUMMARY` (authoritative facts) instead of rules
- `strategy.txt` is replaced with a compact Decision Guide (~78 lines, was ~330)
- The 6-dimension investor profile block is replaced by one synthesised `INVESTOR STANCE` paragraph
- Narrative boundary enforcement moves into `narrative_manager.py` (structural), not the prompt

---

## Files Modified

### 1. [App/src/ai_agent.py](../App/src/ai_agent.py)

**Added 4 new functions** in a new "Pre-computation" section before `build_prompt()`:

- **`pre_compute_constraints(context)`**: Computes stop-loss breaches (per sellable lot), earnings blackouts (from positions/opportunities earnings data), sellable lot summary, cash ratio, position count, concentration, and max_concentration from investor profile.

- **`pre_compute_cash_flows(context)`**: Computes starting cash, per-ticker sellable proceeds (qty × price − fee), and max_deployable total.

- **`build_situation_summary(constraints, cash_flows, context)`**: Translates the two dicts into plain English injected at the top of the prompt. Authoritative — LLM must not recalculate.

- **`_format_investor_stance(config)`**: Replaces `_format_investor_profile()`. Maps each config dimension to its net-effect sentence using hard-coded lookup tables. Returns a 6-line paragraph, not a definition block.

**Updated `build_prompt()`**:
- New signature: `build_prompt(context, strategy, narratives, market_data, situation_summary=None, config=None)`
- Injects `situation_summary` at the top of the prompt
- Uses `_format_investor_stance(cfg)` instead of `_format_investor_profile(config)`
- Removed: `REGULATORY CONSTRAINT`, `LOCK STATUS`, `CRITICAL EARNINGS RULES`, `SEQUENTIAL CASH FLOW CALCULATION`, `PORTFOLIO VS NARRATIVE CONFLICT CHECK`, `NARRATIVE BOUNDARY RULE`
- Simplified `NARRATIVE UPDATES` instruction to 3 lines
- Simplified `YOUR TASK` to reference SITUATION SUMMARY and DECISION QUESTIONS

**Updated `get_recommendation()`**:
- Pre-computes constraints/cash_flows/situation_summary before `build_prompt()`
- Passes `situation_summary` and `config` to `build_prompt()`
- Updates both the manual mode and API paths to use new `validate_actions()` signature
- Stores `rejected_actions` in the recommendation dict

**Updated `validate_actions()`**:
- New signature: `validate_actions(actions, constraints, cash_flows, config) -> tuple[list, list]`
- Returns `(valid_actions, rejected_actions)` — rejected actions include a `rejection_reason` field
- Uses pre-computed constraints (no re-parsing of dates, prices, or lock status)
- Checks: sell blackout, locked lots, buy blackout, max positions, cash sufficiency

---

### 2. [App/config/strategy.txt](../App/config/strategy.txt)

Full rewrite. ~330 lines → ~78 lines. Structure:

```
HARD CONSTRAINTS (enforced by system — do not recalculate)
  → Reference SITUATION SUMMARY as authoritative

JUDGMENT PRINCIPLES (6 condensed principles)

SIGNAL PRIORITY (6 levels)

DECISION QUESTIONS
  → HOLD/EXIT; AVERAGE DOWN; NEW ENTRY; CASH DEPLOYMENT; AVERAGING DOWN SCALE

INVESTOR STANCE
  → [Injected dynamically by _format_investor_stance()]
```

Removed: Layer 0 investor profile definitions, Layer 1 constraint prose, Frameworks A–E step-by-step narration, Signal Hierarchy prose, sequential cash flow instructions, narrative boundary rule.

---

### 3. [App/src/narrative_manager.py](../App/src/narrative_manager.py)

- Added `import re`
- Added `sanitise_narrative_update(update: dict) -> dict` before `get_empty_narratives()`. Detects and strips sentences matching portfolio-state patterns (share counts, lot references, stop-loss dollar levels, cost basis, trade confirmations, cash/proceeds amounts) from narrative `summary` fields before they are written.
- Added call `ai_updates = sanitise_narrative_update(ai_updates)` as the first operation in `update_narratives()`.

This makes the narrative boundary rule structural (enforced in Python) rather than prompt-dependent.

---

### 4. [App/src/display.py](../App/src/display.py)

- Added a "Rejected Actions" block in `display_recommendations()` after the valid actions block. Shows ticker, action type, and reason for each rejected action in yellow.

---

## What Does Not Change

- Portfolio data model (`portfolio.json`)
- Config structure (`config.json`) — `investor_profile` keys remain, read by `_format_investor_stance()`
- CLI commands (`advisor.py`)
- Data collection, ranking, event detection
- Simulation and ledger

---

## Prompt Token Reduction (Estimate)

| Section | Before | After |
|---------|--------|-------|
| Layer 0 investor profile definitions | ~80 lines | 0 (moved to code) |
| Layer 1 constraint prose | ~30 lines | 8 lines (summary reference) |
| Layer 2 principles | ~30 lines | 15 lines (condensed) |
| Layer 3 frameworks A–E | ~120 lines | 40 lines (decision guide) |
| Signal hierarchy | ~30 lines | 12 lines (inline) |
| Sequential cash flow instruction | ~20 lines | 0 (moved to code) |
| Narrative boundary rule | ~20 lines | 3 lines (simplified) |
| **Total strategy content** | **~330 lines** | **~78 lines** |

---

## Verification

1. `cd App && python -m src.advisor run --manual`
2. Open `output/prompt_YYYYMMDD_HHMMSS.md` and confirm:
   - `SITUATION SUMMARY` block at top with pre-computed facts
   - Compact Decision Guide present (~78 lines), no Layer 0–3 prose
   - `INVESTOR STANCE` paragraph (not 6-bullet profile block)
   - No duplicate constraint language
3. Paste to Claude.ai, paste response back — reasoning should be 2–3 sentences per action
4. Terminal output: if LLM produces an invalid action, it appears under "Rejected Actions" with reason
5. Open `narratives.json` — no share counts, cost basis, or stop-loss dollar amounts in summaries
6. Set `risk_tolerance = Conservative` in config.json, re-run, confirm INVESTOR STANCE reflects it
7. Reset to `Moderate`
