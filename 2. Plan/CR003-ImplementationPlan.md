# CR003 Implementation Plan - Add Earnings Calendar to Market Data

**CR Reference**: [CR003-Add Earnings Calendar to Market Data](../3.%20ChangeLog/CR003%20-%20Add%20Earnings%20Calendar%20to%20Market%20Data.md)
**Created**: January 27, 2026
**Status**: Complete

---

## Overview

This plan implements earnings calendar awareness to prevent strategy-violating trades around earnings dates. The implementation leverages existing `_get_earnings_date()` infrastructure and adds:
1. Days-until calculation with restriction flags
2. AI prompt section for earnings calendar
3. Display output for earnings warnings
4. Context integration for position/opportunity data

---

## Phase 1: Data Layer ✅ COMPLETED

**Goal**: Calculate earnings proximity from existing data

| ID | Task | File | Status |
|----|------|------|--------|
| 1.1 | Add `calculate_earnings_proximity()` function | `data_collector.py` | ✅ |
| 1.2 | Integrate into `fetch_all_market_data()` | `data_collector.py` | ✅ |
| 1.3 | Test earnings proximity calculation | Manual | ✅ |

**Deliverables**:
- [x] Function returns `{date, days_until, sell_restricted, buy_restricted, status}`
- [x] Handles None/invalid dates gracefully
- [x] Past dates and >90 days return None

**Completed**: January 27, 2026

---

## Phase 2: Analyzer Integration ✅ COMPLETED

**Goal**: Pass earnings data through to context

| ID | Task | File | Status |
|----|------|------|--------|
| 2.1 | Add `earnings` field to position_analysis | `analyzer.py` | ✅ |
| 2.2 | Add `earnings` field to entry_opportunities | `analyzer.py` | ✅ |
| 2.3 | Verify earnings data flows to context | Manual | ✅ |

**Deliverables**:
- [x] Positions include earnings proximity data
- [x] Entry opportunities include earnings proximity data

**Completed**: January 27, 2026

---

## Phase 3: AI Prompt Enhancement ✅ COMPLETED

**Goal**: AI sees earnings calendar with restrictions

| ID | Task | File | Status |
|----|------|------|--------|
| 3.1 | Add `_format_earnings_calendar()` helper | `ai_agent.py` | ✅ |
| 3.2 | Add earnings calendar section to `build_prompt()` | `ai_agent.py` | ✅ |
| 3.3 | Add CRITICAL EARNINGS RULES section | `ai_agent.py` | ✅ |
| 3.4 | Test AI receives earnings context | Manual | ✅ |

**Deliverables**:
- [x] Imminent earnings (<7 days) show with restrictions
- [x] Upcoming earnings (8-30 days) listed as safe
- [x] Clear DO NOT SELL/BUY rules in prompt

**Completed**: January 27, 2026

---

## Phase 4: Display Output ✅ COMPLETED

**Goal**: User sees earnings warnings in terminal

| ID | Task | File | Status |
|----|------|------|--------|
| 4.1 | Add earnings column to market snapshot | `display.py` | ✅ |
| 4.2 | Add `display_earnings_calendar()` function | `display.py` | ✅ |
| 4.3 | Update `display_full_dashboard()` to include earnings | `display.py` | ✅ |
| 4.4 | Test display output | Manual | ✅ |

**Deliverables**:
- [x] Market snapshot shows earnings column with color coding
- [x] Separate earnings calendar section with restrictions
- [x] Imminent earnings highlighted in red/yellow

**Completed**: January 27, 2026

---

## Phase 5: Testing & Validation ✅ COMPLETED

**Goal**: Verify AI respects earnings restrictions

| ID | Task | File | Status |
|----|------|------|--------|
| 5.1 | Run advisor with MSFT (2 days to earnings) | Manual | ✅ |
| 5.2 | Verify AI does NOT recommend selling MSFT | Manual | ✅ |
| 5.3 | Verify AI mentions earnings in reasoning | Manual | ✅ |
| 5.4 | Test with stock >30 days from earnings | Manual | ✅ |
| 5.5 | Test with stock with no earnings data | Manual | ✅ |

**Deliverables**:
- [x] AI respects 3-day sell blackout
- [x] AI respects 7-day buy restriction
- [x] AI reasoning references earnings timing
- [x] No regressions in existing functionality

**Completed**: January 27, 2026

**Test Results**:
- MSFT (2 days to earnings): AI recommended HOLD instead of SELL
- AI reasoning: "MSFT earnings in 2 days triggers immutable 3-day blackout rule"
- META (2 days): Marked as NO BUY in display
- NVDA (30 days), GOOGL (9 days): Correctly shown as safe/upcoming

---

## Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `data_collector.py` | 1 | Add `calculate_earnings_proximity()` |
| `analyzer.py` | 2 | Add `earnings` to context |
| `ai_agent.py` | 3 | Add `_format_earnings_calendar()` and prompt section |
| `display.py` | 4 | Add earnings display functions |

---

## Dependencies

### Phase Dependencies
```
Phase 1 (Data) -> Phase 2 (Analyzer) -> Phase 3 (AI) & Phase 4 (Display)
```
- Phase 2 depends on Phase 1 (needs earnings proximity data)
- Phases 3 and 4 depend on Phase 2 (need context with earnings)
- Phases 3 and 4 can run in parallel

### External Dependencies
- None new (existing yfinance already provides earnings dates)

---

## Testing Checklist

### Phase 1
- [ ] `calculate_earnings_proximity("2026-01-29")` returns `{days_until: 2, sell_restricted: True, ...}`
- [ ] `calculate_earnings_proximity(None)` returns `None`
- [ ] `calculate_earnings_proximity("2025-01-01")` returns `None` (past date)

### Phase 2
- [ ] Context includes `earnings` field for positions
- [ ] Context includes `earnings` field for opportunities

### Phase 3
- [ ] AI prompt contains "EARNINGS CALENDAR" section
- [ ] MSFT shows with "DO NOT SELL" warning
- [ ] AI reasoning mentions earnings timing

### Phase 4
- [ ] Market snapshot has Earnings column
- [ ] Earnings calendar section displays correctly
- [ ] Color coding works (red for <=3d, yellow for <=7d)

### Phase 5
- [ ] AI does NOT recommend selling MSFT (2 days to earnings)
- [ ] AI explains why it's holding despite rank drop
- [ ] Stocks with no imminent earnings can be traded normally

---

## Rollback Plan

### Quick Rollback
```python
# In data_collector.py - comment out:
# earnings_proximity = calculate_earnings_proximity(earnings_date)
# result['tickers'][ticker]['earnings'] = earnings_proximity

# In ai_agent.py - comment out:
# earnings_text = _format_earnings_calendar(context)
# Remove EARNINGS CALENDAR section from prompt

# In display.py - comment out:
# display_earnings_calendar(context)
```

**Impact**: System returns to pre-CR003 behavior (no earnings awareness)
**Rollback time**: < 5 minutes

---

## Acceptance Criteria

### CR003 Complete When:
- [x] Phase 1: Earnings proximity calculated correctly
- [x] Phase 2: Earnings data flows to context
- [x] Phase 3: AI sees earnings calendar with restrictions
- [x] Phase 4: User sees earnings warnings in output
- [x] Phase 5: AI respects earnings blackout rules
- [x] No regressions in existing functionality

---

## Progress Tracking

| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| 1 | ✅ Completed | 3/3 | Data layer - calculate_earnings_proximity() |
| 2 | ✅ Completed | 3/3 | Analyzer integration - earnings in context |
| 3 | ✅ Completed | 4/4 | AI prompt enhancement - _format_earnings_calendar() |
| 4 | ✅ Completed | 4/4 | Display output - display_earnings_calendar() |
| 5 | ✅ Completed | 5/5 | Testing & validation - AI respects blackout |

---

**Last Updated**: January 27, 2026
**Completed**: January 27, 2026
