# CR009 Implementation Plan: Judgment-Based Advisor Strategy

**Created**: March 19, 2026
**Status**: Implemented
**CR Reference**: `3. ChangeLog/CR009 - Redesign Advisor Strategy-From Rules to Judgment-Based Reasoning`

---

## Summary

CR009 replaces the rules-engine prompt architecture with a three-layer judgment-based reasoning
framework. The advisor was blocking valid decisions (e.g. averaging down NVDA after an earnings
beat) because fixed percentage thresholds were firing without contextual consideration. This is
a prompt-only change — no data pipeline, no portfolio tracking, no CLI changes required.

A new `WAIT` action type is also introduced to disambiguate "keep this position" (HOLD) from
"defer this entry for a stock not yet owned" (WAIT).

---

## Root Cause

The previous `strategy.txt` used tiered conditional rules (TIER 1–4) that the LLM applied as
a checklist. The Tier 3 slow-drift rule (`rank slip + P&L < -3% → tighten stop to -7%`) was
the direct cause of the missed NVDA averaging-down recommendation: P&L at -5.2% triggered the
tighten rule, and the LLM treated that as authoritative without evaluating why the stock was down.

---

## Files Modified

### 1. [App/config/strategy.txt](../App/config/strategy.txt) — Full Rewrite

Replaced the flat rules list with the three-layer architecture.

**Removed:**
- TIER 1 / TIER 2 / TIER 3 / TIER 4 exit rules
- HOLD OVERRIDES section
- DECISION FRAMEWORK PRIORITIES list
- MANDATORY EXITS section (absorbed into Layer 1)
- SPECIAL CONSIDERATIONS section (absorbed into Layer 2 principles)

**Added:**

| Layer | Content |
|---|---|
| Layer 1 — Hard Constraints | 8 non-negotiable rules (FIFO, position limits, stop-loss, earnings timing) |
| Layer 2 — Principles | 8 guiding statements explaining the *why* behind good decisions |
| Layer 3 — Reasoning Frameworks | 4 named question sequences (A: exit, B: average down, C: enter, D: news) |

The capital efficiency rule from CR008 is preserved verbatim in Layer 2.

---

### 2. [App/src/ai_agent.py](../App/src/ai_agent.py) — 3 Targeted Edits

#### Edit 1: YOUR TASK section in `build_prompt()` (~line 227)

Replaced the static 6-point consideration list with a reference to the reasoning frameworks:

```
# BEFORE
Consider:
1. FIFO constraints - can locked positions be sold?
2. Ranking quality - are current holdings still top-ranked?
...

# AFTER
For each decision, work through the relevant reasoning framework defined in your strategy
(Framework A for exits, B for averaging down, C for new entries, D for news assessment).
Layer 1 hard constraints are non-negotiable. Use Layer 2 principles and Layer 3 frameworks
to reason — do not apply thresholds mechanically. ...
Use WAIT (not HOLD) when recommending deferring an entry for a stock you do not currently own.
```

#### Edit 2: Response format JSON in `build_prompt()` (~line 246)

Added WAIT to the action type union with an inline comment:

```json
"type": "SELL" | "BUY" | "HOLD" | "WAIT",  // HOLD = own it, keep it. WAIT = not owned, entry deferred.
```

#### Edit 3: `validate_actions()` (~line 910)

Updated the `else` comment to be explicit about WAIT:

```python
else:  # HOLD or WAIT — always valid, no constraint to check
    action['valid'] = True
```

---

## What Was Not Changed

- 30-day FIFO hold enforcement in `validate_actions()` — unchanged
- Hard stop-loss and profit target handling — unchanged
- Monthly budget handling (CR008) — preserved in Layer 2
- Sequential cash flow calculation — unchanged
- Narrative tracking format and update logic — unchanged
- JSON response structure — only the `type` field expanded (backwards compatible)
- Earnings calendar enforcement in prompt hardcoded section — unchanged
- All other files: `advisor.py`, `analyzer.py`, `recommendations_manager.py`, etc.

---

## Verification Steps

1. Run `cd App && python -m src.advisor --manual`
2. Open `output/prompt_YYYYMMDD_HHMMSS.md` — confirm:
   - Strategy section shows Layer 1 / Layer 2 / Layer 3 structure
   - No TIER rules visible
   - Response format shows `"SELL" | "BUY" | "HOLD" | "WAIT"`
3. Paste a test JSON response containing a WAIT action — confirm it:
   - Passes `validate_actions()` without error
   - Records correctly to `recommendations_ledger.json`
4. Run full `python -m src.advisor` — confirm:
   - Scenario: oversold stock, post-earnings beat, minor loss → Framework B reasoning in output
   - Scenario: unowned stock with unfavorable entry → WAIT (not HOLD) in recommendation
