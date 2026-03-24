# CR012 Implementation Plan: Cash Efficiency — Portfolio-Level Capital Deployment

**Created**: March 20, 2026
**Status**: Implemented
**CR Reference**: `3. ChangeLog/CR012 - Cash Efficiency Portfolio-Level Capital Deployment`

---

## Summary

The advisor evaluates each stock entry decision in isolation. It never steps back to ask
whether the overall cash/equity balance is efficient. The result is systematic cash hoarding:
"no perfect entry available" silently becomes "hold all cash," which is not the behaviour
of a disciplined investor. CR012 adds a cash drag principle and a new Framework E that
triggers whenever cash exceeds 50% of portfolio value, flipping the burden of proof from
"justify investing" to "justify staying in cash."

**Trigger instance**: After the MSFT stop-loss exit, $1,275.78 (87% of portfolio) sat idle
while NVDA — ranked #1, thesis strengthening, down -6.9% in a macro selloff — was never
considered for additional deployment. Framework B (averaging down) was not invoked.

---

## Root Cause

Layer 2 Principle 2 ("cost of inaction is real") exists but is not operationalised.
No framework triggers on cash level. No instruction compels the advisor to reason about
the cash/equity ratio before concluding. The per-stock signal checks all returned
"not yet" signals, and the advisor accepted that outcome without a portfolio-level review.

---

## File Modified

### [App/config/strategy.txt](../App/config/strategy.txt) — 3 targeted edits

---

### Edit 1: Add Principle 9 to Layer 2 (after Principle 8)

```
9. Cash drag is a risk, not a safe default
   Holding >50% of portfolio value in cash is not conservative — it is a
   failure to deploy capital in high-conviction ideas. When cash exceeds
   50% of total portfolio value, the burden of proof flips: the advisor
   must justify staying in cash, not justify investing.
   Cash is appropriate when: no top-3 stocks are available, all positions
   are locked, or a clear macro event warrants temporary defensive posture.
   Cash is not appropriate when: top-ranked stocks are available at a
   discount with intact or strengthening theses.
```

---

### Edit 2: Add step 5 to Framework B (after step 4 — cash buffer and concentration)

```
5. How much should I average down given the cash position?
   - Cash < 30% of portfolio: small addition only (preserve buffer)
   - Cash 30-60% of portfolio: moderate addition (up to 30% of available cash)
   - Cash > 60% of portfolio: consider larger addition (up to 50% of available cash)
     — cash drag justifies more aggressive deployment into highest conviction position
   - Never deploy more than 50% of available cash in a single averaging down action
```

---

### Edit 3: Add Framework E after Framework D (new section at end of Layer 3)

```
--- Framework E: Is my cash position justified? ---

Trigger: Run this framework whenever cash > 50% of total portfolio value.
Purpose: Ensure capital is deployed efficiently, not hoarded by default.

1. What is the current cash/equity ratio?
   Calculate: cash / (cash + total position value)
   - < 30%: healthy, no action needed from this framework
   - 30-50%: elevated, note in reasoning but no mandatory action
   - > 50%: cash drag — proceed through this framework
   - > 75%: severe cash drag — strong presumption toward deployment

2. What deployment options are available? (evaluate in order)

   Option A — Average down on existing positions (highest priority)
     Is any held position down due to macro weakness with intact thesis?
     If yes: averaging down is the priority use of excess cash.
     Apply Framework B with scale guidance from step 5.

   Option B — Enter a new top-3 position despite imperfect timing
     Is a top-3 stock available with no active Priority 2 negative catalyst?
     If cash drag is severe (> 75%) AND stock is within 5% of known support:
     Consider entering with reduced position size despite RSI above 50.
     Rationale: imperfect entry in a high-conviction stock beats
     perfect entry that never comes while cash erodes in real terms.

   Option C — Hold cash with explicit justification
     Cash hold is only justified if ALL of the following are true:
       - All top-3 stocks have active Priority 2 negative catalysts, OR
       - All positions are locked and no new entries qualify, OR
       - A clear macro event warrants defensive posture (state explicitly)
     If none of the above: cash hold requires explicit written justification,
     not just absence of a buy signal.

3. What is the opportunity cost of the current cash position?
   Estimate: if the top-ranked stock recovers to analyst consensus target,
   what return is foregone on the uninvested cash? State this explicitly.
   Do not let cash drag pass without quantifying what the user is giving up.

4. Recommend one of:
   - DEPLOY: Average down or enter position with sizing rationale
   - PARTIAL DEPLOY: Reduced position when timing imperfect but drag severe
   - HOLD CASH: With explicit written justification per Option C above
```

---

## What Does Not Change

- Layer 1 hard constraints (50% concentration limit, stop-loss, FIFO) — unchanged
- Signal hierarchy (CR010) — Framework E is additive, does not override Priority 2 signals
- Frameworks A, B, C, D — unchanged (B gains a new step 5 only)
- Narrative boundary rule (CR011) — unchanged
- Response JSON format — unchanged
- All code files — no changes required

---

## Verification

1. Run `python -m src.advisor --manual` from `App/`
2. Open `output/prompt_YYYYMMDD_HHMMSS.md` — confirm:
   - Layer 2 shows Principle 9 (cash drag)
   - Framework B shows step 5 (scale guidance)
   - Framework E is present after Framework D
3. With current portfolio ($1,275.78 cash, 87% of value):
   - Framework E should trigger (cash > 50%)
   - Step 1: severe cash drag (> 75%)
   - Step 2 Option A: NVDA averaging down evaluated
   - Step 3: opportunity cost of $1,275 vs NVDA consensus PT $265.97 stated
   - Recommendation: DEPLOY or PARTIAL DEPLOY, not HOLD CASH
4. Confirm cash hold still valid when all top-3 have active negative catalysts
