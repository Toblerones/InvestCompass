# CR011 Implementation Plan: Enforce Separation Between Narrative State and Portfolio State

**Created**: March 20, 2026
**Status**: Implemented
**CR Reference**: `3. ChangeLog/CR011 - Enforce Separation Between Narrative State and Portfolio State`

---

## Summary

The advisor was writing portfolio execution state (avg cost, stop-loss levels, trade
confirmations) into narrative fields. Because trades are not always executed after being
recommended, the narrative could reflect a portfolio state that never existed. Subsequent
runs then reasoned against two conflicting sources of truth simultaneously — producing
incoherent recommendations (e.g. phantom stop-loss levels, HOLD/WAIT label confusion).

This is a prompt instruction change only. Three additions to `build_prompt()` in
`ai_agent.py` enforce the boundary and give the LLM an explicit recovery path when a
conflict is detected.

---

## Root Cause

The narrative update instruction said:

```
- UPDATES: If an active theme has new developments, update the summary
```

"New developments" was interpreted too broadly — trade executions are portfolio events,
not market events, but the prompt gave no rule to distinguish them. The NVDA narrative
was updated with `avg cost $185.20, stop-loss $166.68` after a recommended (but
unexecuted) averaging-down trade, causing the advisor to reason against phantom data
on the next run.

---

## File Modified

### [App/src/ai_agent.py](../App/src/ai_agent.py) — `build_prompt()` function

Two new sections inserted and one section rewritten in the prompt string.

---

### Change 1: Portfolio vs Narrative Conflict Check (inserted before NARRATIVE BOUNDARY RULE)

Added to the YOUR TASK section:

```
PORTFOLIO VS NARRATIVE CONFLICT CHECK:
Before reasoning, check whether any narrative contains portfolio state (cost basis,
stop-loss levels, share counts, trade confirmations) that conflicts with the portfolio
data block. If a conflict exists:
1. The portfolio block is correct — disregard the narrative data
2. Note the conflict explicitly in your reasoning
3. Correct the offending narrative in your narrative_updates response
```

Purpose: gives the LLM an explicit recovery mechanism. When contaminated narratives
already exist in `narratives.json` (as they did after the NVDA incident), the advisor
will self-correct rather than silently amplify the bad data.

---

### Change 2: Narrative Boundary Rule (new section, before NARRATIVE UPDATES)

```
NARRATIVE BOUNDARY RULE (enforced):
Narratives track market intelligence only — news, thesis, sentiment, analyst views,
technical observations as market data.

Narratives must NEVER contain:
- Your cost basis or average cost
- Stop-loss price levels (these derive from your cost basis)
- Number of shares held or position size
- Trade execution confirmations ("averaging down initiated", "position exited")
- Cash balance or proceeds calculations

These belong exclusively in the portfolio data block, which is generated from actual
trade records and is always the source of truth. If the portfolio block and a narrative
ever conflict, the portfolio block is correct — disregard the narrative and correct it.
```

Purpose: explicit prohibition list rather than relying on the LLM to infer the boundary.

---

### Change 3: Tightened Narrative Update Instructions (rewrite of existing section)

**Before:**
```
NARRATIVE UPDATES (in addition to recommendations):
After analyzing current conditions, update narratives for stocks you're tracking:
- NEW themes: If a material theme (regulatory, earnings concern, acquisition, etc.) has emerged, add it
- UPDATES: If an active theme has new developments, update the summary
- RESOLVE: If a theme has concluded (e.g., earnings beat resolves concern), mark resolved
```

**After:**
```
NARRATIVE UPDATES (in addition to recommendations):
After analyzing current conditions, update narratives for stocks you're tracking.
Narratives track market intelligence only — never portfolio execution state.

- NEW: If a material market theme has emerged (news event, regulatory development,
  analyst view, competitive shift), add it with impact assessment
- UPDATE: If an active theme has new market developments, update the summary.
  Reference price levels only as external market data, never as your cost basis.
- RESOLVE: If a theme has concluded (e.g. legal dispute settled, earnings result
  confirmed), mark resolved with a one-line outcome summary

Never write into narratives: cost basis, stop-loss levels, share counts,
trade confirmations, or cash calculations. These live in the portfolio block only.
```

Purpose: closes the "new developments" loophole with an explicit reminder at the point
of action, and distinguishes external price levels (allowed) from personal cost basis (not allowed).

---

## What Does Not Change

- Narrative structure (add / update / resolve) and JSON format — unchanged
- Portfolio data block format and content — unchanged
- All reasoning frameworks (A/B/C/D) — unchanged
- Signal hierarchy — unchanged
- Response JSON format — unchanged
- `narrative_manager.py`, `recommendations_manager.py`, all other code files — unchanged

---

## Verification

1. Run `python -m src.advisor --manual` from `App/`
2. Open `output/prompt_YYYYMMDD_HHMMSS.md` — confirm:
   - PORTFOLIO VS NARRATIVE CONFLICT CHECK section is present
   - NARRATIVE BOUNDARY RULE section with the prohibited list is present
   - NARRATIVE UPDATES section includes the market-intelligence-only clarification
3. Submit a prompt with a contaminated narrative (e.g. one containing avg cost and
   stop-loss) — confirm the advisor:
   - Detects the conflict and flags it in reasoning
   - Uses portfolio block values, not narrative values
   - Outputs a corrected narrative in `narrative_updates`
4. After a recommended-but-unexecuted trade, confirm the narrative written on the
   next run contains no cost basis, stop-loss, share count, or trade confirmation text
