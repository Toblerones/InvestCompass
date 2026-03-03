# Change Request: CR007 - Recommendation Ledger, Simulation & Learning Loop

**Date**: March 3, 2026
**Status**: Open
**Priority**: MEDIUM
**Severity**: Enhancement (New Feature)
**Affects**: AI Agent, CLI Interface, Strategy Management

---

## Problem Description

The advisor currently produces recommendations and they disappear after each run. There is **no way to assess whether past advice was good or bad**, no mechanism to track what was recommended versus what the user actually did, and no structured way for the advisor's strategy to improve over time based on real outcomes.

**Current Gap**:
- User runs the advisor, gets recommendations, and either acts on them or doesn't
- No record of what was recommended, when, or at what market conditions
- No way to answer "what if I had followed that advice last month?"
- No feedback loop — the advisor makes the same category of mistakes repeatedly without correction
- Strategy principles in `strategy.txt` are static and never evolve based on real-world results

**User Impact**:
- Cannot build trust in the advisor (no track record to review)
- Cannot identify systematic biases in the advisor's reasoning
- Missed learning opportunities — patterns in good and bad calls are invisible
- Strategy remains frozen at initial configuration regardless of real performance

**Example of the problem**:
```
February 7:  Advisor says "SELL MSFT, BUY NVDA"
             User decides to HOLD instead.

March 3:     User wonders: "Was that advice actually good?"
             No way to check. The recommendation is gone.
             
             Advisor recommends "SELL NVDA" today.
             Has no awareness that it recommended BUYING NVDA just 3 weeks ago.
             No context about whether its recent calls have been accurate.
```

---

## Expected Behavior

Three connected capabilities that build on each other:

### Piece 1: Recommendation Ledger

Every full advisory run automatically saves a recommendation record. The user can review past recommendations at any time.

**What gets stored per recommendation**:
- Unique advice ID (e.g., `ADV-2026-03-03-001`)
- Timestamp of when the advice was generated
- Portfolio snapshot at the time (what positions were held, at what prices)
- Market snapshot at the time (key prices for all tickers involved)
- The full list of recommended actions (BUY/SELL/HOLD with quantities and reasoning)
- Confidence level
- Whether the user accepted the advice (initially unknown, updated when user confirms trades)

**When it gets stored**:
- Automatically on every full advisory run (the default command)
- NOT stored on `check` runs (those are quick status checks, not actionable advice)
- NOT stored on `confirm`, `migrate`, or `sim` runs

**User outcome tracking**:
- When the user runs `confirm` to record executed trades, the system matches confirmed trades against the most recent unresolved advice record
- Marks the advice as `accepted` (followed the advice), `partial` (followed some actions), or `skipped` (did something different)
- This happens automatically — no extra steps for the user

**Example stored record**:
```
Advice ID:    ADV-2026-02-07-001
Date:         February 7, 2026
Portfolio:    MSFT 2.5 shares @ $478.08, NVDA 1.0 @ $191.83
              Cash: $274.17
Market:       MSFT $433.50, NVDA $192.51, AAPL $227.63
Actions:      1. SELL MSFT 1.5 shares (Lot 1)
              2. BUY AAPL $650 worth
Confidence:   HIGH
Outcome:      Skipped (user held all positions)
```

---

### Piece 2: Simulation Command

A new CLI command that lets the user evaluate any past recommendation by calculating what would have happened if they had followed the advice.

**Command**: `python -m src.advisor sim ADV-2026-02-07-001`

**What it does**:
1. Loads the advice record for the given ID
2. Looks up today's current prices for all tickers mentioned in the actions
3. Calculates: "If these exact trades had been executed at the prices on that date, what would those positions be worth today?"
4. Compares the simulated outcome against what actually happened (based on actual portfolio changes)

**What it shows**:

```
SIMULATION: ADV-2026-02-07-001
Date: February 7, 2026 → Today (24 days ago)
══════════════════════════════════════════════════

RECOMMENDED ACTIONS:
  1. SELL MSFT 1.5 shares @ $433.50     → Proceeds: $649.25
  2. BUY AAPL ~2.85 shares @ $227.63    → Cost: $649.25

SIMULATED OUTCOME (if accepted):
  AAPL:  2.85 shares bought @ $227.63 → now $241.80  = +6.2% (+$40.39)
  MSFT:  1.5 shares sold @ $433.50   → now $448.20   = missed +3.4% gain

  Net simulated P&L: +$17.52 (better than holding)

ACTUAL OUTCOME (what you did):
  Held all positions. MSFT Lot 1: $433.50 → $448.20 = +3.4%

VERDICT: Advice was GOOD — would have gained +$17.52 more than holding
```

**Scope boundaries**:
- Simulation evaluates only the specific trades recommended, not the entire portfolio going forward
- It does not attempt to simulate what the *next* advisory run would have said on the altered portfolio
- It uses simple price comparison (buy price then vs current price now)
- Transaction fees are included in the calculation
- It answers "was this specific advice good?" not "what would my entire portfolio look like in an alternate timeline?"

**Listing past recommendations**:

`python -m src.advisor sim --list` shows all stored recommendations:

```
RECOMMENDATION HISTORY
══════════════════════════════════════════════════
ID                       Date          Actions         Outcome    Sim P&L
─────────────────────────────────────────────────────────────────────────
ADV-2026-02-07-001       Feb 07        SELL MSFT,      Skipped    +$17.52
                                       BUY AAPL
ADV-2026-01-30-001       Jan 30        BUY NVDA,       Accepted   +$8.20
                                       BUY MSFT
ADV-2026-01-06-001       Jan 06        HOLD ALL        Accepted   n/a
─────────────────────────────────────────────────────────────────────────
Total recommendations: 3
Accepted: 2 | Skipped: 1
```

---

### Piece 3: Learning Loop

A mechanism for the advisor's strategy to improve over time, based on patterns identified from the recommendation ledger and simulation results.

**Why not feed raw simulation results directly into the AI prompt?**

We considered and rejected this approach for three reasons:

1. **Individual outcomes are noisy.** A good recommendation can lose money due to random market movement. A bad recommendation can profit by luck. Feeding "your last call lost 5%" teaches the AI nothing about *why* it was wrong — it just introduces recency bias.

2. **Context window cost.** The AI prompt is already large (portfolio, market data, news, narratives, strategy). Adding a growing list of historical outcomes would consume tokens and increase API cost without proportional value.

3. **Risk of emotional reasoning.** If the AI sees its recent sell recommendations led to missed gains, it may become reluctant to recommend sells — which is exactly the kind of bias the tool is designed to eliminate.

**What works instead: Strategy Refinements**

The useful signal is not "your last call was wrong" — it is "you have a pattern of misjudging X." The learning loop extracts patterns and encodes them as strategy refinements.

**How it works**:

**Step A: Scorecard accumulates data (automated)**

The system tracks outcomes over time, categorised by decision type and reasoning:
- Sell recommendations: how often were they right vs leaving gains on the table?
- Buy recommendations: hit rate, average return, average holding period
- Hold recommendations: was holding the right call vs missed exit opportunities?
- Breakdowns by reasoning category: fundamental, technical, event-driven, earnings-related

**Step B: Review command surfaces patterns (AI-assisted, user-approved)**

A new command `python -m src.advisor review` runs when enough data has accumulated (minimum 8-10 recommendations). It:
- Loads the full scorecard data
- Sends it to the AI with a specific prompt: "Analyse these outcomes and identify recurring patterns — where does the advisor systematically get it right or wrong?"
- Presents suggested refinements to the user

**Example output**:
```
STRATEGY REVIEW (based on 12 recommendations over 4 months)
══════════════════════════════════════════════════════════════

PATTERN 1: Post-earnings sell timing
  Data:     4 of 5 post-earnings dip sells recovered within 14 days
  Current:  Strategy has no post-earnings patience rule
  Suggest:  "After earnings, wait 14 days before recommending SELL
             if results beat estimates, even if price dips initially."

PATTERN 2: High-RSI entries underperform
  Data:     3 buys with RSI > 65 averaged -4.2% vs +7.1% for RSI < 55
  Current:  Strategy says "technical timing" but no RSI threshold
  Suggest:  "Avoid recommending BUY when RSI > 65, even if fundamental
             rank is #1. Wait for RSI pullback below 55."

PATTERN 3: Profit-taking threshold too high
  Data:     2 positions hit +15% then pulled back below +10% before
            reaching the +20% target
  Current:  Profit target set at +20%
  Suggest:  "Consider partial profit-taking (50% of position) at +15%
             rather than waiting for full +20% target."

────────────────────────────────────────────────────────────
Apply these refinements to strategy? [y/n/select]
```

**Step C: User approves, strategy updates (manual decision)**

- The user reviews the suggested refinements and decides which to accept
- Accepted refinements are added to the strategy principles under a `LEARNED REFINEMENTS` section
- This is a permanent improvement — all future advisory runs benefit from it
- The user can also manually add or edit refinements based on their own observations
- Rejected suggestions are noted so they are not re-suggested

**What this achieves**:
- The AI doesn't "remember" individual past trades (which is noise)
- Instead, the *rules the AI follows* get smarter over time (which is signal)
- The human stays in the loop — only patterns the user agrees with become strategy
- It compounds: each refinement permanently improves all future advice

---

## User Impact

### Scenario 1: Reviewing Past Advice

**Before**:
```
User wonders: "Was it right to ignore last month's sell recommendation?"
No data exists. Can't check. Relies on vague memory.
```

**After**:
```
$ python -m src.advisor sim ADV-2026-02-07-001

Simulation shows the advice would have gained +$17.52 vs holding.
User thinks: "I should probably follow the sell signals more often."
```

**User benefit**: Evidence-based trust calibration

---

### Scenario 2: Building a Track Record

**Before**:
```
User has been using the advisor for 3 months.
No idea if it's been helpful overall.
Gut feeling: "seems okay?"
```

**After**:
```
$ python -m src.advisor sim --list

12 recommendations tracked.
8 accepted, 4 skipped.
Accepted advice: 75% hit rate, avg +6.2%
Skipped advice: would have been 60% profitable.

User thinks: "The advisor is solid on buys but I should re-evaluate
how it handles sell timing."
```

**User benefit**: Quantified advisor performance

---

### Scenario 3: Strategy Gets Smarter

**Before**:
```
Month 1: Advisor recommends selling after earnings dip. Wrong.
Month 2: Advisor recommends selling after earnings dip. Wrong again.
Month 3: Advisor recommends selling after earnings dip. Wrong again.
Strategy never changes. Same mistake repeats.
```

**After**:
```
Month 4: User runs "review" command.
System identifies: "4 of 5 post-earnings sells were premature."
Suggests refinement: "Wait 14 days after earnings before selling."
User approves. Strategy updated.
Month 5: Advisor sees earnings dip, but now follows the refinement.
Recommends HOLD. Stock recovers. Correct call.
```

**User benefit**: Compounding improvement over time

---

### Scenario 4: Quick Status Checks Are Unaffected

**Before and After**:
```
$ python -m src.advisor check
[Same quick portfolio check as before — no recommendation stored]
```

**User benefit**: No change to lightweight workflows. Only full advisory runs are tracked.

---

## CLI Changes

### Updated Command Summary

| Command | Description | Change |
|---------|-------------|--------|
| (none) | Full analysis and recommendations | **Modified**: Also saves recommendation to ledger |
| `check` | Quick portfolio status check | No change |
| `confirm` | Confirm executed trades | **Modified**: Also matches trades against latest advice |
| `migrate` | Migrate legacy portfolio format | No change |
| `sim <ID>` | Simulate outcome of past advice | **New** |
| `sim --list` | List all stored recommendations | **New** |
| `review` | AI-assisted strategy review | **New** |
| `--help` | Show usage information | Updated with new commands |

---

## Success Metrics

### Piece 1: Recommendation Ledger — DONE when:
- [ ] Every full advisory run saves a recommendation record automatically
- [ ] Record includes: advice ID, timestamp, portfolio snapshot, market snapshot, actions, confidence
- [ ] `check` runs do NOT create records
- [ ] `confirm` command matches trades against the most recent unresolved advice
- [ ] Advice marked as accepted, partial, or skipped based on trade matching
- [ ] Records persist across sessions
- [ ] Records are human-readable (can be inspected manually)

### Piece 2: Simulation — DONE when:
- [ ] `sim <ID>` loads the advice record and calculates P&L to today
- [ ] Simulation uses current market prices vs prices at time of advice
- [ ] Transaction fees included in calculation
- [ ] Shows both simulated outcome and actual outcome side by side
- [ ] Shows clear verdict (advice was good/bad/neutral)
- [ ] `sim --list` shows all stored recommendations with summary
- [ ] List shows: ID, date, actions summary, outcome, simulated P&L
- [ ] Handles edge cases: stock splits, delisted stocks (graceful error)

### Piece 3: Learning Loop — DONE when:
- [ ] Scorecard data accumulates automatically from ledger + simulation results
- [ ] Scorecard tracks outcomes by decision type (buy/sell/hold) and reasoning category
- [ ] `review` command runs AI analysis over scorecard data
- [ ] AI identifies recurring patterns (minimum 8 recommendations before review is available)
- [ ] Suggested refinements are presented clearly with supporting data
- [ ] User can accept, reject, or modify each suggestion
- [ ] Accepted refinements are appended to strategy principles
- [ ] Rejected suggestions are not re-suggested in future reviews
- [ ] Strategy refinements are clearly separated from base strategy (own section)

---

## Dependencies

**Piece 1** (Recommendation Ledger): No dependencies — can be built independently
**Piece 2** (Simulation): Depends on Piece 1 (needs stored recommendations to simulate)
**Piece 3** (Learning Loop): Depends on Piece 1 and 2 (needs ledger data and simulation outcomes)

**Existing features affected**:
- Default advisory run: Modified to save recommendation record (additive, no breaking changes)
- `confirm` command: Modified to match trades against advice (additive)
- `strategy.txt`: Will gain a new `LEARNED REFINEMENTS` section over time

**No breaking changes** to existing features. All new functionality is additive.

---

## Implementation Sequence

Recommended build order:

1. **Piece 1 first** — Foundation for everything else. Low risk, high standalone value.
2. **Piece 2 second** — Requires Piece 1 data. Delivers the "was this advice good?" capability.
3. **Piece 3 last** — Requires enough data from Piece 1 and 2 to be meaningful. Can wait weeks/months until sufficient recommendation history exists.

---

## Future Enhancements (Not in Scope)

### Automated Backtesting
- Replay historical market data through the advisor to test strategy changes before going live
- Requires historical data storage beyond current free-tier sources

### Benchmark Comparison
- Compare advisor performance against simple benchmarks (buy-and-hold SPY, equal-weight top 3)
- Requires Piece 2 data accumulation over 6+ months

### Multi-Strategy Testing
- Run simulations with different strategy principles to compare approaches
- Requires significant recommendation history

---

## Rollback Plan

**If the feature causes issues**:

1. Recommendation ledger is stored in its own file — deleting the file removes all records with no impact on existing features
2. Strategy refinements are in a clearly marked section of `strategy.txt` — removing that section reverts to base strategy
3. New CLI commands (`sim`, `review`) are additive — removing them does not affect existing commands
4. No changes to portfolio data format — zero risk to position tracking

**Data safety**: All new data is stored separately from existing portfolio and narrative files. No existing data is modified.

---

## Approval

- [x] Change documented
- [ ] Solution reviewed and approved
- [ ] Piece 1 implementation complete
- [ ] Piece 2 implementation complete
- [ ] Piece 3 implementation complete
- [ ] All acceptance criteria met
- [ ] Documentation updated (Product Requirement updated to v3.0)

**Product Owner**: Tobes
**Implementation Target**: Piece 1 and 2 this sprint. Piece 3 after sufficient data accumulation.
**Priority**: MEDIUM (Enhancement — no existing functionality is broken)
**Estimated Effort**: Piece 1: 1 day | Piece 2: 1 day | Piece 3: 2 days

---

**END OF CHANGE REQUEST**