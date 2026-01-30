"""
event_detector.py - Material Event Detection for Portfolio Holdings

Responsibilities:
- Detect Tier 1 material events affecting held positions
- Provide structured event data for deep analysis
- Only scan holdings (not entire watchlist)

Material Events (Tier 1):
- Earnings Results (reported within last 2 days)
- Regulatory Actions (HIGH frequency or 4+ articles)
- Leadership Changes (CEO/CFO/founder departures)
- Major M&A Activity (acquisition announcements)
- Guidance Changes (mid-quarter warnings)

Key Functions:
- detect_material_events(market_data, portfolio) -> list
- build_event_analysis(events, portfolio, market_data, narratives) -> list
"""

from datetime import datetime, date
from typing import List, Dict, Optional


# =============================================================================
# Event Detection Thresholds
# =============================================================================

EARNINGS_WINDOW_DAYS = 2          # Days after earnings to trigger analysis
REGULATORY_HIGH_THRESHOLD = 4     # Articles in scan period = HIGH
LEADERSHIP_DEPARTURE_KEYWORDS = [
    'resign', 'depart', 'step down', 'steps down', 'retire',
    'leaves', 'leaving', 'exit', 'fired', 'ousted', 'replaced'
]


# =============================================================================
# Event Detection
# =============================================================================

def detect_material_events(market_data: dict, portfolio: dict) -> list:
    """
    Scan holdings for material events requiring deep analysis.

    Only checks stocks currently held in the portfolio (not watchlist).

    Args:
        market_data: Full market data from fetch_all_market_data()
        portfolio: Portfolio dictionary with positions

    Returns:
        List of event dicts, sorted by priority
    """
    events = []
    # Lot-based format: each position has a 'ticker' key (one per stock)
    holdings = {p.get('ticker', '') for p in portfolio.get('positions', [])}

    for ticker in holdings:
        ticker_data = market_data.get('tickers', {}).get(ticker, {})
        if not ticker_data:
            continue

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

    # Sort by priority (HIGH first), then by event type importance
    priority_order = {'HIGH': 0, 'MEDIUM': 1}
    type_order = {'earnings': 0, 'regulatory': 1, 'leadership': 2, 'ma': 3}
    events.sort(key=lambda e: (
        priority_order.get(e['priority'], 2),
        type_order.get(e['event_type'], 4)
    ))

    return events


def _detect_earnings_event(ticker: str, ticker_data: dict) -> Optional[dict]:
    """
    Detect if earnings were recently reported.

    Uses the earnings_proximity data. If days_until is negative and within
    the detection window, the stock recently reported earnings.
    Also checks news themes for earnings-related headlines as a fallback.
    """
    # Primary: Check earnings proximity data for recently reported
    earnings = ticker_data.get('earnings')
    if earnings:
        days_until = earnings.get('days_until')
        if days_until is not None and -EARNINGS_WINDOW_DAYS <= days_until <= 0:
            return {
                'ticker': ticker,
                'event_type': 'earnings',
                'priority': 'HIGH',
                'headline': f'Earnings reported {abs(days_until)} day(s) ago',
                'source': 'Earnings Calendar',
                'article_count': 1,
                'frequency': 'N/A',
                'details': {
                    'days_since_earnings': abs(days_until),
                    'earnings_date': earnings.get('date', 'Unknown'),
                }
            }

    # Fallback: Check news themes for recent earnings headlines
    news = ticker_data.get('news', {})
    themes = news.get('themes', [])
    for theme in themes:
        if theme.get('name') == 'earnings':
            headline = (theme.get('headline', '') or '').lower()
            # Look for keywords indicating results (not upcoming)
            results_keywords = ['beat', 'miss', 'results', 'reported', 'quarterly',
                                'surpass', 'exceeded', 'fell short', 'topped']
            if any(kw in headline for kw in results_keywords):
                return {
                    'ticker': ticker,
                    'event_type': 'earnings',
                    'priority': 'HIGH',
                    'headline': theme.get('headline', 'Earnings results detected'),
                    'source': theme.get('source', 'News'),
                    'article_count': theme.get('article_count', 1),
                    'frequency': theme.get('frequency', 'MEDIUM'),
                    'details': {
                        'detected_from': 'news_theme',
                    }
                }

    return None


def _detect_regulatory_event(ticker: str, ticker_data: dict) -> Optional[dict]:
    """
    Detect escalating regulatory/legal themes.

    Triggers on HIGH frequency or 4+ articles for regulatory/legal themes.
    """
    news = ticker_data.get('news', {})
    themes = news.get('themes', [])

    for theme in themes:
        theme_name = theme.get('name', '')
        if theme_name in ('regulatory', 'legal'):
            frequency = theme.get('frequency', 'LOW')
            article_count = theme.get('article_count', 0)

            if frequency == 'HIGH' or article_count >= REGULATORY_HIGH_THRESHOLD:
                return {
                    'ticker': ticker,
                    'event_type': 'regulatory',
                    'priority': 'HIGH' if frequency == 'HIGH' else 'MEDIUM',
                    'headline': theme.get('headline', 'Regulatory action detected'),
                    'source': theme.get('source', 'News'),
                    'article_count': article_count,
                    'frequency': frequency,
                    'details': {
                        'theme_name': theme_name,
                        'urls': theme.get('urls', []),
                    }
                }

    return None


def _detect_leadership_event(ticker: str, ticker_data: dict) -> Optional[dict]:
    """
    Detect CEO/CFO/founder departures.

    Only triggers on departures (not appointments), since departures create
    uncertainty requiring analysis.
    """
    news = ticker_data.get('news', {})
    themes = news.get('themes', [])

    for theme in themes:
        if theme.get('name') == 'leadership':
            headline = (theme.get('headline', '') or '').lower()

            if any(kw in headline for kw in LEADERSHIP_DEPARTURE_KEYWORDS):
                return {
                    'ticker': ticker,
                    'event_type': 'leadership',
                    'priority': 'HIGH',
                    'headline': theme.get('headline', 'Leadership change detected'),
                    'source': theme.get('source', 'News'),
                    'article_count': theme.get('article_count', 1),
                    'frequency': theme.get('frequency', 'MEDIUM'),
                    'details': {
                        'urls': theme.get('urls', []),
                    }
                }

    return None


def _detect_ma_event(ticker: str, ticker_data: dict) -> Optional[dict]:
    """
    Detect major M&A activity.

    Triggers on acquisition theme detection.
    """
    news = ticker_data.get('news', {})
    themes = news.get('themes', [])

    for theme in themes:
        if theme.get('name') == 'acquisition':
            return {
                'ticker': ticker,
                'event_type': 'ma',
                'priority': 'HIGH',
                'headline': theme.get('headline', 'M&A activity detected'),
                'source': theme.get('source', 'News'),
                'article_count': theme.get('article_count', 1),
                'frequency': theme.get('frequency', 'MEDIUM'),
                'details': {
                    'urls': theme.get('urls', []),
                }
            }

    return None


# =============================================================================
# Event Analysis
# =============================================================================

def build_event_analysis(events: list, portfolio: dict, market_data: dict,
                         narratives: dict = None) -> list:
    """
    Build deep analysis for each detected event.

    Enriches events with position context, thesis validation, and
    decision framework data.

    Args:
        events: List of detected event dicts from detect_material_events()
        portfolio: Portfolio dictionary
        market_data: Full market data
        narratives: Optional narratives for thesis context

    Returns:
        List of enriched event analysis dicts
    """
    if not events:
        return []

    narratives = narratives or {}
    analyses = []

    # Build position lookup (lot-based: one entry per ticker)
    position_lookup = {
        p.get('ticker', ''): p for p in portfolio.get('positions', [])
    }

    for event in events:
        ticker = event['ticker']
        position = position_lookup.get(ticker, {})
        ticker_data = market_data.get('tickers', {}).get(ticker, {})

        # Build position context
        position_context = _build_position_context(position, ticker_data)

        # Build thesis context from narratives
        thesis_context = _build_thesis_context(ticker, narratives)

        # Build event-specific analysis
        event_analysis = {
            'event': event,
            'position_context': position_context,
            'thesis_context': thesis_context,
            'market_reaction': _build_market_reaction(ticker_data),
        }

        # Add event-type-specific sections
        if event['event_type'] == 'earnings':
            event_analysis['decision_framework'] = _earnings_decision_framework()
        elif event['event_type'] == 'regulatory':
            event_analysis['decision_framework'] = _regulatory_decision_framework()
        elif event['event_type'] == 'leadership':
            event_analysis['decision_framework'] = _leadership_decision_framework()
        elif event['event_type'] == 'ma':
            event_analysis['decision_framework'] = _ma_decision_framework()

        analyses.append(event_analysis)

    return analyses


def _build_position_context(position: dict, ticker_data: dict) -> dict:
    """Build position-specific context for analysis (lot-based)."""
    current_price = ticker_data.get('price', {}).get('current_price', 0)

    # Lot-based: compute aggregates from lots
    lots = position.get('lots', [])
    total_quantity = 0
    total_cost = 0
    sellable_quantity = 0
    oldest_days_held = 0

    for lot in lots:
        qty = lot.get('quantity', 0)
        price = lot.get('purchase_price', 0)
        total_quantity += qty
        total_cost += qty * price

        pdate = lot.get('purchase_date', '')
        lot_days = 0
        if pdate:
            try:
                lot_days = (date.today() - datetime.strptime(pdate, '%Y-%m-%d').date()).days
            except (ValueError, TypeError):
                pass

        if lot_days > oldest_days_held:
            oldest_days_held = lot_days
        if lot_days >= 30:
            sellable_quantity += qty

    average_cost = total_cost / total_quantity if total_quantity > 0 else 0
    pnl_pct = 0
    if average_cost > 0:
        pnl_pct = ((current_price - average_cost) / average_cost) * 100

    return {
        'quantity': total_quantity,
        'entry_price': round(average_cost, 2),
        'current_price': current_price,
        'pnl_pct': round(pnl_pct, 2),
        'pnl_dollars': round((current_price - average_cost) * total_quantity, 2),
        'days_held': oldest_days_held,
        'is_sellable': sellable_quantity > 0,
        'sellable_quantity': sellable_quantity,
        'position_value': round(current_price * total_quantity, 2),
    }


def _build_thesis_context(ticker: str, narratives: dict) -> dict:
    """Extract thesis context from narratives."""
    stock_narratives = narratives.get('stocks', {}).get(ticker, {})
    active = stock_narratives.get('active_narratives', [])
    resolved = stock_narratives.get('resolved_narratives', [])

    return {
        'active_themes': [n.get('theme', '') for n in active],
        'active_summaries': [n.get('summary', '') for n in active],
        'resolved_themes': [n.get('theme', '') for n in resolved],
        'has_thesis': len(active) > 0 or len(resolved) > 0,
    }


def _build_market_reaction(ticker_data: dict) -> dict:
    """Build market reaction context."""
    technicals = ticker_data.get('technicals', {})
    price_context = ticker_data.get('price_context', {})

    return {
        'return_30d': price_context.get('return_30d', 0),
        'vs_spy': price_context.get('relative_performance', 0),
        'rsi': technicals.get('rsi_14', 50),
        'trend': price_context.get('trend', 'UNKNOWN'),
    }


def _earnings_decision_framework() -> dict:
    """Decision framework for earnings events."""
    return {
        'option_exit': {
            'action': 'EXIT',
            'label': 'Exit Position',
            'conditions': [
                'Rank dropped below top-3 threshold',
                'Earnings missed or guidance cut',
                'Better alternatives available (higher ranked stocks)',
                'Thesis invalidated by results',
            ]
        },
        'option_hold': {
            'action': 'HOLD',
            'label': 'Hold Position',
            'conditions': [
                'Earnings beat expectations',
                'Thesis validated by results (growth intact)',
                'Rank stable or improving',
                'Guidance raised or maintained',
            ]
        },
        'analysis_questions': [
            'Was this a beat or miss? By how much?',
            'What did guidance indicate?',
            'Does this validate the original investment thesis?',
            'How does the stock rank vs alternatives?',
            'What is the market reaction telling us?',
        ]
    }


def _regulatory_decision_framework() -> dict:
    """Decision framework for regulatory events."""
    return {
        'option_exit': {
            'action': 'EXIT',
            'label': 'Exit Position',
            'conditions': [
                'Business model at risk from regulatory action',
                'High potential financial exposure (fines, revenue loss)',
                'Long uncertain timeline to resolution',
                'Better alternatives without regulatory overhang',
            ]
        },
        'option_hold': {
            'action': 'HOLD',
            'label': 'Hold Position',
            'conditions': [
                'Risk appears priced in (stock already declined)',
                'Similar past cases resolved favorably',
                'Core business fundamentals unaffected',
                'Strong competitive position despite regulatory risk',
            ]
        },
        'analysis_questions': [
            'Who is the regulator (DOJ, FTC, EU, SEC)?',
            'What is the potential financial impact?',
            'Is the business model at risk?',
            'How have similar cases resolved historically?',
            'Is the risk already reflected in the stock price?',
        ]
    }


def _leadership_decision_framework() -> dict:
    """Decision framework for leadership change events."""
    return {
        'option_exit': {
            'action': 'EXIT',
            'label': 'Exit Position',
            'conditions': [
                'Unexpected departure (fired/sudden resignation)',
                'No clear successor identified',
                'High strategy uncertainty',
                'Key initiatives at risk without leadership continuity',
            ]
        },
        'option_hold': {
            'action': 'HOLD',
            'label': 'Hold Position',
            'conditions': [
                'Planned retirement with transition period',
                'Strong internal successor named',
                'Strategy expected to continue unchanged',
                'Company has deep management bench',
            ]
        },
        'analysis_questions': [
            'Was this planned or unexpected?',
            'Is a successor named or search underway?',
            'What is the transition timeline?',
            'Will company strategy change?',
            'How is the market reacting?',
        ]
    }


def _ma_decision_framework() -> dict:
    """Decision framework for M&A events."""
    return {
        'option_if_target': {
            'action': 'EVALUATE',
            'label': 'If Being Acquired',
            'conditions': [
                'Consider holding for deal premium',
                'Assess deal certainty (regulatory approval risk)',
                'Compare current price to offer price',
                'Evaluate deal timeline and completion risk',
            ]
        },
        'option_if_acquirer': {
            'action': 'EVALUATE',
            'label': 'If Making Acquisition',
            'conditions': [
                'Assess strategic fit of the acquisition',
                'Evaluate integration risk and complexity',
                'Check if deal is accretive or dilutive',
                'Consider impact on competitive position',
            ]
        },
        'analysis_questions': [
            'Is the holding the target or the acquirer?',
            'What are the deal terms?',
            'What is the regulatory approval risk?',
            'Does this strengthen or weaken the investment case?',
        ]
    }


# =============================================================================
# Prompt Formatting
# =============================================================================

def format_events_for_prompt(event_analyses: list) -> str:
    """
    Format event analyses into a text section for the AI prompt.

    This section is inserted BEFORE standard recommendations to ensure
    the AI addresses material events with priority.

    Args:
        event_analyses: List of enriched event analysis dicts

    Returns:
        Formatted string for inclusion in AI prompt
    """
    if not event_analyses:
        return ""

    lines = [
        "",
        "=" * 60,
        "MATERIAL EVENTS DETECTED - DEEP ANALYSIS REQUIRED",
        "=" * 60,
        "",
        "The following material events affect stocks you currently HOLD.",
        "For each event, you MUST provide deep analysis in your response.",
        "Address each event explicitly before making standard recommendations.",
        "",
    ]

    for i, analysis in enumerate(event_analyses, 1):
        event = analysis['event']
        pos = analysis['position_context']
        thesis = analysis['thesis_context']
        market = analysis['market_reaction']
        framework = analysis.get('decision_framework', {})

        lines.append("-" * 60)
        lines.append(f"EVENT {i}: {event['ticker']} - {event['event_type'].upper()}")
        lines.append(f"Priority: {event['priority']}")
        lines.append("-" * 60)

        # What happened
        lines.append(f"\nWHAT HAPPENED:")
        lines.append(f"  {event['headline']}")
        if event.get('article_count', 0) > 1:
            lines.append(f"  Coverage: {event['article_count']} articles ({event.get('frequency', 'N/A')} frequency)")

        # Position context
        lines.append(f"\nYOUR POSITION:")
        lines.append(f"  Holding: {pos['quantity']} shares @ ${pos['entry_price']:.2f} entry")
        lines.append(f"  Current: ${pos['current_price']:.2f} ({pos['pnl_pct']:+.1f}% P&L)")
        lines.append(f"  Position value: ${pos['position_value']:.2f}")
        lines.append(f"  Days held: {pos['days_held']} ({'SELLABLE' if pos['is_sellable'] else 'LOCKED - cannot sell'})")

        # Market reaction
        lines.append(f"\nMARKET REACTION:")
        lines.append(f"  30-day return: {market['return_30d']:+.2f}%")
        lines.append(f"  vs SPY: {market['vs_spy']:+.2f}%")
        lines.append(f"  RSI: {market['rsi']:.1f}")
        lines.append(f"  Trend: {market['trend']}")

        # Thesis context
        if thesis['has_thesis']:
            lines.append(f"\nACTIVE NARRATIVES:")
            for theme, summary in zip(thesis['active_themes'], thesis['active_summaries']):
                lines.append(f"  - {theme}: {summary}")
            if thesis['resolved_themes']:
                lines.append(f"  Recently resolved: {', '.join(thesis['resolved_themes'])}")
        else:
            lines.append(f"\nACTIVE NARRATIVES: No prior narratives tracked for this stock")

        # Decision framework
        lines.append(f"\nDECISION FRAMEWORK:")
        for key, option in framework.items():
            if key == 'analysis_questions':
                continue
            action = option.get('action', '')
            label = option.get('label', '')
            conditions = option.get('conditions', [])
            lines.append(f"\n  {label} ({action}):")
            for cond in conditions:
                lines.append(f"    - {cond}")

        # Analysis questions for the AI
        questions = framework.get('analysis_questions', [])
        if questions:
            lines.append(f"\n  QUESTIONS TO ADDRESS:")
            for q in questions:
                lines.append(f"    - {q}")

        lines.append("")

    # Instructions for the AI
    lines.append("=" * 60)
    lines.append("RESPONSE REQUIREMENTS FOR MATERIAL EVENTS:")
    lines.append("=" * 60)
    lines.append("")
    lines.append("For each material event above, your response MUST include:")
    lines.append("1. EVENT ASSESSMENT: What happened and its significance")
    lines.append("2. THESIS VALIDATION: Does this validate or invalidate the investment case?")
    lines.append("3. HOLD vs EXIT ANALYSIS: Specific reasoning for each option")
    lines.append("4. CLEAR RECOMMENDATION: EXIT or HOLD with confidence level")
    lines.append("")
    lines.append("Include this analysis in the 'reasoning' field of the relevant action.")
    lines.append("If recommending EXIT, explain why the event changes the outlook.")
    lines.append("If recommending HOLD, explain why the thesis remains intact.")
    lines.append("")

    return "\n".join(lines)
