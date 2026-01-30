# CR006 Implementation Plan - Lot-Based Position Tracking

**Date**: January 30, 2026
**Status**: Ready for Review
**Estimated Phases**: 6

---

## Requirements Validation

### CR006 Review Summary
- **Problem**: Confirmed. Multiple purchases of same ticker create duplicate entries. Position lookups via dict comprehension (`{p['ticker']: p}`) silently drop earlier lots. Sellability validation is broken.
- **Proposed Solution**: Valid. Lot-based hierarchy is industry standard.
- **Dependencies**: None (foundational change).
- **Impact**: Touches every module that reads position data (7 files).

### Design Decision: Storage vs Compute
CR006 proposes storing `total_quantity` and `average_cost` in portfolio.json. **Recommendation: compute these at runtime only.** Rationale:
- If user manually edits a lot in JSON, stored aggregates become stale
- portfolio.json should be the **source of truth** (lots only)
- Aggregation is cheap and deterministic

**portfolio.json will store:**
```json
{
  "positions": [
    {
      "ticker": "MSFT",
      "lots": [
        {"quantity": 1.5, "purchase_price": 507.6, "purchase_date": "2025-11-18", "notes": "Initial position"},
        {"quantity": 1.0, "purchase_price": 434.0, "purchase_date": "2026-01-30"}
      ]
    },
    {
      "ticker": "NVDA",
      "lots": [
        {"quantity": 1.0, "purchase_price": 191.83, "purchase_date": "2026-01-30"}
      ]
    }
  ],
  "cash_available": 274.17,
  "last_updated": "2026-01-30"
}
```

**Runtime-computed fields** (in `consolidate_position()`):
- `total_quantity`: sum of lot quantities
- `average_cost`: weighted average of lot prices
- `total_pnl_percent`: based on average_cost vs current_price
- Per-lot: `days_held`, `is_sellable`, `unlock_date`, `pnl_percent`

---

## Architecture Overview

### New: Position Consolidation Layer (utils.py)

Add helper functions that convert the lot-based storage into consolidated position views used by all downstream code:

```
portfolio.json (lots)
    │
    ▼
consolidate_positions(positions, market_data)  ← NEW
    │
    ▼
[{ticker, total_quantity, average_cost, lots: [{...with computed fields}],
  sellable_quantity, locked_quantity, lock_status, ...}]
    │
    ▼
analyzer.py / ai_agent.py / display.py / event_detector.py
```

This means downstream code receives **consolidated position dicts** with both position-level aggregates and lot-level detail. Most existing code continues to work with minor field name changes.

### Files Modified

| File | Changes |
|------|---------|
| `utils.py` | New consolidation functions, updated validation |
| `analyzer.py` | Use consolidated positions, update FIFO/exit logic |
| `ai_agent.py` | Format consolidated positions with lot detail for AI |
| `display.py` | Consolidated view with lot breakdown |
| `advisor.py` | Lot-aware trade processing, migration command |
| `event_detector.py` | Use consolidated position lookups |

---

## Phase 1: Data Model & Consolidation (utils.py)

### 1a. New consolidation functions

Add to `utils.py`:

- **`consolidate_positions(raw_positions: list, min_hold_days: int = 30) -> list`**
  - Takes the lot-based positions list from portfolio.json
  - Groups by ticker
  - For each ticker: computes total_quantity, average_cost, sellable_quantity, locked_quantity
  - Enriches each lot with: days_held, is_sellable, unlock_date
  - Sorts lots by purchase_date (FIFO order)
  - Returns list of consolidated position dicts

- **`get_position_lock_status(position: dict) -> str`**
  - Returns: "SELLABLE", "LOCKED", or "PARTIAL_LOCK"
  - Based on lot sellability

- **`get_sellable_quantity(position: dict) -> float`**
  - Sums quantity of sellable lots (FIFO order)

### 1b. Update validation

- **`validate_portfolio()`**: Update to validate new lot-based structure
  - positions[].ticker required
  - positions[].lots required (list of lot dicts)
  - Each lot validated with existing `validate_position()` logic (rename to `validate_lot()`)

### 1c. Consolidated position dict shape

```python
{
    'ticker': 'MSFT',
    'total_quantity': 2.5,
    'average_cost': 478.08,
    'lots': [
        {
            'quantity': 1.5,
            'purchase_price': 507.6,
            'purchase_date': '2025-11-18',
            'days_held': 73,
            'is_sellable': True,
            'unlock_date': '2025-12-18',
            'pnl_percent': -14.6,  # added later when current_price available
            'notes': 'Initial position',
        },
        {
            'quantity': 1.0,
            'purchase_price': 434.0,
            'purchase_date': '2026-01-30',
            'days_held': 0,
            'is_sellable': False,
            'unlock_date': '2026-03-01',
            'pnl_percent': -0.1,
        }
    ],
    'sellable_quantity': 1.5,
    'locked_quantity': 1.0,
    'lock_status': 'PARTIAL_LOCK',  # SELLABLE | LOCKED | PARTIAL_LOCK
}
```

---

## Phase 2: Analyzer Updates (analyzer.py)

### 2a. `generate_market_context()`
- Call `consolidate_positions()` from utils to get grouped positions
- Build `position_analysis` list from consolidated positions (one entry per ticker)
- Each entry includes: ticker, total_quantity, average_cost, lots, sellable_quantity, lock_status
- Add current_price, rank, score, pnl_percent (position-level) from market data
- Per-lot: add pnl_percent using lot's purchase_price vs current_price

### 2b. `check_fifo_eligibility()`
- Refactor to work with consolidated positions (lots array per ticker)
- Return per-lot eligibility within each position

### 2c. `analyze_exit_signals()`
- Currently takes a single flat position dict
- Update to take a consolidated position (with lots)
- Stop-loss: check at **lot level** (any lot below threshold triggers signal)
- Profit target: check at **lot level**
- Sellability: report per-lot (which lots can be sold)

### 2d. Entry opportunities
- `held_tickers` set built from consolidated positions (already one ticker per entry, simpler)

---

## Phase 3: AI Prompt Updates (ai_agent.py)

### 3a. `_format_positions()`
- Show consolidated view: ticker, total_quantity, average_cost, overall P&L
- Include lot breakdown underneath each position
- Show FIFO sellability per lot
- Example output:
  ```
  MSFT: 2.5 shares total, avg cost $478.08, current $433.50, P&L -9.3%
    Lock status: PARTIAL_LOCK (1.5 sellable, 1.0 locked)
    Lot 1: 1.5 shares @ $507.60 (73d, -14.6%) SELLABLE [STOP LOSS]
    Lot 2: 1.0 shares @ $434.00 (0d, -0.1%) LOCKED (unlock 2026-03-01)
  ```

### 3b. `_format_holdings_for_cashflow()`
- Update to use consolidated positions
- Show sellable_quantity (not total_quantity) for SELL value calculations
- Per-lot breakdown for SELL proceeds

### 3c. `validate_actions()`
- Build position_lookup from consolidated positions (one entry per ticker, no overwrite bug)
- SELL validation: check against sellable_quantity, not total_quantity
- Proceeds calculation: use FIFO lot prices for accurate amounts

### 3d. `_build_earnings_calendar_section()`
- Deduplicate: one entry per ticker (not per lot)

### 3e. Prompt text
- Add instruction: "Positions show lot breakdown. When recommending SELL, specify quantity. FIFO is enforced — oldest sellable lots are sold first."
- Add consideration: "Lot-level P&L — individual lots may have different cost bases"

---

## Phase 4: Display Updates (display.py)

### 4a. `display_portfolio_status()`
- Consolidated table: one row per ticker
- Columns: Ticker, Total Qty, Avg Cost, Current, P&L, Status
- Under each position: indented lot rows (if multiple lots)
  ```
  MSFT     2.5   478.08   433.50   -9.3%   PARTIAL LOCK
    ├─ Lot 1: 1.5 @ 507.60 (73d, -14.6%)  SELLABLE [STOP LOSS]
    └─ Lot 2: 1.0 @ 434.00 (0d, -0.1%)    LOCKED (29d)
  ```
- Portfolio summary: "2 stocks" not "3 positions"
- Sellability: "1 partially sellable (MSFT: 1.5 of 2.5)"

### 4b. `display_quick_check()`
- Consolidated view (one line per ticker)
- Show lock_status instead of simple sellable/locked

### 4c. `display_material_events()`
- Position lookup from consolidated positions (no overwrite bug)
- Show total position context with lot detail

### 4d. `display_price_context()`
- One entry per ticker (deduplicated)

### 4e. `display_earnings_calendar()`
- One entry per ticker (deduplicated)

---

## Phase 5: Trade Processing & Migration (advisor.py)

### 5a. `process_trade_input()` - BOUGHT
- Find existing position for ticker, or create new one
- Append lot to position's lots array (don't create duplicate position)
- Lot gets: quantity, purchase_price, purchase_date

### 5b. `process_trade_input()` - SOLD
- Find position by ticker
- FIFO: sell from oldest lot first
- If selling partial lot: reduce lot quantity
- If selling entire lot: remove lot from array
- If selling across lots: consume oldest first, then next
- If position has no lots left: remove position entirely
- Add proceeds to cash

### 5c. Migration command: `cmd_migrate()`
- New CLI command: `python advisor.py migrate`
- Steps:
  1. Load current portfolio.json
  2. Check if already in lot-based format (has 'lots' key) — skip if so
  3. Back up to portfolio.json.backup
  4. Group flat positions by ticker
  5. For each group: create position with lots array, sorted by purchase_date
  6. Preserve notes and other fields per lot
  7. Save new portfolio.json
  8. Validate the result
  9. Print summary

### 5d. Auto-detection
- `load_portfolio()` should detect old format and warn user to run migrate
- Or: auto-migrate on load (simpler, with backup)

---

## Phase 6: Event Detector Updates (event_detector.py)

### 6a. `detect_material_events()`
- Build held_tickers from consolidated positions (one per ticker)

### 6b. `build_event_analysis()`
- Position lookup from consolidated positions (no overwrite bug)
- `_build_position_context()`: show total position + lot breakdown
- Include sellable_quantity in context

---

## Testing Strategy

### Unit Tests
1. **Consolidation**: Multiple lots grouped correctly, averages calculated
2. **Single lot**: Position with one lot works identically to before
3. **FIFO sell**: Oldest lot consumed first, partial lot handling
4. **Sell across lots**: Selling more than oldest lot quantity
5. **Validation**: New format validates correctly, old format rejected with migrate hint
6. **Migration**: Old format converts to new format correctly
7. **Empty portfolio**: No positions works fine

### Integration Tests
8. **Display**: Consolidated view, lot breakdown, correct counts
9. **AI prompt**: Consolidated positions in prompt, no duplicates
10. **Event detection**: No duplicate events for same ticker
11. **Full flow**: Load → analyze → recommend → display (end-to-end)

### Manual Verification
12. Run migration on actual portfolio.json
13. Run full advisor flow and verify output

---

## Rollback Plan

1. portfolio.json.backup created before migration
2. All code changes in git (revert commit if needed)
3. Auto-migration detects format, so old code + old data still works

---

## Implementation Order

```
Phase 1 (utils.py)     → Foundation: consolidation + validation
Phase 2 (analyzer.py)  → Core: consolidated analysis pipeline
Phase 3 (ai_agent.py)  → AI: lot-aware prompts + validation
Phase 4 (display.py)   → UI: consolidated display
Phase 5 (advisor.py)   → CLI: trade processing + migration
Phase 6 (event_detector.py) → Events: fix position lookups
```

Each phase builds on the previous. Phase 1 must be complete before any other phase.
