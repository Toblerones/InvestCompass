# Change Request: CR003 - Add Earnings Calendar to Market Data

**Date**: January 27, 2026
**Status**: Complete
**Priority**: URGENT
**Severity**: Critical (Risk Management Bug)
**Affects**: `data_collector.py`, `analyzer.py`, `ai_agent.py`, `display.py`
**Completed**: January 27, 2026

---

## Code Review Audit (January 27, 2026)

**Reviewer**: Claude Code Assistant

### Issues Found in Original CR003

| Issue | Original | Correction |
|-------|----------|------------|
| 1. Wrong integration function | `fetch_market_data()` | Should be `fetch_all_market_data()` (line 841) |
| 2. Existing code not acknowledged | N/A | `_get_earnings_date()` already exists (line 233) |
| 3. Earnings data already collected | "Not fetched" | IS fetched via `get_fundamentals()` but not surfaced |
| 4. Function signature mismatch | `display_market_snapshot(market_data, rankings)` | Actual: `display_market_snapshot(context: dict)` |
| 5. Helper naming convention | `format_earnings_calendar_for_prompt()` | Should be `_format_earnings_calendar()` |
| 6. Prompt template references | `load_strategy_principles()` | Strategy is passed as parameter |

### Key Finding

Earnings dates ARE being fetched (`get_fundamentals()` returns `earnings_date`), but:
- No "days until" calculation
- Not formatted for AI prompt
- No restriction logic applied

Verified via test:
```
MSFT: earnings_date = 2026-01-29 (2 days away!)
NVDA: earnings_date = 2026-02-26 (30 days away)
```

### Corrected Approach

Instead of creating new data fetch, leverage existing infrastructure:
1. Extend existing data with `days_until` calculation
2. Add `_format_earnings_calendar()` helper to `ai_agent.py`
3. Add earnings display to `display.py`
4. Update `build_prompt()` to include earnings section

---

## Problem Description

The AI recommendation engine currently lacks visibility into upcoming earnings dates, causing it to violate critical timing rules defined in the investment strategy. This creates substantial risk for the user.

**Discovered Issue**:
- AI recommended SELL MSFT when earnings were 2 days away
- Strategy explicitly prohibits: "Avoid selling within 3 days of earnings (gap risk)"
- Strategy explicitly prohibits: "Avoid buying within 7 days of earnings (volatility risk)"
- AI had no way to know about the earnings timing

**Root Cause**:
Earnings dates are **structured calendar data**, not narrative news. While news might mention "earnings uncertainty," it doesn't consistently provide explicit dates like "earnings on Jan 28." The system fetches news but doesn't fetch the earnings calendar, leaving AI blind to critical timing information.

**Risk Impact**:
- **Selling before earnings**: May miss runup OR may avoid gap down (high uncertainty)
- **Buying before earnings**: Exposed to earnings volatility immediately after entry
- **Strategy violation**: User's explicitly defined risk rules are not enforced
- **User trust**: Recommendations that violate stated strategy erode confidence

**Example of impact**:
```
Current recommendation:
"SELL MSFT - all shares
 Reasoning: Rank dropped to #4, approaching stop-loss"

Missing context:
"⚠️  MSFT EARNINGS IN 2 DAYS - Selling now violates 3-day rule"
```

---

## Current Behavior

### Data Collection
```python
# In data_collector.py - what's ACTUALLY happening:

# Line 233-249: _get_earnings_date() DOES exist and fetches earnings
def _get_earnings_date(info: dict) -> Optional[str]:
    """Extract next earnings date from stock info."""
    earnings_dates = info.get('earningsTimestamp')
    if earnings_dates:
        return datetime.fromtimestamp(earnings_dates).strftime('%Y-%m-%d')
    # ... fallback logic

# Line 213: get_fundamentals() DOES return earnings_date
result[ticker] = {
    'pe_ratio': trailing_pe,
    'revenue_growth_yoy': revenue_growth,
    'earnings_date': _get_earnings_date(info),  # ✅ COLLECTED
    # ...
}

# ❌ PROBLEM: earnings_date exists but is NOT:
#    - Calculated for "days_until"
#    - Passed to AI prompt
#    - Used for restriction logic
```

### AI Prompt
```
MARKET ANALYSIS:
- MSFT: Rank #4, Score 5.7, P/E 33.1
- Price: $470.28, RSI: 45.7
- News: "Earnings uncertainty" theme

❌ NO EARNINGS CALENDAR SECTION
```

### AI Output
```
Recommendation: SELL MSFT
Reasoning: Rank dropped, approaching stop-loss, held 70 days

❌ NO AWARENESS of earnings in 2 days
❌ NO WARNING about timing risk
```

---

## Expected Behavior

### Data Collection
```python
# In data_collector.py - what should be fetched:

def fetch_market_data(tickers):
    data = {}
    earnings_calendar = get_earnings_calendar(tickers)  # NEW
    
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        data[ticker] = {
            "price": stock.info['currentPrice'],
            "pe_ratio": stock.info.get('trailingPE'),
            "revenue_growth": ...,
            "earnings": earnings_calendar.get(ticker)  # NEW
        }
    return data

def get_earnings_calendar(tickers):
    """Fetch upcoming earnings dates for all tickers"""
    calendar = {}
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        try:
            # yfinance provides earnings date in calendar attribute
            earnings_dates = stock.calendar
            if earnings_dates is not None and 'Earnings Date' in earnings_dates:
                next_earnings = earnings_dates['Earnings Date']
                
                # Calculate days until earnings
                if isinstance(next_earnings, list):
                    next_earnings = next_earnings[0]  # Take first date if range
                
                days_until = (next_earnings - datetime.now()).days
                
                calendar[ticker] = {
                    "date": next_earnings.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                    "confirmed": True
                }
        except Exception as e:
            # If data unavailable, set to None
            calendar[ticker] = None
    
    return calendar
```

### AI Prompt
```
MARKET ANALYSIS:
- MSFT: Rank #4, Score 5.7, P/E 33.1
- Price: $470.28, RSI: 45.7
- News: "Earnings uncertainty" theme

✅ UPCOMING EVENTS CALENDAR:

MSFT:
  ⚠️  EARNINGS in 2 DAYS (Jan 28, 2026)
  CRITICAL: Strategy prohibits SELL within 3 days of earnings
  CRITICAL: Strategy prohibits BUY within 7 days of earnings
  Reason: Gap risk, volatility, potential runup/rundown

NVDA:
  Earnings in 18 days (Feb 13, 2026)
  Status: SAFE for entry/exit decisions

GOOGL:
  No earnings in next 30 days
  Status: SAFE for entry/exit decisions
```

### AI Output
```
Recommendation: HOLD MSFT (do not sell)
Reasoning: 
  While MSFT rank dropped to #4 and P&L at -7.4%, earnings 
  are in 2 days (Jan 28). Strategy prohibits selling within 
  3 days of earnings due to gap risk and potential runup miss.
  
  Action: Wait until Jan 29 (after earnings) to reassess.
  If earnings disappoint, execute exit then. If earnings beat,
  reassess whether to hold despite rank #4.

Alternative: 
  If urgently need to exit (e.g., approaching -10% stop-loss),
  could sell now but user must accept risk of missing earnings
  runup or avoiding gap down. Recommend waiting.

✅ AWARENESS of earnings timing
✅ RECOMMENDATION respects strategy rules
```

---

## Proposed Solution (CORRECTED)

### Component 1: Earnings Calendar Calculation

**File**: `data_collector.py`

**Approach**: Leverage existing `_get_earnings_date()` and add days_until calculation.

**New function** (add after line 249):
```python
def calculate_earnings_proximity(earnings_date_str: str) -> dict:
    """
    Calculate days until earnings and determine trading restrictions.

    Args:
        earnings_date_str: Date string in YYYY-MM-DD format (from fundamentals)

    Returns:
        Dict with earnings proximity info or None if invalid
    """
    if not earnings_date_str:
        return None

    try:
        earnings_date = datetime.strptime(earnings_date_str, '%Y-%m-%d').date()
        today = date.today()
        days_until = (earnings_date - today).days

        # Ignore past dates or very far future (>90 days)
        if days_until < 0 or days_until > 90:
            return None

        # Determine restrictions
        sell_restricted = days_until <= 3  # 3-day rule
        buy_restricted = days_until <= 7   # 7-day rule

        return {
            'date': earnings_date_str,
            'days_until': days_until,
            'sell_restricted': sell_restricted,
            'buy_restricted': buy_restricted,
            'status': 'IMMINENT' if days_until <= 7 else 'UPCOMING' if days_until <= 30 else 'SAFE'
        }
    except (ValueError, TypeError):
        return None
```

**Integration into `fetch_all_market_data()`** (modify line 892-899):
```python
# In fetch_all_market_data(), after building result['tickers'][ticker]:

for ticker in tickers:
    # Existing code...
    fundamentals_data = fundamentals.get(ticker, {})

    # NEW: Calculate earnings proximity from existing fundamentals data
    earnings_date = fundamentals_data.get('earnings_date')
    earnings_proximity = calculate_earnings_proximity(earnings_date)

    result['tickers'][ticker] = {
        'price': prices.get(ticker, {}),
        'fundamentals': fundamentals_data,
        'technicals': technicals.get(ticker, {}),
        'price_context': price_context.get(ticker, {}),
        'news': news.get(ticker, {"themes": [], "raw_articles": [], "stats": {}}),
        'earnings': earnings_proximity,  # NEW
    }
```

---

### Component 2: AI Prompt Enhancement (CORRECTED)

**File**: `ai_agent.py`

**Approach**: Follow existing helper naming convention (`_format_*`) and integrate with current `build_prompt()` structure.

**New helper function** (add after `_format_price_context()` around line 394):
```python
def _format_earnings_calendar(context: dict) -> str:
    """
    Format earnings calendar with trading restrictions for AI prompt.

    Args:
        context: Market context containing positions and opportunities with earnings data

    Returns:
        Formatted earnings calendar string
    """
    positions = context.get('current_positions', [])
    opportunities = context.get('entry_opportunities', [])

    imminent = []  # <= 7 days (restricted)
    upcoming = []  # 8-30 days (safe)
    none = []      # No data or > 30 days

    # Check held positions
    for pos in positions:
        ticker = pos.get('ticker', '')
        earnings = pos.get('earnings')
        if earnings:
            if earnings['days_until'] <= 7:
                imminent.append((ticker, earnings, 'HELD'))
            elif earnings['days_until'] <= 30:
                upcoming.append((ticker, earnings))
            else:
                none.append(ticker)
        else:
            none.append(ticker)

    # Check entry opportunities
    for opp in opportunities:
        ticker = opp.get('ticker', '')
        earnings = opp.get('earnings')
        if earnings:
            if earnings['days_until'] <= 7:
                imminent.append((ticker, earnings, 'OPPORTUNITY'))
            elif earnings['days_until'] <= 30:
                upcoming.append((ticker, earnings))
            else:
                none.append(ticker)
        else:
            none.append(ticker)

    lines = []

    # Imminent earnings - critical restrictions
    if imminent:
        lines.append("⚠️  IMMINENT EARNINGS (Trading Restricted):")
        for ticker, earnings, position_type in imminent:
            days = earnings['days_until']
            date_str = earnings['date']
            lines.append(f"  {ticker}: {date_str} ({days} days)")
            if earnings.get('sell_restricted'):
                lines.append(f"    ⛔ DO NOT SELL - Within 3-day blackout (gap risk)")
            if earnings.get('buy_restricted'):
                lines.append(f"    ⛔ DO NOT BUY - Within 7-day volatility window")
            lines.append(f"    Action: HOLD and reassess after earnings")
        lines.append("")

    # Upcoming earnings - informational
    if upcoming:
        lines.append("📅 Upcoming Earnings (Safe to Trade):")
        for ticker, earnings in upcoming:
            lines.append(f"  {ticker}: {earnings['date']} ({earnings['days_until']} days)")
        lines.append("")

    # No near-term earnings
    if none:
        lines.append(f"✓ No Near-Term Earnings: {', '.join(none)}")

    return "\n".join(lines) if lines else "No earnings data available."
```

**Update `build_prompt()`** (add after PRICE CONTEXT section, around line 121):
```python
    # In build_prompt(), add after price_context_text:

    # Format earnings calendar
    earnings_text = _format_earnings_calendar(context)

    # Then add to prompt template:
    prompt = f"""...

PRICE CONTEXT (30-day performance vs market):
{price_context_text}

EARNINGS CALENDAR:
{earnings_text}

CRITICAL EARNINGS RULES (IMMUTABLE - override other considerations):
1. DO NOT SELL within 3 days before earnings
   - Gap risk: may miss runup or avoid crash
   - Wait for post-earnings clarity

2. DO NOT BUY within 7 days before earnings
   - High volatility around earnings
   - Entry price likely better after event

3. Exception: If approaching -10% stop-loss AND earnings imminent:
   - Warn user explicitly about timing conflict
   - Recommend waiting unless stop-loss breach is certain

ONGOING NARRATIVES:
...
"""
```

---

### Component 3: Output Display Enhancement (CORRECTED)

**File**: `display.py`

**Approach**: Match existing function signature `display_market_snapshot(context: dict)` and add earnings column.

**Update `display_market_snapshot()`** (modify around line 202-232):
```python
def display_market_snapshot(context: dict) -> None:
    """Display market snapshot with rankings and earnings warnings."""
    print_header("MARKET SNAPSHOT")

    rankings = context.get('rankings', {})
    # ... existing code ...

    # Updated header with Earnings column
    header = f"{'Rank':<6}{'Ticker':<8}{'Score':>8}{'P/E':>10}{'RevGrwth':>10}{'RSI':>8}{'Earnings':>10}{'Status':>12}"
    print(colorize(header, Colors.BOLD))
    print_divider()

    sorted_rankings = sorted(rankings.items(), key=lambda x: x[1].get('rank', 99))

    for ticker, data in sorted_rankings[:10]:
        # ... existing rank, score, fundamentals, technicals ...

        # NEW: Format earnings info
        earnings = data.get('earnings')
        if earnings:
            days = earnings['days_until']
            if days <= 3:
                earnings_str = colorize(f"⚠️ {days}d", Colors.RED)
            elif days <= 7:
                earnings_str = colorize(f"⚠️ {days}d", Colors.YELLOW)
            elif days <= 30:
                earnings_str = f"{days}d"
            else:
                earnings_str = "-"
        else:
            earnings_str = "-"

        print(f"{rank_str:<14}{ticker:<8}{score:>8.1f}{pe:>10.1f}{rev_growth:>9.1f}%{rsi:>8.1f}{earnings_str:>10}{status:>20}")
```

**Add new `display_earnings_calendar()` function** (after `display_price_context()`):
```python
def display_earnings_calendar(context: dict) -> None:
    """
    Display earnings calendar with trading restrictions.

    Args:
        context: Market context from analyzer
    """
    print_header("EARNINGS CALENDAR")

    positions = context.get('current_positions', [])
    opportunities = context.get('entry_opportunities', [])

    has_imminent = False

    # Check positions for imminent earnings
    for pos in positions:
        earnings = pos.get('earnings')
        if earnings and earnings['days_until'] <= 7:
            if not has_imminent:
                print()
                print(colorize("  ⚠️  IMMINENT EARNINGS (Trading Restricted):", Colors.YELLOW + Colors.BOLD))
                has_imminent = True

            ticker = pos.get('ticker', '')
            days = earnings['days_until']
            date_str = earnings['date']

            restriction = ""
            if earnings.get('sell_restricted'):
                restriction = colorize("NO SELL", Colors.RED)
            if earnings.get('buy_restricted'):
                restriction += " " + colorize("NO BUY", Colors.YELLOW) if restriction else colorize("NO BUY", Colors.YELLOW)

            print(f"    {ticker}: {date_str} ({days} days) [{restriction}]")

    # Check opportunities for imminent earnings
    for opp in opportunities:
        earnings = opp.get('earnings')
        if earnings and earnings['days_until'] <= 7:
            if not has_imminent:
                print()
                print(colorize("  ⚠️  IMMINENT EARNINGS (Trading Restricted):", Colors.YELLOW + Colors.BOLD))
                has_imminent = True

            ticker = opp.get('ticker', '')
            days = earnings['days_until']
            date_str = earnings['date']

            print(f"    {ticker}: {date_str} ({days} days) [{colorize('NO BUY', Colors.YELLOW)}]")

    if not has_imminent:
        print()
        print(colorize("  ✓ No imminent earnings - all tickers safe for trading", Colors.GREEN))
```

**Update `display_full_dashboard()`** (add after `display_price_context()`):
```python
def display_full_dashboard(portfolio: dict, context: dict, recommendation: dict) -> None:
    # ... existing code ...
    display_news(context)
    display_price_context(context)
    display_earnings_calendar(context)  # NEW
    display_recommendations(recommendation)
    # ...
```

---

### Component 4: Analyzer Context Integration

**File**: `analyzer.py`

**Approach**: Add earnings data to position_analysis and entry_opportunities in `generate_market_context()`.

**Update `generate_market_context()`** (modify around line 450-491):
```python
def generate_market_context(market_data: dict, portfolio: dict, config: dict) -> dict:
    # ... existing code ...

    for pos in positions:
        ticker = pos.get('ticker', '')
        ticker_data = market_data.get('tickers', {}).get(ticker, {})

        # ... existing analysis ...

        # NEW: Get earnings data
        earnings = ticker_data.get('earnings')

        position_analysis.append({
            'ticker': ticker,
            # ... existing fields ...
            'return_30d': price_ctx.get('return_30d', 0),
            'relative_performance': price_ctx.get('relative_performance', 0),
            'trend': price_ctx.get('trend', 'UNKNOWN'),
            'earnings': earnings,  # NEW
        })

    # ... entry opportunities ...

    for ticker in top_3:
        if ticker not in held_tickers:
            ticker_data = market_data.get('tickers', {}).get(ticker, {})

            # NEW: Get earnings data
            earnings = ticker_data.get('earnings')

            entry_opportunities.append({
                'ticker': ticker,
                # ... existing fields ...
                'return_30d': price_ctx.get('return_30d', 0),
                'relative_performance': price_ctx.get('relative_performance', 0),
                'trend': price_ctx.get('trend', 'UNKNOWN'),
                'earnings': earnings,  # NEW
            })
```

---

## Implementation Details

### Data Source: yfinance

**yfinance earnings data access**:
```python
import yfinance as yf

stock = yf.Ticker("MSFT")

# Method 1: calendar attribute (recommended)
calendar = stock.calendar
# Returns: {'Earnings Date': Timestamp('2026-01-28 00:00:00')}
# or: {'Earnings Date': [Timestamp(...), Timestamp(...)]} for date ranges

# Method 2: earnings_dates attribute (historical)
earnings_history = stock.earnings_dates
# Returns: DataFrame of historical earnings dates
```

**Handling edge cases**:
```python
# Case 1: No earnings data available
if cal_data is None:
    return None

# Case 2: Date range instead of single date
if isinstance(earnings_date, list):
    earnings_date = earnings_date[0]  # Use earliest date (conservative)

# Case 3: Past earnings date (shouldn't happen, but handle)
if days_until < 0:
    return None  # Ignore past dates

# Case 4: Very far future (>90 days)
if days_until > 90:
    return None  # Too far to be relevant, treat as "no near-term earnings"
```

---

### Testing Plan

**Unit Tests**:
```python
# test_earnings_calendar.py

def test_get_earnings_calendar_basic():
    """Test fetching earnings for known upcoming earnings"""
    # Use a ticker with known upcoming earnings
    calendar = get_earnings_calendar(['MSFT'])
    
    assert 'MSFT' in calendar
    if calendar['MSFT'] is not None:
        assert 'date' in calendar['MSFT']
        assert 'days_until' in calendar['MSFT']
        assert isinstance(calendar['MSFT']['days_until'], int)

def test_get_earnings_calendar_multiple():
    """Test fetching for multiple tickers"""
    tickers = ['MSFT', 'NVDA', 'GOOGL']
    calendar = get_earnings_calendar(tickers)
    
    assert len(calendar) == 3
    for ticker in tickers:
        assert ticker in calendar
        # Value can be None or dict, both valid

def test_earnings_calendar_date_range():
    """Test handling of date ranges"""
    # Mock yfinance to return date range
    # Verify we take first date

def test_earnings_calendar_error_handling():
    """Test graceful handling of API errors"""
    calendar = get_earnings_calendar(['INVALID_TICKER'])
    assert calendar['INVALID_TICKER'] is None
```

**Integration Tests**:
```python
def test_full_data_fetch_includes_earnings():
    """Verify earnings calendar included in market data"""
    market_data = fetch_market_data(['MSFT', 'NVDA'])
    
    assert 'MSFT' in market_data
    assert 'earnings' in market_data['MSFT']
    # earnings can be None or dict

def test_prompt_includes_earnings_section():
    """Verify AI prompt contains earnings calendar"""
    market_data = fetch_market_data(['MSFT'])
    prompt = build_prompt(market_data, portfolio, config)
    
    assert "EARNINGS CALENDAR" in prompt
    # If MSFT has earnings, should show warning
```

**Manual Testing**:
1. Run program with current portfolio (MSFT with earnings in 2 days)
2. Verify output shows:
   ```
   ⚠️  IMMINENT EARNINGS (Action Restricted):
   MSFT:
     Earnings Date: 2026-01-28 (2 days away)
     ⛔ DO NOT SELL - Within 3-day blackout window
   ```
3. Verify AI recommendation respects this (doesn't recommend selling MSFT)
4. Test with ticker with no near-term earnings (should be in "safe" section)
5. Test with ticker having earnings in 15 days (should be in "upcoming" section)

---

## Acceptance Criteria

**Data Collection** - DONE when:
- [ ] `get_earnings_calendar()` function implemented
- [ ] Function fetches earnings dates from yfinance
- [ ] Returns structured dict with date, days_until, confirmed status
- [ ] Handles None/missing data gracefully (no crashes)
- [ ] Handles date ranges (takes first/earliest date)
- [ ] Integrated into `fetch_market_data()` pipeline
- [ ] Execution time < 5 seconds for 10 tickers

**AI Prompt** - DONE when:
- [ ] `format_earnings_calendar_for_prompt()` function implemented
- [ ] Earnings calendar section added to prompt
- [ ] Tickers grouped by proximity (imminent/upcoming/none)
- [ ] Imminent earnings (<7 days) show explicit restrictions
- [ ] Critical rules section added explaining why timing matters
- [ ] Prompt clearly instructs AI to respect earnings calendar

**Output Display** - DONE when:
- [ ] Earnings warnings shown in market snapshot
- [ ] Imminent earnings (< 7 days) highlighted with ⚠️  
- [ ] Earnings column added to rankings table
- [ ] Clear visual distinction between safe/restricted tickers

**AI Behavior** - DONE when:
- [ ] AI does NOT recommend selling within 3 days of earnings
- [ ] AI does NOT recommend buying within 7 days of earnings
- [ ] AI explicitly mentions earnings timing in reasoning
- [ ] AI provides post-earnings alternative plans when applicable
- [ ] Confidence level adjusted when near earnings (e.g., HIGH → MEDIUM)

**Testing** - DONE when:
- [ ] Unit tests pass (earnings calendar fetch)
- [ ] Integration tests pass (full data pipeline)
- [ ] Manual test with MSFT (earnings in 2 days) passes:
  - System shows earnings warning
  - AI does NOT recommend selling
  - AI reasoning mentions earnings timing
- [ ] Manual test with NVDA (earnings in 18 days) passes:
  - System shows "safe" status
  - AI can recommend normally
- [ ] No regressions (existing functionality unchanged)

---

## Impact Analysis

### Benefits

**Risk Reduction**:
- Prevents selling before earnings (avoids gap risk, runup miss)
- Prevents buying before earnings (avoids immediate volatility)
- Enforces user's own strategy rules programmatically
- Reduces chance of costly timing mistakes

**AI Quality**:
- AI has complete context to make timing-aware decisions
- Recommendations align with strategy principles
- More sophisticated reasoning (considers events, not just rankings)
- Confidence levels more accurate (adjusted for uncertainty)

**User Trust**:
- System respects stated rules (no violations)
- Recommendations feel more thoughtful (timing-aware)
- User doesn't need to manually check earnings calendar
- Builds confidence in delegating decisions to AI

### Risks

**Data Accuracy**:
- yfinance earnings dates occasionally wrong/missing
- **Mitigation**: Display "confirmed" status, user can verify manually

**API Reliability**:
- yfinance calendar API could fail
- **Mitigation**: Graceful None handling, continue with other data

**False Positives**:
- System might be too conservative (block valid actions)
- **Mitigation**: User can override, rules are guidelines not absolute

**Performance**:
- Additional API calls could slow execution
- **Mitigation**: Fetched in parallel with other data, minimal impact (<5 sec total)

### Cost

**API Costs**:
- yfinance is free, no additional cost
- Slightly longer Claude API prompts (+100 tokens)
- Impact: +$0.002 per run (negligible)

**Performance**:
- +2-5 seconds to fetch earnings for 10 tickers
- Total execution time: 35-65 seconds (was 30-60 seconds)
- Acceptable for monthly decision cadence

---

## Dependencies

**Python Libraries** (already installed):
- `yfinance` - Provides earnings calendar data
- `datetime` - Date calculations

**No new dependencies required**

---

## Rollback Plan

**If implementation causes issues**:

1. **Remove earnings calendar fetch**:
   ```python
   # Comment out in data_collector.py
   # earnings_calendar = get_earnings_calendar(tickers)
   ```

2. **Remove from prompt**:
   ```python
   # Comment out in ai_agent.py
   # {format_earnings_calendar_for_prompt(market_data)}
   ```

3. **Impact**: System returns to current behavior (no earnings awareness)

**No data loss risk**: All changes are additive, portfolio.json untouched

**Rollback time**: < 5 minutes (comment out 2-3 lines)

---

## Future Enhancements (Not in this CR)

- Add earnings time (before/after market) if available
- Add analyst earnings estimates (expected EPS)
- Add historical earnings beat/miss rate
- Add other event types (product launches, conference dates, FDA approvals)
- Add earnings season patterns (avoid concentrated earnings weeks)

---

## Documentation Updates

**README.md** - Add section:
```markdown
### Earnings Calendar

The system automatically fetches upcoming earnings dates for all stocks 
and enforces timing rules:
- No selling within 3 days of earnings (gap risk)
- No buying within 7 days of earnings (volatility risk)

Earnings dates are sourced from yfinance and displayed in:
- Market snapshot (earnings column)
- AI recommendations (imminent earnings warnings)
```

**strategy.txt** - Clarify:
```
EARNINGS PROXIMITY RULES (automatically enforced):
- DO NOT sell within 3 days before earnings
- DO NOT buy within 7 days before earnings
- These rules override other considerations (ranking, P&L targets)
- System will flag violations and suggest post-earnings alternatives
```

---

## Approval

- [x] Change documented
- [x] Solution reviewed and approved
- [x] Implementation complete
- [x] Testing complete
- [x] User acceptance testing complete
- [ ] Documentation updated

**Product Owner**: Tobes
**Reviewer**: Claude Code Assistant
**Implementation Target**: Week of Jan 27, 2026
**Implementation Completed**: January 27, 2026
**Priority**: URGENT (Critical Risk Management Bug)
**Actual Effort**: ~2 hours

---

**END OF CHANGE REQUEST**