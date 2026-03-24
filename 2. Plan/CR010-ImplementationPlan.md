# CR010 Implementation Plan: Signal Hierarchy for Conflicting Decision Factors

**Created**: March 20, 2026
**Status**: Implemented
**CR Reference**: `3. ChangeLog/CR010 — Introduce Signal Hierarchy to Resolve Conflicting Decision Factors`

---

## Summary

CR009 defined *what questions to ask* before each decision. CR010 adds *how to weigh answers
when they conflict*. Without a signal hierarchy, the LLM defaults to whichever signal has the
most explicit threshold in the prompt — currently RSI (`RSI < 50`), which was never intended to
be a hard gate. This is a prompt-only change: one new section and one modified framework step
in `strategy.txt`.

---

## Root Cause

Framework C (new entry) currently checks entry timing in step 2:
```
RSI < 50 or at technical support: favorable
```
This is the most explicit numerical threshold in the framework. With no declared priority ordering,
the LLM treats it as equally weighted against all other signals — and because it's the most
concrete, it implicitly wins. A major positive catalyst with RSI at 55 would be blocked by this
soft preference, which is the wrong outcome.

---

## File to Modify

### [App/config/strategy.txt](../App/config/strategy.txt) — Two edits

---

### Edit 1: Add Signal Hierarchy section to Layer 3 (before Framework A)

Insert the following block at the start of Layer 3, before `--- Framework A ---`:

```
--- Signal Hierarchy: How to resolve conflicting inputs ---

When signals conflict, resolve them in this order. A higher-priority signal
always outweighs a lower-priority one. Never let a weak signal block a strong one.

PRIORITY 1 — Hard constraints (Layer 1)
  Always enforced. No signal overrides these.
  Examples: 30-day hold, -10% stop-loss, earnings proximity rules.

PRIORITY 2 — Material fundamental events
  New, concrete information about the business.
  A material event overrides technical timing.
  Positive: large contract, earnings beat, guidance raise, strategic partnership
    → enter or hold even if RSI is above 50
  Negative: earnings miss, rank collapse, CEO departure, regulatory action
    → exit or do not enter even if RSI appears oversold

PRIORITY 3 — Fundamental rank
  Must be top 3 for entry. Rank alone does not override a negative material event.

PRIORITY 4 — Thesis integrity
  Is the original investment case intact, strengthening, or weakening?
  A weakening thesis outweighs favorable technical signals.

PRIORITY 5 — Portfolio-level signals
  Concentration, correlation, cash buffer. Constrain position sizing but do not
  override fundamental signals.

PRIORITY 6 — Technical timing (RSI, support levels, vs SPY)
  A soft preference that improves entry/exit timing.
  RSI < 50 is a favorable signal, not a gate.
  RSI > 50 defers entry only when no stronger signal (Priority 2–4) is present.

CONFLICT RESOLUTION RULE:
  When signals conflict, explicitly state which priority level each belongs to,
  which is winning, and why. Never let a lower-priority signal block a
  higher-priority one silently.
```

---

### Edit 2: Update Framework C — split step 2 (entry timing) into two steps

**Current step 2 in Framework C:**
```
2. Is entry timing favorable?
   - RSI < 50 or at technical support: favorable
   - Within 7 days of earnings: do not enter
   - No major negative catalyst in past 7 days: required
```

**Replace with:**
```
2. Is there a material fundamental signal? (Priority 2 — check before technicals)
   - Major positive catalyst in past 7 days (large contract, earnings beat,
     guidance raise, strategic partnership): favorable entry regardless of RSI
   - Major negative catalyst in past 7 days: do not enter regardless of RSI
   - No material signal present: proceed to step 3

3. Is entry timing favorable? (Priority 6 — only if no material signal from step 2)
   - RSI < 50 or at technical support: favorable
   - RSI > 50 with no material positive signal: defer entry, use WAIT
   - Within 7 days of earnings: do not enter (hard constraint, Priority 1)
```

Note: The existing steps 3, 4 in Framework C (portfolio fit and capital source) become steps
4 and 5 after the insertion.

---

## What Does Not Change

- Layer 1 hard constraints — unchanged
- Layer 2 principles — unchanged
- Frameworks A, B, D — unchanged
- WAIT action type — unchanged
- RSI remains a valid input — demoted from implicit gate to explicit tiebreaker
- All code files — no changes required

---

## Verification

1. Run `python -m src.advisor --manual` from `App/`
2. Open `output/prompt_YYYYMMDD_HHMMSS.md` — confirm:
   - Signal Hierarchy section is visible in the strategy section before Framework A
   - Framework C step 2 shows the material signal check before RSI
3. Test scenario A (no catalyst, RSI > 50): advisor should return WAIT and cite RSI
   as Priority 6 tiebreaker with no higher-priority signal present
4. Test scenario B (positive catalyst, RSI > 50): advisor should recommend BUY and
   explicitly state material event (Priority 2) overrides RSI (Priority 6)
5. Test scenario C (negative catalyst, RSI oversold): advisor should not enter/average
   down and state thesis integrity (Priority 4) overrides RSI
