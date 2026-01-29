# CR005 Implementation Plan - Position Event Monitor & Deep Analysis

**CR Reference**: [CR005 - Position Event Monitor & Deep Analysis](../3.%20ChangeLog/CR005%20-%20Position%20Event%20Monitor%20&%20Deep%20Analysis.md)
**Created**: January 29, 2026
**Status**: Ready for Implementation

---

## Requirements Validation

### Dependencies Check

| Dependency | Status | Location | Notes |
|------------|--------|----------|-------|
| CR002: News Themes | ✅ COMPLETE | `data_collector.py` lines 493-969 | Theme classification, frequency analysis, article counts |
| CR003: Earnings Calendar | ✅ COMPLETE | `data_collector.py` lines 254-304, `ai_agent.py` lines 449-524 | Earnings dates, days_until, trading restrictions |
| Narrative Storage | ✅ COMPLETE | `narrative_manager.py` | Thesis context for validation |

### Data Sources Validation

| Event Type | Detection Source | Available Data | Status |
|------------|-----------------|----------------|--------|
| Earnings Results | `calculate_earnings_proximity()` | `days_until`, `earnings_date` | ✅ Ready |
| Regulatory Actions | `THEME_KEYWORDS["regulatory"]` | Theme frequency (HIGH/MEDIUM/LOW), article count | ✅ Ready |
| Leadership Changes | `THEME_KEYWORDS["leadership"]` | Theme detection from news | ✅ Ready |
| M&A Activity | `THEME_KEYWORDS["acquisition"]` | Theme detection from news | ✅ Ready |
| Guidance Changes | `THEME_KEYWORDS["earnings"]` | Mid-quarter detection possible | ✅ Ready |

### Architecture Compatibility

| Component | Integration Point | Change Required |
|-----------|-------------------|-----------------|
| Data Layer | `fetch_all_market_data()` | None - data already collected |
| Context Generation | `generate_market_context()` | Add event detection logic |
| AI Prompt | `build_prompt()` | Add event analysis section |
| Display | `display.py` | Add `display_material_events()` |

**Validation Result**: ✅ All requirements are implementable with existing infrastructure

---

## Architecture Overview

### Data Flow

```
fetch_all_market_data()
       ↓ (existing)
generate_market_context()
       ↓ [NEW: detect_material_events()]
       ↓
build_prompt()
       ↓ [NEW: Add event analysis sections]
       ↓
get_recommendation()
       ↓
display_full_dashboard()
       ↓ [NEW: display_material_events() FIRST]
```

### New Module: `event_detector.py`

Centralized event detection and analysis logic:

```
event_detector.py
├── MATERIAL_EVENT_TYPES (constants)
├── detect_material_events(market_data, portfolio) → List[MaterialEvent]
├── analyze_earnings_event(event, position, narratives) → EarningsAnalysis
├── analyze_regulatory_event(event, position, narratives) → RegulatoryAnalysis
├── analyze_leadership_event(event, position, narratives) → LeadershipAnalysis
├── analyze_ma_event(event, position, narratives) → MAAnalysis
└── format_event_for_prompt(analysis) → str
```

---

## Phase 1: Event Detection Engine

**Goal**: Detect Tier 1 material events affecting holdings only

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `App/src/event_detector.py` | CREATE | New module for event detection |
| `App/src/analyzer.py` | MODIFY | Integrate event detection into context |

### Task 1.1: Create Event Detection Module

**File**: `App/src/event_detector.py`

```python
"""
Material Event Detection for Portfolio Holdings

Detects Tier 1 events that require deep analysis:
- Earnings Results (within 2 days of report)
- Regulatory Actions (HIGH frequency or major announcement)
- Leadership Changes (CEO/CFO/founder departures)
- M&A Activity (acquisition announcements)
- Guidance Changes (mid-quarter warnings)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta

@dataclass
class MaterialEvent:
    ticker: str
    event_type: str  # earnings, regulatory, leadership, ma, guidance
    priority: str    # HIGH, MEDIUM
    detected_date: str
    headline: str
    source: str
    article_count: int
    frequency: str
    details: Dict

# Event detection thresholds
EARNINGS_WINDOW_DAYS = 2  # Days after earnings to trigger analysis
REGULATORY_HIGH_THRESHOLD = 4  # Articles in 14 days = HIGH frequency
LEADERSHIP_KEYWORDS = ['ceo', 'cfo', 'founder', 'chief executive', 'chief financial',
                       'resign', 'depart', 'step down', 'retire', 'terminate', 'fired']
MA_KEYWORDS = ['acquire', 'acquisition', 'merger', 'buyout', 'takeover', 'bid']


def detect_material_events(market_data: Dict, portfolio: Dict) -> List[MaterialEvent]:
    """
    Scan holdings for material events.

    Args:
        market_data: Full market data from fetch_all_market_data()
        portfolio: Portfolio with positions

    Returns:
        List of MaterialEvent objects for holdings with detected events
    """
    events = []
    holdings = {p['ticker'] for p in portfolio.get('positions', [])}

    for ticker in holdings:
        ticker_data = market_data.get('tickers', {}).get(ticker, {})

        # Check each event type
        earnings_event = _detect_earnings_event(ticker, ticker_data)
        if earnings_event:
            events.append(earnings_event)

        regulatory_event = _detect_regulatory_event(ticker, ticker_data)
        if regulatory_event:
            events.append(regulatory_event)

        leadership_event = _detect_leadership_event(ticker, ticker_data)
        if leadership_event:
            events.append(leadership_event)

        ma_event = _detect_ma_event(ticker, ticker_data)
        if ma_event:
            events.append(ma_event)

    # Sort by priority (HIGH first), then by event type (earnings first)
    priority_order = {'HIGH': 0, 'MEDIUM': 1}
    type_order = {'earnings': 0, 'regulatory': 1, 'leadership': 2, 'ma': 3}
    events.sort(key=lambda e: (priority_order.get(e.priority, 2), type_order.get(e.event_type, 4)))

    return events


def _detect_earnings_event(ticker: str, ticker_data: Dict) -> Optional[MaterialEvent]:
    """Detect if earnings were recently reported."""
    earnings = ticker_data.get('earnings', {})
    days_until = earnings.get('days_until')

    # Negative days_until means earnings already happened
    if days_until is not None and -EARNINGS_WINDOW_DAYS <= days_until <= 0:
        return MaterialEvent(
            ticker=ticker,
            event_type='earnings',
            priority='HIGH',
            detected_date=datetime.now().strftime('%Y-%m-%d'),
            headline=f'Q4 earnings reported {abs(days_until)} day(s) ago',
            source='Earnings Calendar',
            article_count=1,
            frequency='N/A',
            details={
                'days_since_earnings': abs(days_until),
                'earnings_date': earnings.get('earnings_date')
            }
        )
    return None


def _detect_regulatory_event(ticker: str, ticker_data: Dict) -> Optional[MaterialEvent]:
    """Detect escalating regulatory/legal themes."""
    news = ticker_data.get('news', {})
    themes = news.get('themes', [])

    for theme in themes:
        if theme.get('name') in ['regulatory', 'legal']:
            frequency = theme.get('frequency', 'LOW')
            article_count = theme.get('article_count', 0)

            # HIGH frequency OR 4+ articles triggers event
            if frequency == 'HIGH' or article_count >= REGULATORY_HIGH_THRESHOLD:
                return MaterialEvent(
                    ticker=ticker,
                    event_type='regulatory',
                    priority='HIGH' if frequency == 'HIGH' else 'MEDIUM',
                    detected_date=datetime.now().strftime('%Y-%m-%d'),
                    headline=theme.get('headline', 'Regulatory action detected'),
                    source=theme.get('source', 'News'),
                    article_count=article_count,
                    frequency=frequency,
                    details={
                        'theme_name': theme.get('name'),
                        'urls': theme.get('urls', [])
                    }
                )
    return None


def _detect_leadership_event(ticker: str, ticker_data: Dict) -> Optional[MaterialEvent]:
    """Detect CEO/CFO/founder departures."""
    news = ticker_data.get('news', {})
    themes = news.get('themes', [])

    for theme in themes:
        if theme.get('name') == 'leadership':
            headline = theme.get('headline', '').lower()

            # Check if headline indicates departure (not just appointment)
            if any(kw in headline for kw in ['resign', 'depart', 'step down', 'retire', 'leave', 'exit']):
                return MaterialEvent(
                    ticker=ticker,
                    event_type='leadership',
                    priority='HIGH',
                    detected_date=datetime.now().strftime('%Y-%m-%d'),
                    headline=theme.get('headline', 'Leadership change detected'),
                    source=theme.get('source', 'News'),
                    article_count=theme.get('article_count', 1),
                    frequency=theme.get('frequency', 'MEDIUM'),
                    details={
                        'urls': theme.get('urls', [])
                    }
                )
    return None


def _detect_ma_event(ticker: str, ticker_data: Dict) -> Optional[MaterialEvent]:
    """Detect major M&A activity."""
    news = ticker_data.get('news', {})
    themes = news.get('themes', [])

    for theme in themes:
        if theme.get('name') == 'acquisition':
            return MaterialEvent(
                ticker=ticker,
                event_type='ma',
                priority='HIGH',
                detected_date=datetime.now().strftime('%Y-%m-%d'),
                headline=theme.get('headline', 'M&A activity detected'),
                source=theme.get('source', 'News'),
                article_count=theme.get('article_count', 1),
                frequency=theme.get('frequency', 'MEDIUM'),
                details={
                    'urls': theme.get('urls', [])
                }
            )
    return None
```

### Task 1.2: Integrate Detection into Context Generation

**File**: `App/src/analyzer.py`

Add at end of `generate_market_context()`:

```python
from src.event_detector import detect_material_events

# In generate_market_context(), after existing analysis:
material_events = detect_material_events(market_data, portfolio)
context['material_events'] = [
    {
        'ticker': e.ticker,
        'event_type': e.event_type,
        'priority': e.priority,
        'headline': e.headline,
        'article_count': e.article_count,
        'frequency': e.frequency,
        'details': e.details
    }
    for e in material_events
]
```

### Acceptance Criteria - Phase 1

- [ ] `event_detector.py` created with detection functions
- [ ] Earnings events detected within 2-day window
- [ ] Regulatory events detected with HIGH frequency or 4+ articles
- [ ] Leadership departures detected (not appointments)
- [ ] M&A events detected from acquisition theme
- [ ] Events only detected for holdings (not watchlist)
- [ ] Events sorted by priority

---

## Phase 2: Deep Analysis Templates

**Goal**: Generate detailed analysis for each event type

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `App/src/event_detector.py` | MODIFY | Add analysis functions |
| `App/src/ai_agent.py` | MODIFY | Add event sections to prompt |

### Task 2.1: Add Analysis Functions

**File**: `App/src/event_detector.py` (append)

```python
def analyze_event(event: MaterialEvent, position: Dict, narratives: Dict,
                  market_data: Dict) -> Dict:
    """
    Generate deep analysis for a material event.

    Returns structured analysis with:
    - Event context
    - Position context
    - Thesis validation
    - Decision framework
    """
    ticker = event.ticker
    ticker_data = market_data.get('tickers', {}).get(ticker, {})

    # Position context
    position_context = _build_position_context(position, ticker_data)

    # Thesis from narratives
    thesis_context = _build_thesis_context(ticker, narratives)

    # Event-specific analysis
    if event.event_type == 'earnings':
        return _analyze_earnings(event, position_context, thesis_context, ticker_data)
    elif event.event_type == 'regulatory':
        return _analyze_regulatory(event, position_context, thesis_context, ticker_data)
    elif event.event_type == 'leadership':
        return _analyze_leadership(event, position_context, thesis_context, ticker_data)
    elif event.event_type == 'ma':
        return _analyze_ma(event, position_context, thesis_context, ticker_data)

    return {}


def _build_position_context(position: Dict, ticker_data: Dict) -> Dict:
    """Build position-specific context."""
    current_price = ticker_data.get('price', {}).get('current', 0)
    entry_price = position.get('purchase_price', 0)
    quantity = position.get('quantity', 0)

    # Calculate P&L
    if entry_price > 0:
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
    else:
        pnl_pct = 0

    # Calculate days held
    purchase_date = position.get('purchase_date', '')
    if purchase_date:
        try:
            days_held = (datetime.now() - datetime.strptime(purchase_date, '%Y-%m-%d')).days
        except:
            days_held = 0
    else:
        days_held = 0

    return {
        'quantity': quantity,
        'entry_price': entry_price,
        'current_price': current_price,
        'pnl_pct': round(pnl_pct, 2),
        'pnl_dollars': round((current_price - entry_price) * quantity, 2),
        'days_held': days_held,
        'is_sellable': days_held >= 30,
        'position_value': round(current_price * quantity, 2)
    }


def _build_thesis_context(ticker: str, narratives: Dict) -> Dict:
    """Extract thesis from narratives."""
    stock_narratives = narratives.get('stocks', {}).get(ticker, {})
    active = stock_narratives.get('active_narratives', [])
    resolved = stock_narratives.get('resolved_narratives', [])

    return {
        'active_themes': [n.get('theme') for n in active],
        'active_summaries': [n.get('summary') for n in active],
        'resolved_themes': [n.get('theme') for n in resolved],
        'has_thesis': len(active) > 0 or len(resolved) > 0
    }


def _analyze_earnings(event: MaterialEvent, position: Dict, thesis: Dict,
                      ticker_data: Dict) -> Dict:
    """Generate earnings event analysis."""
    fundamentals = ticker_data.get('fundamentals', {})
    technicals = ticker_data.get('technicals', {})
    price_context = ticker_data.get('price_context', {})

    return {
        'event_type': 'earnings',
        'priority': event.priority,
        'sections': {
            'event_context': {
                'what_happened': event.headline,
                'when': f"{event.details.get('days_since_earnings', 0)} day(s) ago",
                'earnings_date': event.details.get('earnings_date', 'Unknown')
            },
            'position_context': position,
            'market_reaction': {
                'price_change_30d': price_context.get('return_30d', 0),
                'vs_spy': price_context.get('vs_spy', 0),
                'rsi': technicals.get('rsi', 50),
                'current_rank': ticker_data.get('rank', 'N/A')
            },
            'thesis_validation': {
                'active_themes': thesis.get('active_themes', []),
                'has_prior_context': thesis.get('has_thesis', False),
                'check_required': [
                    'Did earnings validate growth thesis?',
                    'Is guidance positive or negative?',
                    'How does this compare to peers?'
                ]
            },
            'decision_framework': {
                'option_a': {
                    'action': 'EXIT',
                    'conditions': [
                        'Rank dropped below threshold',
                        'Earnings missed or guidance cut',
                        'Better alternatives available'
                    ]
                },
                'option_b': {
                    'action': 'HOLD',
                    'conditions': [
                        'Earnings beat expectations',
                        'Thesis validated by results',
                        'Rank stable or improving'
                    ]
                }
            }
        }
    }


def _analyze_regulatory(event: MaterialEvent, position: Dict, thesis: Dict,
                        ticker_data: Dict) -> Dict:
    """Generate regulatory event analysis."""
    return {
        'event_type': 'regulatory',
        'priority': event.priority,
        'sections': {
            'event_context': {
                'what_happened': event.headline,
                'frequency': event.frequency,
                'article_count': event.article_count,
                'source': event.source
            },
            'position_context': position,
            'severity_assessment': {
                'frequency_level': event.frequency,
                'escalating': event.article_count >= 4,
                'check_required': [
                    'Who is the regulator (DOJ, FTC, EU, SEC)?',
                    'What are the allegations?',
                    'What is the potential financial impact?'
                ]
            },
            'thesis_validation': {
                'active_themes': thesis.get('active_themes', []),
                'impact_question': 'Does this change the investment case?'
            },
            'decision_framework': {
                'option_a': {
                    'action': 'EXIT',
                    'conditions': [
                        'Business model at risk',
                        'High financial exposure',
                        'Long timeline to resolution'
                    ]
                },
                'option_b': {
                    'action': 'HOLD',
                    'conditions': [
                        'Risk already priced in',
                        'Similar past cases resolved favorably',
                        'Core business unaffected'
                    ]
                }
            }
        }
    }


def _analyze_leadership(event: MaterialEvent, position: Dict, thesis: Dict,
                        ticker_data: Dict) -> Dict:
    """Generate leadership change analysis."""
    return {
        'event_type': 'leadership',
        'priority': event.priority,
        'sections': {
            'event_context': {
                'what_happened': event.headline,
                'source': event.source
            },
            'position_context': position,
            'change_assessment': {
                'check_required': [
                    'Was this planned or unexpected?',
                    'Is successor named?',
                    'What is the transition timeline?'
                ]
            },
            'thesis_validation': {
                'active_themes': thesis.get('active_themes', []),
                'impact_question': 'Does strategy continuity remain?'
            },
            'decision_framework': {
                'option_a': {
                    'action': 'EXIT',
                    'conditions': [
                        'Unexpected departure (fired/sudden)',
                        'No clear successor',
                        'Strategy uncertainty high'
                    ]
                },
                'option_b': {
                    'action': 'HOLD',
                    'conditions': [
                        'Planned retirement with transition',
                        'Strong internal successor',
                        'Strategy expected to continue'
                    ]
                }
            }
        }
    }


def _analyze_ma(event: MaterialEvent, position: Dict, thesis: Dict,
                ticker_data: Dict) -> Dict:
    """Generate M&A event analysis."""
    return {
        'event_type': 'ma',
        'priority': event.priority,
        'sections': {
            'event_context': {
                'what_happened': event.headline,
                'source': event.source
            },
            'position_context': position,
            'deal_assessment': {
                'check_required': [
                    'Is holding the target or acquirer?',
                    'What are deal terms?',
                    'What is regulatory approval risk?'
                ]
            },
            'thesis_validation': {
                'active_themes': thesis.get('active_themes', []),
                'impact_question': 'Does this strengthen or weaken the company?'
            },
            'decision_framework': {
                'option_a_target': {
                    'action': 'HOLD until close (if target)',
                    'conditions': [
                        'Premium to current price',
                        'High deal certainty',
                        'Regulatory approval likely'
                    ]
                },
                'option_b_acquirer': {
                    'action': 'EVALUATE (if acquirer)',
                    'conditions': [
                        'Strategic fit assessment',
                        'Integration risk evaluation',
                        'Valuation impact analysis'
                    ]
                }
            }
        }
    }
```

### Task 2.2: Add Event Sections to AI Prompt

**File**: `App/src/ai_agent.py`

Add new function and integrate into `build_prompt()`:

```python
def _format_material_events(context: Dict, narratives: Dict, market_data: Dict) -> str:
    """Format material events section for AI prompt."""
    events = context.get('material_events', [])
    if not events:
        return ""

    from src.event_detector import analyze_event, MaterialEvent

    lines = [
        "=" * 60,
        "MATERIAL EVENTS DETECTED - ANALYSIS REQUIRED",
        "=" * 60,
        "",
        f"The following material events affect your current holdings.",
        f"Each requires a hold/exit decision analysis.",
        ""
    ]

    for event_data in events:
        # Find position for this ticker
        position = None
        for p in context.get('positions', []):
            if p.get('ticker') == event_data['ticker']:
                position = p
                break

        if not position:
            continue

        # Create MaterialEvent object
        event = MaterialEvent(
            ticker=event_data['ticker'],
            event_type=event_data['event_type'],
            priority=event_data['priority'],
            detected_date='',
            headline=event_data['headline'],
            source='',
            article_count=event_data.get('article_count', 0),
            frequency=event_data.get('frequency', ''),
            details=event_data.get('details', {})
        )

        # Get analysis
        analysis = analyze_event(event, position, narratives, market_data)

        lines.append("-" * 60)
        lines.append(f"EVENT: {event.ticker} - {event.event_type.upper()}")
        lines.append(f"Priority: {event.priority}")
        lines.append("-" * 60)

        sections = analysis.get('sections', {})

        # Event context
        ec = sections.get('event_context', {})
        lines.append("\nWHAT HAPPENED:")
        lines.append(f"  {ec.get('what_happened', 'Unknown')}")
        if 'when' in ec:
            lines.append(f"  When: {ec['when']}")

        # Position context
        pc = sections.get('position_context', {})
        lines.append("\nYOUR POSITION:")
        lines.append(f"  Quantity: {pc.get('quantity', 0)} shares @ ${pc.get('entry_price', 0):.2f}")
        lines.append(f"  Current: ${pc.get('current_price', 0):.2f} ({pc.get('pnl_pct', 0):+.1f}%)")
        lines.append(f"  Days held: {pc.get('days_held', 0)} ({'SELLABLE' if pc.get('is_sellable') else 'LOCKED'})")

        # Decision framework
        df = sections.get('decision_framework', {})
        lines.append("\nDECISION FRAMEWORK:")

        for option_key, option in df.items():
            action = option.get('action', 'Unknown')
            conditions = option.get('conditions', [])
            lines.append(f"\n  {action}:")
            for cond in conditions:
                lines.append(f"    - {cond}")

        lines.append("")

    lines.append("=" * 60)
    lines.append("IMPORTANT: For each material event above, your recommendation")
    lines.append("MUST include specific analysis of whether to HOLD or EXIT,")
    lines.append("with clear reasoning based on the event details and position context.")
    lines.append("=" * 60)
    lines.append("")

    return "\n".join(lines)


# In build_prompt(), add BEFORE standard recommendations:
# material_events_section = _format_material_events(context, narratives, market_data)
# prompt_parts.insert(position_after_strategy, material_events_section)
```

### Acceptance Criteria - Phase 2

- [ ] Analysis functions return structured data for all event types
- [ ] Position context includes P&L, days held, sellability
- [ ] Thesis context pulled from narratives
- [ ] Decision framework included for each event type
- [ ] AI prompt includes material events section
- [ ] Event analysis appears BEFORE standard recommendations in prompt

---

## Phase 3: Display Integration

**Goal**: Show material events prominently in output

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `App/src/display.py` | MODIFY | Add material events display |
| `App/src/advisor.py` | MODIFY | Call display before standard output |

### Task 3.1: Add Material Events Display

**File**: `App/src/display.py`

```python
def display_material_events(context: Dict, recommendation: Dict) -> None:
    """Display material events section at top of output."""
    events = context.get('material_events', [])
    if not events:
        return

    console = Console()

    # Alert header
    console.print()
    console.print("=" * 60, style="bold red")
    console.print(f"  MATERIAL EVENT{'S' if len(events) > 1 else ''} DETECTED", style="bold red")
    console.print("=" * 60, style="bold red")
    console.print()

    for event in events:
        ticker = event['ticker']
        event_type = event['event_type'].upper()
        priority = event['priority']
        headline = event['headline']

        # Event header
        priority_style = "bold red" if priority == "HIGH" else "bold yellow"
        console.print(f"[{priority_style}]{ticker}: {event_type}[/{priority_style}]")
        console.print(f"  {headline}")

        # Find position
        position = None
        for p in context.get('positions', []):
            if p.get('ticker') == ticker:
                position = p
                break

        if position:
            pnl = position.get('current_pnl_pct', 0)
            days = position.get('days_held', 0)
            pnl_style = "green" if pnl >= 0 else "red"
            console.print(f"  Position: [{pnl_style}]{pnl:+.1f}%[/{pnl_style}], {days} days held")

        # Show AI recommendation for this event
        actions = recommendation.get('actions', [])
        for action in actions:
            if action.get('ticker') == ticker:
                action_type = action.get('type', 'HOLD')
                reasoning = action.get('reasoning', '')

                action_style = "green" if action_type == "HOLD" else "red" if action_type == "SELL" else "yellow"
                console.print(f"\n  [bold]RECOMMENDATION: [{action_style}]{action_type}[/{action_style}][/bold]")
                console.print(f"  {reasoning[:200]}..." if len(reasoning) > 200 else f"  {reasoning}")

        console.print()

    console.print("=" * 60, style="bold red")
    console.print()
```

### Task 3.2: Integrate into Advisor Flow

**File**: `App/src/advisor.py`

In `cmd_run()`, after getting recommendation:

```python
# Display material events FIRST (before standard dashboard)
if context.get('material_events'):
    display_material_events(context, recommendation)

# Then display standard dashboard
display_full_dashboard(...)
```

### Acceptance Criteria - Phase 3

- [ ] Material events displayed FIRST in output
- [ ] Alert formatting with visual priority (colors, borders)
- [ ] Position context shown (P&L, days held)
- [ ] AI recommendation shown for each event
- [ ] Clean output when no events detected
- [ ] Multiple events handled gracefully

---

## Phase 4: Testing & Validation

**Goal**: Verify feature works correctly

### Test Cases

| ID | Scenario | Expected Result |
|----|----------|-----------------|
| T1 | Holding reports earnings 1 day ago | Earnings event detected, analysis shown |
| T2 | Holding has 5 regulatory articles | Regulatory event detected, HIGH priority |
| T3 | Holding has CEO departure news | Leadership event detected |
| T4 | Holding has acquisition announcement | M&A event detected |
| T5 | No material events for holdings | No events section shown, normal output |
| T6 | Event for watchlist stock (not held) | Event NOT detected (only holdings) |
| T7 | Multiple events across holdings | All events shown, sorted by priority |

### Test Commands

```bash
# Test event detection
cd App && python -c "
from src.event_detector import detect_material_events
# Mock test data
market_data = {'tickers': {'MSFT': {'earnings': {'days_until': -1}}}}
portfolio = {'positions': [{'ticker': 'MSFT', 'purchase_price': 400}]}
events = detect_material_events(market_data, portfolio)
print(f'Events detected: {len(events)}')
for e in events:
    print(f'  {e.ticker}: {e.event_type} ({e.priority})')
"

# Full integration test
cd App && python -m src.advisor
```

### Acceptance Criteria - Phase 4

- [ ] All test cases pass
- [ ] Event detection accuracy >90%
- [ ] False positive rate <20%
- [ ] No regressions in existing functionality
- [ ] Execution time <90 seconds with events

---

## Phase 5: Polish & Documentation

**Goal**: Refine UX and document feature

### Tasks

| ID | Task | Description |
|----|------|-------------|
| 5.1 | Visual refinements | Improve formatting, spacing, colors |
| 5.2 | Edge case handling | Multiple simultaneous events, locked positions |
| 5.3 | Error handling | Graceful degradation if analysis fails |
| 5.4 | User guide update | Document feature in README |

### Acceptance Criteria - Phase 5

- [ ] Output visually polished
- [ ] Edge cases handled gracefully
- [ ] Error handling prevents crashes
- [ ] README updated with Material Events section

---

## Implementation Summary

### Files to Create

| File | Purpose |
|------|---------|
| `App/src/event_detector.py` | Event detection and analysis logic |

### Files to Modify

| File | Changes |
|------|---------|
| `App/src/analyzer.py` | Integrate event detection into context |
| `App/src/ai_agent.py` | Add event sections to prompt |
| `App/src/display.py` | Add material events display |
| `App/src/advisor.py` | Orchestrate event display flow |
| `README.md` | Document new feature |

### Estimated Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Event Detection | 2-3 hours | Critical |
| Phase 2: Analysis Templates | 2-3 hours | Critical |
| Phase 3: Display Integration | 1-2 hours | Critical |
| Phase 4: Testing | 1-2 hours | Required |
| Phase 5: Polish | 1 hour | Optional |

**Total**: 7-11 hours

---

## Rollback Plan

If issues arise:

1. **Detection false positives**: Tighten thresholds (increase `REGULATORY_HIGH_THRESHOLD`)
2. **Performance issues**: Make event detection optional via config flag
3. **Display problems**: Disable `display_material_events()` call, revert to standard output
4. **AI prompt issues**: Remove event sections from prompt, revert to standard recommendations

---

## Progress Tracking

| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| 1 | Pending | 0/2 | |
| 2 | Pending | 0/2 | |
| 3 | Pending | 0/2 | |
| 4 | Pending | 0/7 | |
| 5 | Pending | 0/4 | |

---

**Ready for Implementation**: January 29, 2026
