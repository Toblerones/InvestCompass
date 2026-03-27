"""
ai_agent.py - LLM Integration (Claude API)

Responsibilities:
- Build prompt from market context + portfolio state + strategy rules
- Call Claude API
- Parse JSON response
- Validate recommendations against hard constraints
- Handle API errors

Key Functions:
- build_prompt(context: dict, strategy: str) -> str
- get_recommendation(context: dict, strategy: str) -> dict
- parse_recommendation(response: str) -> dict
- validate_actions(actions: list, context: dict) -> list
"""

import os
import sys
import json
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# =============================================================================
# Logging Configuration
# =============================================================================

# Setup logging to file for debugging AI responses
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("ai_agent")
logger.setLevel(logging.DEBUG)

# File handler - logs full responses for debugging
log_file = LOG_DIR / "ai_agent.log"
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))
logger.addHandler(file_handler)


# =============================================================================
# Retry Configuration
# =============================================================================

MAX_API_RETRIES = 3
RETRY_DELAY = 2.0
RETRY_BACKOFF = 2.0


# =============================================================================
# Pre-computation (hard constraints and cash flows)
# =============================================================================

def pre_compute_constraints(context: dict) -> dict:
    """
    Compute all hard constraint states from context before the prompt is built.
    The LLM receives facts, not rules.
    """
    config = context.get('config', {})
    positions = context.get('current_positions', [])
    cash = context.get('cash_available', 0)

    total_value = cash + sum(
        p.get('total_quantity', 0) * p.get('current_price', 0) for p in positions
    )
    cash_ratio = cash / total_value if total_value > 0 else 1.0

    THESIS_ASSESSMENT_THRESHOLD = -0.10   # hardcoded — triggers LLM judgment
    catastrophic_threshold = config.get('stop_loss_percent', -20) / 100  # -0.20

    # Per-lot breach detection (sellable lots only)
    thesis_assessment_required = []
    catastrophic_breaches = []
    sellable_lots = {}

    # Lock status lookup (built by analyzer)
    lock_status_map = context.get('portfolio_lock_status', {}).get('positions', {})

    for pos in positions:
        ticker = pos.get('ticker', '')
        current_price = pos.get('current_price', 0)
        lots = pos.get('lots', [])
        lock_info = lock_status_map.get(ticker, {})

        sellable_qty = lock_info.get('sellable_quantity', 0)
        next_unlock = lock_info.get('unlock_date')

        sellable_lots[ticker] = {
            'sellable_qty': sellable_qty,
            'total_qty': pos.get('total_quantity', 0),
            'next_unlock': next_unlock,
        }

        for i, lot in enumerate(lots):
            if not lot.get('is_sellable', False):
                continue
            purchase_price = lot.get('purchase_price', 0)
            if purchase_price <= 0:
                continue
            pnl_pct = (current_price - purchase_price) / purchase_price
            if pnl_pct <= catastrophic_threshold:
                catastrophic_breaches.append({
                    'ticker': ticker,
                    'lot': i + 1,
                    'purchase_price': purchase_price,
                    'current_price': current_price,
                    'pnl_pct': round(pnl_pct * 100, 2),
                    'sellable': True,
                })
            elif pnl_pct <= THESIS_ASSESSMENT_THRESHOLD:
                thesis_assessment_required.append({
                    'ticker': ticker,
                    'lot': i + 1,
                    'purchase_price': purchase_price,
                    'current_price': current_price,
                    'pnl_pct': round(pnl_pct * 100, 2),
                    'sellable': lot.get('is_sellable', False),
                })

    # Earnings blackouts — derived from positions and opportunities
    no_sell = []   # earnings within 3 days
    no_buy = []    # earnings within 7 days
    all_tickers_with_earnings = (
        list(context.get('current_positions', []))
        + list(context.get('entry_opportunities', []))
    )
    for item in all_tickers_with_earnings:
        ticker = item.get('ticker', '')
        earnings = item.get('earnings')
        if not earnings:
            continue
        days = earnings.get('days_until', 999)
        if 0 < days <= 3 and earnings.get('sell_restricted'):
            no_sell.append(ticker)
        if 0 < days <= 7 and earnings.get('buy_restricted'):
            no_buy.append(ticker)

    # Concentration per ticker
    concentration = {}
    for pos in positions:
        ticker = pos.get('ticker', '')
        if total_value > 0:
            concentration[ticker] = round(
                (pos.get('total_quantity', 0) * pos.get('current_price', 0)) / total_value, 3
            )

    # Max single-position concentration from investor profile
    profile = config.get('investor_profile', {})
    sig = profile.get('portfolio_significance', 'Meaningful')
    max_concentration = 0.35 if sig == 'Primary' else (0.40 if sig == 'Meaningful' else 0.50)

    return {
        'thesis_assessment_required': thesis_assessment_required,
        'catastrophic_breaches': catastrophic_breaches,
        'earnings_blackouts': {'no_sell': no_sell, 'no_buy': no_buy},
        'sellable_lots': sellable_lots,
        'cash_ratio': round(cash_ratio, 3),
        'framework_e_required': cash_ratio > 0.50,
        'position_count': len(positions),
        'max_positions': config.get('max_positions', 3),
        'concentration': concentration,
        'max_concentration': max_concentration,
        'cash': cash,
        'total_value': round(total_value, 2),
    }


def pre_compute_cash_flows(context: dict) -> dict:
    """
    Calculate available cash and maximum proceeds from sellable positions.
    Passed to the LLM as context — the LLM selects actions, Python validates the math.
    """
    config = context.get('config', {})
    fee = config.get('transaction_fee', 1.0)
    cash = context.get('cash_available', 0)
    lock_status_map = context.get('portfolio_lock_status', {}).get('positions', {})

    sellable_positions = {}
    total_max_proceeds = 0.0

    for pos in context.get('current_positions', []):
        ticker = pos.get('ticker', '')
        lock_info = lock_status_map.get(ticker, {})
        sellable_qty = lock_info.get('sellable_quantity', 0)
        if sellable_qty > 0:
            current_price = pos.get('current_price', 0)
            proceeds = max(0.0, (sellable_qty * current_price) - fee)
            sellable_positions[ticker] = {
                'sellable_qty': sellable_qty,
                'current_price': current_price,
                'max_proceeds': round(proceeds, 2),
            }
            total_max_proceeds += proceeds

    return {
        'starting_cash': round(cash, 2),
        'sellable_positions': sellable_positions,
        'max_deployable': round(cash + total_max_proceeds, 2),
    }


def build_situation_summary(constraints: dict, cash_flows: dict, context: dict) -> str:
    """
    Translate pre-computed constraint and cash flow dicts into plain English.
    Injected at the top of the prompt as an authoritative facts block.
    """
    lines = ["SITUATION SUMMARY (pre-computed — do not recalculate):", ""]

    pos_count = constraints['position_count']
    max_pos = constraints['max_positions']
    available = max(0, max_pos - pos_count)
    lines.append(f"Portfolio: {pos_count} position(s), {available} slot(s) available.")

    cash = cash_flows['starting_cash']
    cash_pct = int(constraints['cash_ratio'] * 100)
    fe_note = " — Framework E required: justify deployment or hold." if constraints['framework_e_required'] else ""
    lines.append(f"Cash: ${cash:,.2f} ({cash_pct}% of portfolio){fe_note}")
    lines.append("")

    # Per-position lot summary
    for ticker, lot_info in constraints['sellable_lots'].items():
        sellable = lot_info['sellable_qty']
        total = lot_info['total_qty']
        locked = total - sellable
        next_unlock = lot_info.get('next_unlock') or 'unknown date'
        if locked > 0:
            lines.append(
                f"{ticker}: {total} share(s) held, {sellable} sellable "
                f"({locked} locked until {next_unlock})."
            )
        else:
            lines.append(f"{ticker}: {total} share(s) held, all sellable.")

    # Catastrophic floor (hard constraint — system will enforce SELL)
    for breach in constraints.get('catastrophic_breaches', []):
        lines.append(
            f"CATASTROPHIC FLOOR: {breach['ticker']} Lot {breach['lot']} at "
            f"{breach['pnl_pct']}% from ${breach['purchase_price']:.2f}. "
            f"Unconditional exit required — system will enforce SELL."
        )

    # Thesis assessment trigger (judgment — LLM must assess before acting)
    for item in constraints.get('thesis_assessment_required', []):
        status = "Sellable" if item['sellable'] else "Locked"
        lines.append(
            f"THESIS ASSESSMENT REQUIRED: {item['ticker']} Lot {item['lot']} at "
            f"{item['pnl_pct']}% from ${item['purchase_price']:.2f} ({status}). "
            f"Before any recommendation for {item['ticker']}: assess whether this weakness "
            f"is macro-driven or reflects genuine thesis deterioration. "
            f"State conclusion explicitly in reasoning."
        )

    lines.append("")

    # Cash flow if positions sold
    for ticker, cf in cash_flows['sellable_positions'].items():
        lines.append(
            f"If {ticker} ({cf['sellable_qty']} share(s)) sold: "
            f"${cf['max_proceeds']:,.2f} proceeds → ${cash_flows['max_deployable']:,.2f} total available."
        )

    # Earnings blackouts
    no_sell = constraints['earnings_blackouts']['no_sell']
    no_buy = constraints['earnings_blackouts']['no_buy']
    if no_sell:
        lines.append(f"⚠ Sell blackout (earnings within 3 days): {', '.join(no_sell)}")
    else:
        lines.append("No sell restrictions active (no earnings within 3 days).")
    if no_buy:
        lines.append(f"⚠ Buy blackout (earnings within 7 days): {', '.join(no_buy)}")
    else:
        lines.append("No buy restrictions active (no earnings within 7 days).")

    return "\n".join(lines)


def _format_investor_stance(config: dict) -> str:
    """
    Generate a single synthesised investor stance paragraph from config values.
    Replaces the 6-dimension verbose profile block — communicates net effect only.
    """
    profile = config.get('investor_profile', {})
    defaults = {
        'risk_tolerance': 'Moderate',
        'ai_thesis_conviction': 'High',
        'lock_period_comfort': 'Medium',
        'cash_buffer_preference': 'Moderate',
        'portfolio_significance': 'Meaningful',
        'drawdown_behaviour': 'Hold through',
    }
    p = {k: profile.get(k, defaults[k]) for k in defaults}

    risk_map = {
        'Conservative': 'a capital-preservation investor — smaller positions, higher conviction required before averaging down.',
        'Moderate': 'a moderate-risk investor — balance growth and preservation, apply frameworks as designed.',
        'Aggressive': 'a growth-oriented investor — deploy cash more actively, accept higher concentration.',
    }
    ai_map = {
        'Low': 'No AI sector weighting — treat AI infrastructure stocks like any other.',
        'Medium': 'Mild preference for top-ranked AI names. No special treatment.',
        'High': 'High conviction in the AI infrastructure supercycle — weight thesis strength heavily. '
                'Enter AI names despite RSI > 50 if thesis is actively strengthening.',
    }
    lock_map = {
        'Low': 'Reduce averaging scale by 50% or defer if SPY 30-day return is negative.',
        'Medium': 'Accept lock periods normally. No scale reduction unless macro is clearly deteriorating.',
        'High': 'Lock period is not a moderating factor — apply averaging scale fully.',
    }
    buffer_map = {
        'Minimal': 'Comfortable with <15% cash when high-conviction opportunities exist.',
        'Moderate': 'Prefer 20–35% cash buffer. Framework E triggers at >50% cash.',
        'Substantial': 'Prefer 35–50% cash buffer. Framework E triggers at >65% cash (not >50%).',
    }
    sig_map = {
        'Discretionary': 'Max single position: 50% of portfolio.',
        'Meaningful': 'Max single position: 40% of portfolio.',
        'Primary': 'Max single position: 35%. Require two confirming thesis signals before averaging down.',
    }
    drawdown_map = {
        'Hold through': ('Hold through drawdowns unless thesis assessment concludes deterioration. '
                         'No early exit flags — catastrophic floor at -20% is the only unconditional stop.'),
        'Tighten gradually': 'At -7% loss, reassess thesis explicitly. Flag exit if two or more minor concerns.',
        'Exit early': 'At -6% loss, begin flagging exit option. Recommend partial exit if two or more minor concerns.',
    }

    lines = [
        f"You are advising {risk_map.get(p['risk_tolerance'], risk_map['Moderate'])}",
        ai_map.get(p['ai_thesis_conviction'], ai_map['High']),
        buffer_map.get(p['cash_buffer_preference'], buffer_map['Moderate']),
        sig_map.get(p['portfolio_significance'], sig_map['Meaningful']),
        lock_map.get(p['lock_period_comfort'], lock_map['Medium']),
        drawdown_map.get(p['drawdown_behaviour'], drawdown_map['Hold through']),
    ]
    return "\n".join(lines)


# =============================================================================
# Prompt Building
# =============================================================================

def build_prompt(context: dict, strategy: str, narratives: dict = None,
                 market_data: dict = None, situation_summary: str = None,
                 config: dict = None) -> str:
    """
    Build the prompt for Claude API.

    Args:
        context: Market context from analyzer.generate_market_context()
        strategy: Strategy principles text
        narratives: Optional narratives dictionary for context memory
        market_data: Optional raw market data for event analysis
        situation_summary: Pre-computed situation summary (from build_situation_summary)
        config: Config dict (falls back to context['config'] if not provided)

    Returns:
        Formatted prompt string
    """
    # Resolve config
    cfg = config if config is not None else context.get('config', {})

    # Import narrative formatter if narratives provided
    narratives_text = ""
    if narratives:
        from .narrative_manager import format_narratives_for_prompt, has_narratives
        held_tickers = [p.get('ticker') for p in context.get('current_positions', [])]
        top_3 = context.get('top_3_tickers', [])
        all_tickers = list(set(held_tickers + top_3))
        if has_narratives(narratives):
            narratives_text = format_narratives_for_prompt(narratives, all_tickers)

    # Format material events section (if any detected)
    material_events_text = ""
    material_events = context.get('material_events', [])
    if material_events and market_data:
        from .event_detector import build_event_analysis, format_events_for_prompt
        portfolio_positions = []
        for pos in context.get('current_positions', []):
            portfolio_positions.append({
                'ticker': pos.get('ticker', ''),
                'lots': pos.get('lots', [{
                    'quantity': pos.get('total_quantity', 0),
                    'purchase_price': pos.get('average_cost', 0),
                    'purchase_date': pos.get('lots', [{}])[0].get('purchase_date', '') if pos.get('lots') else '',
                }]),
            })
        portfolio_for_events = {'positions': portfolio_positions}
        event_analyses = build_event_analysis(
            material_events, portfolio_for_events, market_data, narratives
        )
        material_events_text = format_events_for_prompt(event_analyses)

    # Format context sections
    positions_text = _format_positions(context.get('current_positions', []))
    rankings_text = _format_rankings(context.get('rankings', {}))
    opportunities_text = _format_opportunities(context.get('entry_opportunities', []))
    news_text = _format_news(context.get('news_highlights', []))
    price_context_text = _format_price_context(context)
    earnings_text = _format_earnings_calendar(context)

    cash = context.get('cash_available', 0)
    transaction_fee = cfg.get('transaction_fee', 1)
    investor_stance = _format_investor_stance(cfg)

    prompt = f"""You are a portfolio advisor managing a tech stock portfolio.

{situation_summary if situation_summary else ""}

STRATEGY PRINCIPLES:
{strategy}

{investor_stance}

CURRENT PORTFOLIO:
{positions_text}

Cash Available: ${cash:,.2f}

STOCK RANKINGS (by fundamental score):
{rankings_text}

ENTRY OPPORTUNITIES (Top 3 not in portfolio):
{opportunities_text}

RECENT NEWS:
{news_text}

PRICE CONTEXT (30-day performance vs market):
{price_context_text}

EARNINGS CALENDAR:
{earnings_text}

{material_events_text}
ONGOING NARRATIVES (from previous analysis):
{narratives_text if narratives_text else "No prior narratives tracked (first run or no active themes)."}

CONSTRAINTS:
- Maximum positions: {cfg.get('max_positions', 3)}
- Transaction fee: ${transaction_fee} per trade
- Monthly deposit budget: ${cfg.get('monthly_budget', 300)} (external capital not in the portfolio — never add to or subtract from available cash. Only mention in risk_warnings if confidence=HIGH and cash is insufficient: "Consider depositing your monthly budget to fund this position.")
- Stop loss threshold: {cfg.get('stop_loss_percent', -10)}%
- Profit target: +{cfg.get('profit_target_percent', 20)}%

NARRATIVE UPDATES:
For each tracked ticker, update the summary of any theme with new market developments.
Keep to market intelligence only (news, analyst views, thesis signals, price levels as
external data). Return updates in the same JSON structure as before.

YOUR TASK:
Review the SITUATION SUMMARY, then work through the DECISION QUESTIONS in the strategy.

Return a JSON object:
{{
  "actions": [
    {{
      "type": "SELL" | "BUY" | "HOLD" | "WAIT",
      "ticker": "SYMBOL",
      "amount": "all shares" | "$XXX" | "X shares",
      "reasoning": "2-3 sentences: what signal drove this, how investor stance influenced it if at all, key risk to watch"
    }}
  ],
  "overall_strategy": "1-2 sentence portfolio-level view",
  "risk_warnings": ["Warning 1", "Warning 2"],
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "narrative_updates": {{
    "TICKER": {{
      "add": [{{"theme": "regulatory_risk", "summary": "DOJ investigation announced", "impact": "negative"}}],
      "update": [{{"theme": "earnings_concern", "summary": "Updated: Q4 guidance lowered", "impact": "negative"}}],
      "resolve": ["acquisition_rumor"]
    }}
  }}
}}

Use WAIT (not HOLD) when entry conditions are right but capital is locked or timing is poor.
Apply the investor stance — state explicitly when it moderates a recommendation.
Do not recalculate any fact from the SITUATION SUMMARY.

Important: Your response must be valid JSON only, no markdown or other formatting."""

    return prompt


def _format_investor_profile(config: dict) -> str:
    """Format investor profile block for prompt injection."""
    profile = config.get('investor_profile', {})
    defaults = {
        'risk_tolerance': 'Moderate',
        'ai_thesis_conviction': 'High',
        'lock_period_comfort': 'Medium',
        'cash_buffer_preference': 'Moderate',
        'portfolio_significance': 'Meaningful',
        'drawdown_behaviour': 'Hold through',
    }
    p = {k: profile.get(k, defaults[k]) for k in defaults}
    return (
        f"- Risk Tolerance: {p['risk_tolerance']}\n"
        f"- AI Thesis Conviction: {p['ai_thesis_conviction']}\n"
        f"- Lock-Period Comfort: {p['lock_period_comfort']}\n"
        f"- Cash Buffer Preference: {p['cash_buffer_preference']}\n"
        f"- Portfolio Significance: {p['portfolio_significance']}\n"
        f"- Drawdown Behaviour: {p['drawdown_behaviour']}"
    )


def _format_positions(positions: list) -> str:
    """Format consolidated positions (lot-based) for prompt."""
    if not positions:
        return "No current positions."

    lines = []
    for pos in positions:
        ticker = pos.get('ticker', '')
        total_qty = pos.get('total_quantity', 0)
        avg_cost = pos.get('average_cost', 0)
        current = pos.get('current_price', 0)
        pnl = pos.get('pnl_percent', 0)
        rank = pos.get('rank', 'N/A')
        lock_status = pos.get('lock_status', 'LOCKED')
        sellable_qty = pos.get('sellable_quantity', 0)
        lots = pos.get('lots', [])

        lines.append(
            f"- {ticker}: {total_qty} shares total, avg cost ${avg_cost:.2f} (now ${current:.2f}), "
            f"P&L: {pnl:+.1f}%, Rank: #{rank}, Status: {lock_status}"
        )

        if lock_status == 'PARTIAL_LOCK':
            lines.append(
                f"  Sellable: {sellable_qty} of {total_qty} shares (FIFO order)"
            )

        # Show lot breakdown
        if len(lots) > 1:
            for i, lot in enumerate(lots):
                lot_qty = lot.get('quantity', 0)
                lot_price = lot.get('purchase_price', 0)
                lot_days = lot.get('days_held', 0)
                lot_pnl = lot.get('pnl_percent', 0)
                lot_sellable = "SELLABLE" if lot.get('is_sellable', False) else "LOCKED"
                lines.append(
                    f"  Lot {i+1}: {lot_qty} shares @ ${lot_price:.2f} "
                    f"({lot_days}d, {lot_pnl:+.1f}%) {lot_sellable}"
                )

        # Add exit signals/warnings
        for signal in pos.get('exit_signals', []):
            lines.append(f"  [!] {signal}")
        for warning in pos.get('exit_warnings', []):
            lines.append(f"  [!] {warning}")

    return "\n".join(lines)


def _format_rankings(rankings: dict) -> str:
    """Format stock rankings for prompt."""
    if not rankings:
        return "No rankings available."

    lines = []
    sorted_rankings = sorted(rankings.items(), key=lambda x: x[1].get('rank', 99))

    for ticker, data in sorted_rankings[:10]:  # Top 10
        rank = data.get('rank', 0)
        score = data.get('score', 0)
        fundamentals = data.get('fundamentals', {})
        technicals = data.get('technicals', {})

        pe = fundamentals.get('pe_ratio', 0)
        rev_growth = (fundamentals.get('revenue_growth_yoy', 0) or 0) * 100
        rsi = technicals.get('rsi_14', 0)

        lines.append(
            f"#{rank} {ticker}: Score={score:.1f}, P/E={pe:.1f}, "
            f"RevGrowth={rev_growth:.1f}%, RSI={rsi:.1f}"
        )

    return "\n".join(lines)


def _format_opportunities(opportunities: list) -> str:
    """Format entry opportunities for prompt."""
    if not opportunities:
        return "No entry opportunities (all top 3 already held)."

    lines = []
    for opp in opportunities:
        ticker = opp.get('ticker', '')
        rank = opp.get('rank', 0)
        price = opp.get('current_price', 0)
        rec = opp.get('entry_recommendation', '')
        rsi = opp.get('rsi', 50)

        lines.append(
            f"- {ticker} (Rank #{rank}): ${price:.2f}, RSI={rsi:.1f}, Entry: {rec}"
        )

        for signal in opp.get('entry_signals', []):
            lines.append(f"  [+] {signal}")
        for warning in opp.get('entry_warnings', []):
            lines.append(f"  [!] {warning}")

    return "\n".join(lines)


def _format_lock_status(lock_status: dict) -> str:
    """Format portfolio lock status for prompt."""
    total = lock_status.get('total_positions', 0)
    sellable = lock_status.get('sellable_count', 0)
    partially = lock_status.get('partially_sellable_count', 0)
    locked = lock_status.get('locked_count', 0)
    next_unlock = lock_status.get('next_unlock_date', '')

    if total == 0:
        return "No positions to evaluate."

    status = f"Total: {total} stocks, Fully sellable: {sellable}, Partially sellable: {partially}, Fully locked: {locked}"
    if next_unlock:
        status += f"\nNext unlock date: {next_unlock}"

    return status


def _format_news(news: list) -> str:
    """
    Format enhanced news themes for prompt.

    Args:
        news: List of theme highlights with frequency and article counts

    Returns:
        Formatted news showing material themes with trend indicators
    """
    if not news:
        return "No material news themes identified."

    lines = []
    seen = set()  # Avoid duplicates
    for item in news[:10]:
        ticker = item.get('ticker', '')
        theme_name = item.get('theme_name', 'unknown').replace('_', ' ').title()
        headline = item.get('headline', '')
        date = item.get('date', '')
        source = item.get('source', 'Unknown')
        article_count = item.get('article_count', 1)
        frequency = item.get('frequency', 'LOW')

        # Create unique key to avoid duplicates
        key = f"{ticker}:{theme_name}:{headline}"
        if headline and key not in seen:
            # Format: [TICKER] Theme (FREQ - N articles): Headline (Date, Source)
            lines.append(
                f"- [{ticker}] {theme_name} ({frequency} frequency - {article_count} articles): "
                f"{headline} ({date}, {source})"
            )
            seen.add(key)

    return "\n".join(lines) if lines else "No material news themes identified."


def _format_price_context(context: dict) -> str:
    """
    Format price context showing 30-day performance vs benchmark.

    Args:
        context: Market context containing benchmark and position data

    Returns:
        Formatted price context string
    """
    benchmark = context.get('benchmark', {})
    benchmark_return = benchmark.get('return_30d', 0)
    positions = context.get('current_positions', [])
    opportunities = context.get('entry_opportunities', [])

    lines = [f"Market Benchmark (SPY): {benchmark_return:+.2f}% (30-day)"]
    lines.append("")

    # Current holdings performance
    if positions:
        lines.append("Current Holdings:")
        for pos in positions:
            ticker = pos.get('ticker', '')
            return_30d = pos.get('return_30d', 0)
            rel_perf = pos.get('relative_performance', 0)
            trend = pos.get('trend', 'UNKNOWN')

            trend_indicator = {
                'OUTPERFORMING': '(beating market)',
                'UNDERPERFORMING': '(lagging market)',
                'NEUTRAL': '(tracking market)',
                'UNKNOWN': ''
            }.get(trend, '')

            lines.append(
                f"  - {ticker}: {return_30d:+.2f}% vs SPY {rel_perf:+.2f}% {trend_indicator}"
            )
        lines.append("")

    # Entry opportunities performance
    if opportunities:
        lines.append("Entry Opportunities:")
        for opp in opportunities:
            ticker = opp.get('ticker', '')
            return_30d = opp.get('return_30d', 0)
            rel_perf = opp.get('relative_performance', 0)
            trend = opp.get('trend', 'UNKNOWN')

            trend_indicator = {
                'OUTPERFORMING': '(beating market)',
                'UNDERPERFORMING': '(lagging market)',
                'NEUTRAL': '(tracking market)',
                'UNKNOWN': ''
            }.get(trend, '')

            lines.append(
                f"  - {ticker}: {return_30d:+.2f}% vs SPY {rel_perf:+.2f}% {trend_indicator}"
            )

    return "\n".join(lines) if lines else "Price context unavailable."


def _format_holdings_for_cashflow(positions: list, transaction_fee: float) -> str:
    """
    Format consolidated holdings with prices for cash flow calculations.

    Shows sellable quantity separately from total for accurate SELL planning.

    Args:
        positions: List of consolidated positions with lots
        transaction_fee: Fee per transaction

    Returns:
        Formatted string showing holdings and potential proceeds
    """
    if not positions:
        return "No holdings to sell."

    lines = []
    for pos in positions:
        ticker = pos.get('ticker', '')
        total_qty = pos.get('total_quantity', 0)
        sellable_qty = pos.get('sellable_quantity', 0)
        current = pos.get('current_price', 0)
        lock_status = pos.get('lock_status', 'LOCKED')

        sellable_value = sellable_qty * current
        net_proceeds = sellable_value - transaction_fee if sellable_qty > 0 else 0

        lines.append(
            f"- {ticker}: {total_qty} total shares ({sellable_qty} sellable) x ${current:.2f} "
            f"= ${sellable_value:.2f} sellable value "
            f"(net after fee: ${net_proceeds:.2f}) [{lock_status}]"
        )

    return "\n".join(lines)


def _format_earnings_calendar(context: dict) -> str:
    """
    Format earnings calendar with trading restrictions for AI prompt.

    Args:
        context: Market context containing positions and opportunities with earnings data

    Returns:
        Formatted earnings calendar string with restrictions clearly stated
    """
    positions = context.get('current_positions', [])
    opportunities = context.get('entry_opportunities', [])

    imminent = []   # <= 7 days (restricted)
    upcoming = []   # 8-30 days (safe)
    no_data = []    # No data or > 30 days

    # Check held positions (only future earnings for calendar restrictions)
    for pos in positions:
        ticker = pos.get('ticker', '')
        earnings = pos.get('earnings')
        if earnings:
            if 0 < earnings['days_until'] <= 7:
                imminent.append((ticker, earnings, 'HELD'))
            elif 7 < earnings['days_until'] <= 30:
                upcoming.append((ticker, earnings))
            else:
                no_data.append(ticker)
        else:
            no_data.append(ticker)

    # Check entry opportunities (only future earnings)
    for opp in opportunities:
        ticker = opp.get('ticker', '')
        earnings = opp.get('earnings')
        if earnings:
            if 0 < earnings['days_until'] <= 7:
                imminent.append((ticker, earnings, 'OPPORTUNITY'))
            elif 7 < earnings['days_until'] <= 30:
                upcoming.append((ticker, earnings))
            else:
                no_data.append(ticker)
        else:
            no_data.append(ticker)

    lines = []

    # Imminent earnings - critical restrictions
    if imminent:
        lines.append("IMMINENT EARNINGS (Trading Restricted):")
        for ticker, earnings, position_type in imminent:
            days = earnings['days_until']
            date_str = earnings['date']
            lines.append(f"  {ticker}: {date_str} ({days} days away)")
            if earnings.get('sell_restricted'):
                lines.append(f"    - DO NOT SELL: Within 3-day blackout (gap risk, may miss runup)")
            if earnings.get('buy_restricted'):
                lines.append(f"    - DO NOT BUY: Within 7-day volatility window")
            lines.append(f"    - Action: HOLD current position, reassess after earnings")
        lines.append("")

    # Upcoming earnings - informational
    if upcoming:
        lines.append("Upcoming Earnings (Safe to Trade):")
        for ticker, earnings in upcoming:
            lines.append(f"  {ticker}: {earnings['date']} ({earnings['days_until']} days)")
        lines.append("")

    # No near-term earnings
    if no_data:
        lines.append(f"No Near-Term Earnings: {', '.join(set(no_data))}")

    if not lines:
        return "No earnings data available for tracked tickers."

    return "\n".join(lines)


# =============================================================================
# Claude API Integration
# =============================================================================

def get_recommendation(context: dict, strategy: str, narratives: dict = None,
                       market_data: dict = None, manual_mode: bool = False) -> dict:
    """
    Get AI recommendation from Claude API with retry logic.

    Args:
        context: Market context from analyzer
        strategy: Strategy principles text
        narratives: Optional narratives dictionary for context memory
        market_data: Optional raw market data for event analysis
        manual_mode: If True, write prompt to file and read response from stdin

    Returns:
        Parsed recommendation dictionary (includes narrative_updates if provided)
    """
    # Pre-compute hard constraints and cash flows (used in prompt + validation)
    constraints = pre_compute_constraints(context)
    cash_flows = pre_compute_cash_flows(context)
    situation_summary = build_situation_summary(constraints, cash_flows, context)
    cfg = context.get('config', {})

    # Build the prompt
    prompt = build_prompt(context, strategy, narratives, market_data,
                          situation_summary=situation_summary, config=cfg)

    if manual_mode:
        from pathlib import Path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        prompt_file = out_dir / f"prompt_{timestamp}.md"
        prompt_file.write_text(
            f"# InvestCompass Advisor Prompt\n\n```\n{prompt}\n```\n",
            encoding="utf-8"
        )
        print(f"\n[Manual Mode] Prompt saved to: {prompt_file}")
        print("Copy the prompt into Claude (or any LLM), then paste the JSON response")
        print("below. When done, press Ctrl+D (Mac/Linux) or Ctrl+Z then Enter (Windows):\n")
        response_text = sys.stdin.read().strip()
        recommendation = parse_recommendation(response_text)
        if recommendation.get('actions'):
            valid_actions, rejected_actions = validate_actions(
                recommendation['actions'], constraints, cash_flows, cfg
            )
            recommendation['actions'] = valid_actions
            recommendation['rejected_actions'] = rejected_actions
        return recommendation

    try:
        import anthropic
    except ImportError:
        return {
            'error': 'anthropic package not installed. Run: pip install anthropic',
            'actions': [],
            'overall_strategy': '',
            'risk_warnings': ['API client not available'],
            'confidence': 'LOW',
            'narrative_updates': {}
        }

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {
            'error': 'ANTHROPIC_API_KEY not found in environment',
            'actions': [],
            'overall_strategy': '',
            'risk_warnings': ['API key not configured'],
            'confidence': 'LOW',
            'narrative_updates': {}
        }

    client = anthropic.Anthropic(api_key=api_key)

    # Retry loop
    last_error = None
    current_delay = RETRY_DELAY

    for attempt in range(MAX_API_RETRIES + 1):
        try:
            message = client.messages.create(
                model="claude-opus-4-5-20251101",
                max_tokens=4000,
                temperature=0.3,  # Lower temp for more consistent reasoning
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract response text
            response_text = message.content[0].text

            # Parse the response
            recommendation = parse_recommendation(response_text)

            # Validate actions against pre-computed constraints
            if recommendation.get('actions'):
                valid_actions, rejected_actions = validate_actions(
                    recommendation['actions'], constraints, cash_flows, cfg
                )
                recommendation['actions'] = valid_actions
                recommendation['rejected_actions'] = rejected_actions

            return recommendation

        except anthropic.APIConnectionError as e:
            last_error = ('connection', str(e))
            if attempt < MAX_API_RETRIES:
                print(f"  [!] API connection failed (attempt {attempt + 1}/{MAX_API_RETRIES + 1})")
                print(f"      Retrying in {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay *= RETRY_BACKOFF
            continue

        except anthropic.RateLimitError as e:
            last_error = ('rate_limit', str(e))
            if attempt < MAX_API_RETRIES:
                # Rate limit needs longer delay
                wait_time = current_delay * 2
                print(f"  [!] Rate limited (attempt {attempt + 1}/{MAX_API_RETRIES + 1})")
                print(f"      Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                current_delay *= RETRY_BACKOFF
            continue

        except anthropic.APIStatusError as e:
            # Don't retry on 4xx client errors (except 429 rate limit)
            if hasattr(e, 'status_code') and 400 <= e.status_code < 500:
                return {
                    'error': f'API error ({e.status_code}): {str(e)}',
                    'actions': [],
                    'overall_strategy': '',
                    'risk_warnings': ['API returned a client error'],
                    'confidence': 'LOW'
                }
            last_error = ('api_status', str(e))
            if attempt < MAX_API_RETRIES:
                print(f"  [!] API error (attempt {attempt + 1}/{MAX_API_RETRIES + 1})")
                print(f"      Retrying in {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay *= RETRY_BACKOFF
            continue

        except Exception as e:
            last_error = ('unexpected', str(e))
            break  # Don't retry on unexpected errors

    # All retries failed
    error_type, error_msg = last_error if last_error else ('unknown', 'Unknown error')

    error_messages = {
        'connection': ('Could not connect to Claude API', 'Connection error'),
        'rate_limit': ('API rate limit reached after retries', 'Rate limit exceeded'),
        'api_status': ('API returned an error', 'API error'),
        'unexpected': ('An unexpected error occurred', 'Unexpected error'),
        'unknown': ('Unknown error occurred', 'Unknown error')
    }

    warning, prefix = error_messages.get(error_type, error_messages['unknown'])

    return {
        'error': f'{prefix}: {error_msg}',
        'actions': [],
        'overall_strategy': '',
        'risk_warnings': [warning],
        'confidence': 'LOW'
    }


# =============================================================================
# Response Parsing
# =============================================================================

def parse_recommendation(response: str) -> dict:
    """
    Parse Claude's response into structured recommendation.

    Args:
        response: Raw response text from Claude

    Returns:
        Parsed recommendation dictionary
    """
    # Log full response for debugging
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"=== AI Response at {timestamp} ===")
    logger.info(f"Response length: {len(response)} chars")
    logger.debug(f"Full response:\n{response}")

    # Default structure
    default = {
        'actions': [],
        'overall_strategy': '',
        'risk_warnings': [],
        'confidence': 'LOW',
        'narrative_updates': {},
        'raw_response': response
    }

    try:
        # Try to parse as JSON directly
        result = json.loads(response)
        logger.info("Successfully parsed JSON directly")
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Direct JSON parse failed: {e}")

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                logger.info("Successfully parsed JSON from markdown code block")
                return result
            except json.JSONDecodeError as e2:
                logger.warning(f"Markdown block JSON parse failed: {e2}")

        # Try to find JSON object in response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group())
                logger.info("Successfully parsed JSON from regex extraction")
                return result
            except json.JSONDecodeError as e3:
                logger.warning(f"Regex JSON parse failed: {e3}")

        # Return default with error
        logger.error(f"All JSON parse attempts failed. Response logged above.")
        default['error'] = 'Could not parse JSON response'
        default['overall_strategy'] = 'Unable to parse AI response. Please review manually.'
        return default


# =============================================================================
# Action Validation
# =============================================================================

def validate_actions(actions: list, constraints: dict, cash_flows: dict,
                     config: dict) -> tuple:
    """
    Validate actions against pre-computed hard constraints.
    Returns (valid_actions, rejected_actions).

    Rejected actions are removed from the valid list and include a rejection_reason.
    Valid actions may still carry validation_warning for soft issues.

    Args:
        actions: List of action dictionaries from LLM
        constraints: Pre-computed constraints from pre_compute_constraints()
        cash_flows: Pre-computed cash flows from pre_compute_cash_flows()
        config: Config dictionary

    Returns:
        Tuple of (valid_actions, rejected_actions)
    """
    valid = []
    rejected = []

    sellable_lots = constraints.get('sellable_lots', {})
    no_sell = constraints.get('earnings_blackouts', {}).get('no_sell', [])
    no_buy = constraints.get('earnings_blackouts', {}).get('no_buy', [])
    position_count = constraints.get('position_count', 0)
    max_positions = constraints.get('max_positions', 3)
    concentration = constraints.get('concentration', {})
    max_conc = constraints.get('max_concentration', 0.50)
    total_value = constraints.get('total_value', 0)
    transaction_fee = config.get('transaction_fee', 1.0)

    # Running cash: starts with available cash, increases as SELLs are processed
    running_cash = cash_flows.get('starting_cash', 0)
    # Track new positions added by BUYs this cycle
    new_positions = set()

    for action in actions:
        action_type = action.get('type', '').upper()
        ticker = action.get('ticker', '')

        if action_type == 'SELL':
            lot_info = sellable_lots.get(ticker, {})
            sellable_qty = lot_info.get('sellable_qty', 0)
            next_unlock = lot_info.get('next_unlock', 'N/A')

            if ticker in no_sell:
                action['rejection_reason'] = (
                    f"{ticker} has earnings within 3 days — sell blackout active."
                )
                rejected.append(action)
                continue

            if sellable_qty <= 0:
                action['rejection_reason'] = (
                    f"{ticker} has no sellable lots. "
                    f"All shares locked until {next_unlock}."
                )
                rejected.append(action)
                continue

            # Valid SELL — add proceeds to running cash
            cf_info = cash_flows.get('sellable_positions', {}).get(ticker, {})
            proceeds = cf_info.get('max_proceeds', 0)
            running_cash += proceeds
            action['valid'] = True
            valid.append(action)

        elif action_type == 'BUY':
            if ticker in no_buy:
                action['rejection_reason'] = (
                    f"{ticker} has earnings within 7 days — buy blackout active."
                )
                rejected.append(action)
                continue

            # Check max positions (only for new tickers not already held)
            already_held = ticker in sellable_lots  # held positions are in sellable_lots
            is_new = ticker not in sellable_lots and ticker not in new_positions
            if is_new and (position_count + len(new_positions)) >= max_positions:
                action['rejection_reason'] = (
                    f"Cannot open {ticker}: already at max {max_positions} position(s)."
                )
                rejected.append(action)
                continue

            # Check cash sufficiency
            amount_str = action.get('amount', '')
            if '$' in str(amount_str):
                try:
                    amount = float(re.sub(r'[^\d.]', '', str(amount_str)))
                    if amount > running_cash + 10:  # $10 rounding buffer
                        action['validation_warning'] = (
                            f"Requested ${amount:,.2f} but only ${running_cash:,.2f} available "
                            f"(including any SELL proceeds)."
                        )
                    else:
                        running_cash -= amount
                except ValueError:
                    pass

            if is_new:
                new_positions.add(ticker)
            action['valid'] = True
            valid.append(action)

        else:  # HOLD or WAIT — always valid
            action['valid'] = True
            valid.append(action)

    # Catastrophic floor enforcement — inject SELL for any breach not already covered
    catastrophic_breaches = constraints.get('catastrophic_breaches', [])
    if catastrophic_breaches:
        sell_tickers = {a.get('ticker') for a in valid if a.get('type', '').upper() == 'SELL'}
        for breach in catastrophic_breaches:
            ticker = breach['ticker']
            if ticker not in sell_tickers:
                sellable_qty = constraints.get('sellable_lots', {}).get(ticker, {}).get('sellable_qty', 'all')
                injected = {
                    'type': 'SELL',
                    'ticker': ticker,
                    'amount': f"{sellable_qty} share(s)",
                    'reasoning': (
                        f"System-enforced: catastrophic floor breached at "
                        f"{breach['pnl_pct']}% from ${breach['purchase_price']:.2f}. "
                        f"Unconditional exit — no thesis reasoning overrides this."
                    ),
                    'valid': True,
                    'system_enforced': True,
                }
                valid.insert(0, injected)
                sell_tickers.add(ticker)

    return valid, rejected


# =============================================================================
# Utility Functions
# =============================================================================

def format_recommendation_text(recommendation: dict) -> str:
    """
    Format recommendation for terminal display.

    Args:
        recommendation: Parsed recommendation dictionary

    Returns:
        Formatted text string
    """
    lines = []

    # Check for errors
    if recommendation.get('error'):
        lines.append(f"ERROR: {recommendation['error']}")
        lines.append("")

    # Overall strategy
    strategy = recommendation.get('overall_strategy', '')
    if strategy:
        lines.append("STRATEGY SUMMARY")
        lines.append("-" * 40)
        lines.append(strategy)
        lines.append("")

    # Actions
    actions = recommendation.get('actions', [])
    if actions:
        lines.append("RECOMMENDED ACTIONS")
        lines.append("-" * 40)

        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'UNKNOWN')
            ticker = action.get('ticker', '')
            amount = action.get('amount', '')
            reasoning = action.get('reasoning', '')
            valid = action.get('valid', True)

            # Action header
            status = "[+]" if valid else "[X]"
            lines.append(f"{i}. [{status}] {action_type} {ticker} - {amount}")

            # Validation error/warning
            if action.get('validation_error'):
                lines.append(f"   [!] {action['validation_error']}")
            if action.get('validation_warning'):
                lines.append(f"   [!] {action['validation_warning']}")

            # Reasoning
            if reasoning:
                lines.append(f"   Reasoning: {reasoning}")

            lines.append("")
    else:
        lines.append("No specific actions recommended.")
        lines.append("")

    # Risk warnings
    warnings = recommendation.get('risk_warnings', [])
    if warnings:
        lines.append("RISK WARNINGS")
        lines.append("-" * 40)
        for warning in warnings:
            lines.append(f"[!] {warning}")
        lines.append("")

    # Confidence
    confidence = recommendation.get('confidence', 'UNKNOWN')
    lines.append(f"Confidence Level: {confidence}")

    return "\n".join(lines)
