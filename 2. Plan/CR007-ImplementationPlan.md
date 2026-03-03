# CR007 Implementation Plan: Recommendation Ledger, Simulation & Learning Loop

**Created**: March 3, 2026
**Status**: In Progress
**CR Reference**: `3. ChangeLog/CR007 - Recommendation Ledger, Simulation & Learning Loop`

---

## Summary

CR007 adds three connected capabilities:
1. **Recommendation Ledger** - Auto-save every recommendation with portfolio/market snapshots
2. **Simulation Command** - Evaluate past advice by comparing to current prices
3. **Learning Loop** (Phase 3) - AI-assisted pattern analysis for strategy refinement

**Verdict: CR007 is well-designed and integrates cleanly with the current system.** The existing `narrative_manager.py` provides an excellent template, and all required data is already available at recommendation time.

---

## Implementation Phases

### Phase 1: Ledger Foundation
- [x] Create `recommendations_manager.py` module
- [x] Modify `cmd_run()` to record recommendations
- [x] Add `sim --list` command

### Phase 2: Simulation Engine
- [x] Implement P&L calculation logic (in recommendations_manager.py)
- [x] Add `sim <ID>` command with verdict display
- [x] Add display functions for simulation results

### Phase 3: Trade Matching
- [x] Modify `process_trade_input()` to match trades to recommendations
- [x] Track outcomes: accepted/partial/skipped

### Phase 4: Polish & Future Prep
- [x] Add pruning logic (in recommendations_manager.py)
- [x] Add `sim --summary` display
- [x] Add stub `review` command

---

## Files to Create/Modify

### NEW: `App/src/recommendations_manager.py` ✅ CREATED

Core functions implemented:
```
load_ledger() / save_ledger()
record_recommendation(portfolio, context, recommendation, market_data)
match_trade_to_recommendations(trade_type, ticker, quantity, price, date)
simulate_recommendation(rec_id, current_prices)
calculate_hypothetical_pnl(recommendation, prices_then, prices_now)
determine_verdict(pnl_followed, pnl_ignored, threshold=50)
prune_ledger(ledger, max_entries=100)
list_recommendations(limit, filters)
get_ledger_summary()
fetch_current_prices_for_simulation(tickers)
```

### MODIFY: `App/src/advisor.py`

1. **Add CLI commands** to argparser choices:
   - `sim` - simulation command
   - `review` - learning loop (stub)

2. **In `cmd_run()`** (after line 105):
   ```python
   from .recommendations_manager import record_recommendation
   try:
       rec_id = record_recommendation(portfolio, context, recommendation, market_data)
       print(colorize(f"  Recommendation recorded: {rec_id}", Colors.DIM))
   except Exception as e:
       print(colorize(f"  Warning: Failed to record recommendation: {e}", Colors.YELLOW))
   ```

3. **In `process_trade_input()`** (after successful trade):
   ```python
   from .recommendations_manager import match_trade_to_recommendations
   try:
       matched_id = match_trade_to_recommendations(action, ticker, qty, price, date)
       if matched_id:
           return f"{message} (matched to {matched_id})"
   except Exception:
       pass  # Silent failure - matching is optional
   ```

4. **Add new command functions**:
   - `cmd_sim(args)` - handles sim, sim --list, sim --summary
   - `cmd_review(args)` - stub for Phase 3

### MODIFY: `App/src/display.py`

Add display functions:
- `display_recommendation_list(recs)` - table of past recommendations
- `display_simulation_results(rec, simulation)` - detailed sim output
- `display_ledger_summary(stats)` - aggregate statistics

### NEW: `App/config/recommendations_ledger.json`

Auto-created on first run. Schema:
```json
{
  "version": "1.0",
  "last_updated": "...",
  "statistics": { "total_recommendations": 0, ... },
  "recommendations": [
    {
      "id": "rec_20260303_160829",
      "timestamp": "...",
      "outcome": "pending|accepted|partial|skipped",
      "portfolio_snapshot": { positions, cash, total_value },
      "market_snapshot": { top_3, rankings with prices },
      "recommendation": { actions, confidence, strategy },
      "execution": { matched trades },
      "simulation": { calculated P&L, verdict }
    }
  ]
}
```

---

## Key Design Decisions

### Recommendation ID Format
`rec_YYYYMMDD_HHMMSS` - sortable, human-readable, collision-resistant

### Outcome States
`pending` → `accepted` (all actions matched) | `partial` (some matched) | `skipped` (none matched after 7 days)

### Simulation Verdict Logic
- **GOOD**: Following advice beat ignoring by > $50
- **BAD**: Ignoring beat following by > $50
- **NEUTRAL**: Within $50 either way

### Trade Matching Window
7 days - recommendations older than 7 days without full match are finalized as partial/skipped

### Pruning Strategy
- Max 100 entries, 180-day retention
- Never prune pending recommendations
- Always keep 20 most recent
- Preserve GOOD verdicts for learning

---

## Verification Plan

### Test Phase 1 (Ledger)
1. Run `python -m src.advisor` - verify ledger file created
2. Run again - verify new entry appended
3. Check JSON structure matches schema

### Test Phase 2 (Simulation)
1. Run `python -m src.advisor sim --list` - shows recorded recommendations
2. Run `python -m src.advisor sim` - simulates most recent
3. Verify P&L calculation against manual calculation

### Test Phase 3 (Matching)
1. Run advisor, get recommendation
2. Run `python -m src.advisor confirm` and enter matching trade
3. Verify recommendation outcome updated to "accepted"
4. Run `sim --list` to confirm status change

### Test Phase 4 (Pruning)
1. Add 110+ test entries
2. Verify pruning keeps 100 and preserves pending/GOOD entries

---

## Edge Cases Handled

| Case | Handling |
|------|----------|
| Stock splits | yfinance returns split-adjusted prices |
| Delisted stocks | Mark simulation incomplete, use last known price |
| Fractional shares | All quantities stored/calculated as floats |
| Multiple recs same day | Unique IDs include time component |
| Partial execution | Outcome = "partial" with reason noted |

---

## Estimated Effort

| Phase | Scope | Estimate |
|-------|-------|----------|
| Phase 1 | Ledger foundation | 2-3 hours |
| Phase 2 | Simulation engine | 2-3 hours |
| Phase 3 | Trade matching | 1-2 hours |
| Phase 4 | Polish & pruning | 1 hour |
| **Total** | | **6-9 hours** |

---

## Dependencies

- Phase 2 depends on Phase 1 (needs stored recommendations)
- Phase 3 depends on Phase 1 (needs ledger to update)
- Learning Loop (future) depends on accumulated data (20+ recommendations with verdicts)

No external dependencies - uses existing yfinance for current prices.

---

## Progress Log

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| 2026-03-03 | Phase 1 | Complete | Created recommendations_manager.py with all core functions |
| 2026-03-03 | Phase 2 | Complete | Added sim command with --list, --summary, and ID simulation |
| 2026-03-03 | Phase 3 | Complete | Added trade matching in process_trade_input() |
| 2026-03-03 | Phase 4 | Complete | Added review command stub, all features integrated |
