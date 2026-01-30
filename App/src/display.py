"""
display.py - Terminal Output Formatting

Responsibilities:
- Format recommendations for terminal display
- Generate ASCII tables
- Apply color coding
- Create summary sections

Key Functions:
- display_portfolio_status(portfolio: dict, context: dict)
- display_market_snapshot(context: dict)
- display_recommendations(recommendation: dict)
- display_risk_warnings(warnings: list)
- print_header(title: str)
"""

from datetime import date
from typing import Optional


# =============================================================================
# ANSI Color Codes
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


def colorize(text: str, color: str) -> str:
    """Apply color to text."""
    return f"{color}{text}{Colors.RESET}"


def color_value(value: float, neutral_threshold: float = 0) -> str:
    """Color a numeric value based on positive/negative."""
    if value > neutral_threshold:
        return colorize(f"+{value:.2f}%", Colors.GREEN)
    elif value < -neutral_threshold:
        return colorize(f"{value:.2f}%", Colors.RED)
    else:
        return f"{value:.2f}%"


def color_status(status: str) -> str:
    """Color status text."""
    status_upper = status.upper()
    if status_upper in ('SELLABLE', 'HIGH', 'FAVORABLE', 'BUY'):
        return colorize(status, Colors.GREEN)
    elif status_upper in ('LOCKED', 'LOW', 'CAUTION', 'SELL'):
        return colorize(status, Colors.RED)
    elif status_upper in ('MEDIUM', 'NEUTRAL', 'HOLD'):
        return colorize(status, Colors.YELLOW)
    return status


# =============================================================================
# Header and Section Formatting
# =============================================================================

def print_header(title: str, width: int = 60) -> None:
    """Print a section header."""
    print()
    print(colorize("=" * width, Colors.CYAN))
    print(colorize(f" {title}", Colors.BOLD + Colors.CYAN))
    print(colorize("=" * width, Colors.CYAN))


def print_subheader(title: str, width: int = 60) -> None:
    """Print a subsection header."""
    print()
    print(colorize(f"--- {title} ---", Colors.BOLD))


def print_divider(width: int = 60) -> None:
    """Print a horizontal divider."""
    print(colorize("-" * width, Colors.DIM))


# =============================================================================
# Portfolio Display
# =============================================================================

def display_portfolio_status(portfolio: dict, context: dict) -> None:
    """
    Display current portfolio status (consolidated lot-based view).

    Shows one row per stock with lot breakdown underneath.

    Args:
        portfolio: Portfolio dictionary
        context: Market context from analyzer
    """
    print_header("PORTFOLIO STATUS")

    positions = context.get('current_positions', [])
    cash = portfolio.get('cash_available', 0)
    lock_status = context.get('portfolio_lock_status', {})

    if not positions:
        print("\n  No positions currently held.")
        print(f"\n  Cash Available: {colorize(f'${cash:,.2f}', Colors.GREEN)}")
        return

    # Calculate totals
    total_value = cash
    total_cost = 0

    # Print position table header
    print()
    header = f"{'Ticker':<8}{'Qty':>6}{'Avg Cost':>10}{'Current':>10}{'P&L':>10}{'Rank':>6}{'Status':>14}"
    print(colorize(header, Colors.BOLD))
    print_divider()

    for pos in positions:
        ticker = pos.get('ticker', '')
        total_qty = pos.get('total_quantity', 0)
        avg_cost = pos.get('average_cost', 0)
        current = pos.get('current_price', 0)
        pnl_pct = pos.get('pnl_percent', 0)
        rank = pos.get('rank', 'N/A')
        pos_lock_status = pos.get('lock_status', 'LOCKED')
        lots = pos.get('lots', [])

        # Calculate value
        position_value = total_qty * current
        position_cost = total_qty * avg_cost
        total_value += position_value
        total_cost += position_cost

        # Format P&L with color
        pnl_str = color_value(pnl_pct)

        # Format status with color
        status_str = color_status(pos_lock_status)

        print(f"{ticker:<8}{total_qty:>6}{avg_cost:>10.2f}{current:>10.2f}{pnl_str:>18}{'#'+str(rank):>6}{status_str:>22}")

        # Show lot breakdown (if multiple lots)
        if len(lots) > 1:
            for i, lot in enumerate(lots):
                lot_qty = lot.get('quantity', 0)
                lot_price = lot.get('purchase_price', 0)
                lot_days = lot.get('days_held', 0)
                lot_pnl = lot.get('pnl_percent', 0)
                lot_sellable = lot.get('is_sellable', False)
                is_last = (i == len(lots) - 1)
                prefix = "  └─" if is_last else "  ├─"

                lot_status = colorize("SELLABLE", Colors.GREEN) if lot_sellable else colorize("LOCKED", Colors.RED)
                lot_pnl_str = color_value(lot_pnl)

                print(colorize(
                    f"{prefix} Lot {i+1}: {lot_qty} @ {lot_price:.2f} ({lot_days}d, ",
                    Colors.DIM
                ) + f"{lot_pnl_str}" + colorize(")", Colors.DIM) + f"  {lot_status}")

        # Show exit signals if any
        for signal in pos.get('exit_signals', []):
            print(colorize(f"         [!]  {signal}", Colors.YELLOW))

    print_divider()

    # Portfolio summary
    total_pnl = total_value - total_cost - cash
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    print(f"\n  {'Portfolio Value:':<20} {colorize(f'${total_value:,.2f}', Colors.BOLD)}")
    print(f"  {'Cash Available:':<20} ${cash:,.2f}")
    print(f"  {'Total P&L:':<20} {color_value(total_pnl_pct)} ({'+' if total_pnl >= 0 else ''}${total_pnl:,.2f})")

    # Lock status summary (lot-aware)
    sellable_count = lock_status.get('sellable_count', 0)
    partially_count = lock_status.get('partially_sellable_count', 0)
    locked_count = lock_status.get('locked_count', 0)
    next_unlock = lock_status.get('next_unlock_date', '')

    status_parts = []
    if sellable_count > 0:
        status_parts.append(f"{sellable_count} sellable")
    if partially_count > 0:
        status_parts.append(f"{partially_count} partially sellable")
    if locked_count > 0:
        status_parts.append(f"{locked_count} locked")

    print(f"\n  {'Stocks:':<20} {len(positions)} ({', '.join(status_parts)})")

    # Show partially sellable detail
    for pos in positions:
        if pos.get('lock_status') == 'PARTIAL_LOCK':
            sellable_qty = pos.get('sellable_quantity', 0)
            total_qty = pos.get('total_quantity', 0)
            print(colorize(
                f"  {'':>20} {pos['ticker']}: {sellable_qty} of {total_qty} shares sellable",
                Colors.YELLOW
            ))

    if next_unlock:
        print(f"  {'Next Unlock:':<20} {next_unlock}")


# =============================================================================
# Market Snapshot Display
# =============================================================================

def display_market_snapshot(context: dict) -> None:
    """
    Display market snapshot with rankings.

    Args:
        context: Market context from analyzer
    """
    print_header("MARKET SNAPSHOT")

    rankings = context.get('rankings', {})
    top_3 = context.get('top_3_tickers', [])
    held_tickers = [p.get('ticker', '') for p in context.get('current_positions', [])]

    if not rankings:
        print("\n  No market data available.")
        return

    # Print rankings table
    print()
    header = f"{'Rank':<6}{'Ticker':<8}{'Score':>8}{'P/E':>10}{'RevGrwth':>10}{'RSI':>8}{'Status':>12}"
    print(colorize(header, Colors.BOLD))
    print_divider()

    sorted_rankings = sorted(rankings.items(), key=lambda x: x[1].get('rank', 99))

    for ticker, data in sorted_rankings[:10]:
        rank = data.get('rank', 0)
        score = data.get('score', 0)
        fundamentals = data.get('fundamentals', {})
        technicals = data.get('technicals', {})

        pe = fundamentals.get('pe_ratio', 0)
        rev_growth = (fundamentals.get('revenue_growth_yoy', 0) or 0) * 100
        rsi = technicals.get('rsi_14', 0)

        # Status
        if ticker in held_tickers:
            status = colorize("HELD", Colors.CYAN)
        elif ticker in top_3:
            status = colorize("TOP 3", Colors.GREEN)
        else:
            status = ""

        # Highlight top 3
        if rank <= 3:
            rank_str = colorize(f"#{rank}", Colors.GREEN + Colors.BOLD)
        else:
            rank_str = f"#{rank}"

        print(f"{rank_str:<14}{ticker:<8}{score:>8.1f}{pe:>10.1f}{rev_growth:>9.1f}%{rsi:>8.1f}{status:>20}")

    # Entry opportunities
    opportunities = context.get('entry_opportunities', [])
    if opportunities:
        print_subheader("Entry Opportunities")
        for opp in opportunities:
            ticker = opp.get('ticker', '')
            rank = opp.get('rank', 0)
            price = opp.get('current_price', 0)
            rec = opp.get('entry_recommendation', '')
            rsi = opp.get('rsi', 50)

            rec_color = color_status(rec)
            print(f"  {ticker} (Rank #{rank}): ${price:.2f}, RSI={rsi:.1f}, Entry: {rec_color}")

            for signal in opp.get('entry_signals', []):
                print(colorize(f"    [+] {signal}", Colors.GREEN))
            for warning in opp.get('entry_warnings', []):
                print(colorize(f"    [!] {warning}", Colors.YELLOW))


# =============================================================================
# News Display
# =============================================================================

def display_news(context: dict, max_items: int = 8) -> None:
    """
    Display recent news highlights.

    Args:
        context: Market context from analyzer
        max_items: Maximum news items to show
    """
    print_header("RECENT NEWS")

    news = context.get('news_highlights', [])

    if not news:
        print("\n  No recent news available.")
        return

    print()
    seen = set()
    count = 0

    for item in news:
        if count >= max_items:
            break

        # Enhanced news structure with themes
        headline = item.get('headline', '')
        theme_name = item.get('theme_name', 'unknown').replace('_', ' ').title()

        if not headline or headline in seen:
            continue

        ticker = item.get('ticker', '')
        date_str = item.get('date', '')
        frequency = item.get('frequency', '')
        article_count = item.get('article_count', 1)

        # Format theme badge
        freq_badge = f"{frequency}" if frequency else ""
        theme_badge = f"{theme_name} ({freq_badge} - {article_count} articles)" if freq_badge else theme_name

        # Truncate long headlines
        if len(headline) > 60:
            headline = headline[:57] + "..."

        print(f"  [{colorize(ticker, Colors.CYAN)}] [{colorize(theme_badge, Colors.YELLOW)}]")
        print(f"    {headline}")
        if date_str:
            print(colorize(f"       {date_str}", Colors.DIM))

        seen.add(headline)
        count += 1


# =============================================================================
# Price Context Display
# =============================================================================

def display_price_context(context: dict) -> None:
    """
    Display 30-day price context vs market benchmark.

    Args:
        context: Market context from analyzer
    """
    print_header("PRICE CONTEXT (30-Day vs SPY)")

    benchmark = context.get('benchmark', {})
    benchmark_return = benchmark.get('return_30d', 0)

    print()
    print(f"  Market Benchmark (SPY): {color_value(benchmark_return)}")
    print_divider()

    positions = context.get('current_positions', [])
    opportunities = context.get('entry_opportunities', [])

    # Holdings price context
    if positions:
        print()
        print(colorize("  Current Holdings:", Colors.BOLD))
        for pos in positions:
            ticker = pos.get('ticker', '')
            return_30d = pos.get('return_30d', 0)
            rel_perf = pos.get('relative_performance', 0)
            trend = pos.get('trend', 'UNKNOWN')

            # Color the trend
            trend_colors = {
                'OUTPERFORMING': Colors.GREEN,
                'UNDERPERFORMING': Colors.RED,
                'NEUTRAL': Colors.YELLOW,
                'UNKNOWN': Colors.DIM
            }
            trend_str = colorize(trend, trend_colors.get(trend, Colors.DIM))

            print(f"    {ticker:<8} {color_value(return_30d):>14} vs SPY {rel_perf:+.2f}%  [{trend_str}]")

    # Entry opportunities price context
    if opportunities:
        print()
        print(colorize("  Entry Opportunities:", Colors.BOLD))
        for opp in opportunities:
            ticker = opp.get('ticker', '')
            return_30d = opp.get('return_30d', 0)
            rel_perf = opp.get('relative_performance', 0)
            trend = opp.get('trend', 'UNKNOWN')

            trend_colors = {
                'OUTPERFORMING': Colors.GREEN,
                'UNDERPERFORMING': Colors.RED,
                'NEUTRAL': Colors.YELLOW,
                'UNKNOWN': Colors.DIM
            }
            trend_str = colorize(trend, trend_colors.get(trend, Colors.DIM))

            print(f"    {ticker:<8} {color_value(return_30d):>14} vs SPY {rel_perf:+.2f}%  [{trend_str}]")


# =============================================================================
# Earnings Calendar Display
# =============================================================================

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
    has_upcoming = False

    # Check positions for imminent earnings (future only, not recently reported)
    print()
    for pos in positions:
        earnings = pos.get('earnings')
        if earnings and 0 < earnings['days_until'] <= 7:
            if not has_imminent:
                print(colorize("  IMMINENT EARNINGS (Trading Restricted):", Colors.YELLOW + Colors.BOLD))
                has_imminent = True

            ticker = pos.get('ticker', '')
            days = earnings['days_until']
            date_str = earnings['date']

            # Build restriction badges
            restrictions = []
            if earnings.get('sell_restricted'):
                restrictions.append(colorize("NO SELL", Colors.RED))
            if earnings.get('buy_restricted'):
                restrictions.append(colorize("NO BUY", Colors.YELLOW))

            restriction_str = " | ".join(restrictions) if restrictions else ""
            print(f"    {ticker}: {date_str} ({days} days) [{restriction_str}]")

    # Check opportunities for imminent earnings (future only)
    for opp in opportunities:
        earnings = opp.get('earnings')
        if earnings and 0 < earnings['days_until'] <= 7:
            if not has_imminent:
                print(colorize("  IMMINENT EARNINGS (Trading Restricted):", Colors.YELLOW + Colors.BOLD))
                has_imminent = True

            ticker = opp.get('ticker', '')
            days = earnings['days_until']
            date_str = earnings['date']

            print(f"    {ticker}: {date_str} ({days} days) [{colorize('NO BUY', Colors.YELLOW)}]")

    # Check for upcoming earnings (8-30 days)
    upcoming_tickers = []
    for pos in positions:
        earnings = pos.get('earnings')
        if earnings and 7 < earnings['days_until'] <= 30:
            upcoming_tickers.append(f"{pos.get('ticker', '')} ({earnings['days_until']}d)")

    for opp in opportunities:
        earnings = opp.get('earnings')
        if earnings and 7 < earnings['days_until'] <= 30:
            upcoming_tickers.append(f"{opp.get('ticker', '')} ({earnings['days_until']}d)")

    if upcoming_tickers:
        if has_imminent:
            print()
        print(colorize("  Upcoming Earnings (Safe to Trade):", Colors.BOLD))
        print(f"    {', '.join(upcoming_tickers)}")
        has_upcoming = True

    if not has_imminent and not has_upcoming:
        print(colorize("  No near-term earnings - all tickers safe for trading", Colors.GREEN))


# =============================================================================
# Recommendations Display
# =============================================================================

def display_recommendations(recommendation: dict) -> None:
    """
    Display AI recommendations.

    Args:
        recommendation: Parsed recommendation from AI agent
    """
    print_header("AI RECOMMENDATIONS")

    # Check for errors
    if recommendation.get('error'):
        print()
        print(colorize(f"  ERROR: {recommendation['error']}", Colors.RED))
        print()
        return

    # Overall strategy
    strategy = recommendation.get('overall_strategy', '')
    if strategy:
        print_subheader("Strategy Summary")
        # Word wrap long strategy text
        words = strategy.split()
        line = "  "
        for word in words:
            if len(line) + len(word) > 70:
                print(line)
                line = "  "
            line += word + " "
        if line.strip():
            print(line)

    # Actions
    actions = recommendation.get('actions', [])
    if actions:
        print_subheader("Recommended Actions")

        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'UNKNOWN').upper()
            ticker = action.get('ticker', '')
            amount = action.get('amount', '')
            reasoning = action.get('reasoning', '')
            valid = action.get('valid', True)

            # Action header with color
            if action_type == 'BUY':
                type_str = colorize("BUY", Colors.GREEN + Colors.BOLD)
            elif action_type == 'SELL':
                type_str = colorize("SELL", Colors.RED + Colors.BOLD)
            else:
                type_str = colorize("HOLD", Colors.YELLOW + Colors.BOLD)

            status_icon = colorize("[+]", Colors.GREEN) if valid else colorize("[X]", Colors.RED)

            print(f"\n  {i}. [{status_icon}] {type_str} {colorize(ticker, Colors.BOLD)} - {amount}")

            # Validation error/warning
            if action.get('validation_error'):
                print(colorize(f"     [!]  {action['validation_error']}", Colors.RED))
            if action.get('validation_warning'):
                print(colorize(f"     [!]  {action['validation_warning']}", Colors.YELLOW))

            # Reasoning (word-wrapped)
            if reasoning:
                print(colorize("     Reasoning:", Colors.DIM))
                words = reasoning.split()
                line = "     "
                for word in words:
                    if len(line) + len(word) > 70:
                        print(line)
                        line = "     "
                    line += word + " "
                if line.strip():
                    print(line)
    else:
        print("\n  No specific actions recommended at this time.")

    # Risk warnings
    display_risk_warnings(recommendation.get('risk_warnings', []))

    # Confidence
    confidence = recommendation.get('confidence', 'UNKNOWN')
    print_subheader("Confidence Level")
    conf_color = Colors.GREEN if confidence == 'HIGH' else Colors.YELLOW if confidence == 'MEDIUM' else Colors.RED
    print(f"  {colorize(confidence, conf_color + Colors.BOLD)}")


def display_risk_warnings(warnings: list) -> None:
    """
    Display risk warnings.

    Args:
        warnings: List of warning strings
    """
    if not warnings:
        return

    print_subheader("Risk Warnings")
    for warning in warnings:
        print(colorize(f"  [!]  {warning}", Colors.YELLOW))


# =============================================================================
# Quick Check Display
# =============================================================================

def display_quick_check(portfolio: dict, context: dict) -> None:
    """
    Display quick portfolio check (for 'advisor check' command).

    Args:
        portfolio: Portfolio dictionary
        context: Market context from analyzer
    """
    print_header("QUICK PORTFOLIO CHECK")
    print(f"  {colorize(f'As of: {date.today().isoformat()}', Colors.DIM)}")

    positions = context.get('current_positions', [])
    lock_status = context.get('portfolio_lock_status', {})

    if not positions:
        print("\n  No positions currently held.")
        return

    # Quick summary
    total_pnl = sum(p.get('pnl_percent', 0) for p in positions) / len(positions) if positions else 0
    sellable = lock_status.get('sellable_count', 0)
    partially = lock_status.get('partially_sellable_count', 0)
    locked = lock_status.get('locked_count', 0)

    status_parts = []
    if sellable > 0:
        status_parts.append(f"{sellable} sellable")
    if partially > 0:
        status_parts.append(f"{partially} partial")
    if locked > 0:
        status_parts.append(f"{locked} locked")

    print(f"\n  Stocks: {len(positions)} ({', '.join(status_parts)})")
    print(f"  Avg P&L: {color_value(total_pnl)}")
    print(f"  Cash: ${portfolio.get('cash_available', 0):,.2f}")

    # Position quick view with trend
    print_subheader("Positions")
    for pos in positions:
        ticker = pos.get('ticker', '')
        pnl = pos.get('pnl_percent', 0)
        days = pos.get('days_held', 0)
        rank = pos.get('rank', 'N/A')
        pos_lock = pos.get('lock_status', 'LOCKED')
        sellable_tag = "[OK]" if pos_lock == 'SELLABLE' else "[PART]" if pos_lock == 'PARTIAL_LOCK' else "[LOCK]"
        trend = pos.get('trend', 'UNKNOWN')

        pnl_str = color_value(pnl)

        # Trend indicator
        trend_icons = {
            'OUTPERFORMING': colorize('+', Colors.GREEN),
            'UNDERPERFORMING': colorize('-', Colors.RED),
            'NEUTRAL': colorize('=', Colors.YELLOW),
            'UNKNOWN': ' '
        }
        trend_icon = trend_icons.get(trend, ' ')

        print(f"  {sellable_tag} {ticker}: {pnl_str} (Day {days}, Rank #{rank}) [{trend_icon}]")

        # Show critical signals only
        for signal in pos.get('exit_signals', []):
            if 'STOP LOSS' in signal or 'PROFIT TARGET' in signal:
                print(colorize(f"     [!]  {signal}", Colors.YELLOW))

    # Overall assessment
    print_subheader("Assessment")
    has_signals = any(pos.get('exit_signals') for pos in positions)
    if has_signals:
        print(colorize("  [!]  Action may be needed - run full analysis", Colors.YELLOW))
    else:
        print(colorize("  [+]  All positions stable - continue holding", Colors.GREEN))


# =============================================================================
# Material Events Display
# =============================================================================

def display_material_events(context: dict, recommendation: dict) -> None:
    """
    Display material events section when events are detected for holdings.

    Shown FIRST in the output, before standard dashboard sections.
    Only displays when material events are detected.

    Args:
        context: Market context from analyzer (contains material_events)
        recommendation: AI recommendation (contains event-specific reasoning)
    """
    events = context.get('material_events', [])
    if not events:
        return

    # Alert banner
    event_count = len(events)
    print()
    print(colorize("=" * 60, Colors.RED + Colors.BOLD))
    print(colorize(
        f"  MATERIAL EVENT{'S' if event_count > 1 else ''} DETECTED"
        f" - Analysis Required",
        Colors.RED + Colors.BOLD
    ))
    print(colorize("=" * 60, Colors.RED + Colors.BOLD))

    # Build position lookup from context
    position_lookup = {}
    for pos in context.get('current_positions', []):
        position_lookup[pos.get('ticker', '')] = pos

    for event in events:
        ticker = event.get('ticker', '')
        event_type = event.get('event_type', 'unknown').upper()
        priority = event.get('priority', 'MEDIUM')
        headline = event.get('headline', '')

        # Event header
        print()
        priority_color = Colors.RED if priority == 'HIGH' else Colors.YELLOW
        print(colorize(f"  [{priority}] {ticker}: {event_type}", priority_color + Colors.BOLD))
        print(colorize("-" * 58, Colors.DIM))

        # Event details
        print(f"  {headline}")
        article_count = event.get('article_count', 0)
        frequency = event.get('frequency', '')
        if article_count > 1 and frequency:
            print(colorize(
                f"  Coverage: {article_count} articles ({frequency} frequency)",
                Colors.DIM
            ))

        # Position context (consolidated)
        pos = position_lookup.get(ticker, {})
        if pos:
            pnl = pos.get('pnl_percent', 0)
            days = pos.get('days_held', 0)
            avg_cost = pos.get('average_cost', 0)
            current = pos.get('current_price', 0)
            total_qty = pos.get('total_quantity', 0)
            pos_lock = pos.get('lock_status', 'LOCKED')
            sellable_qty = pos.get('sellable_quantity', 0)

            pnl_color = Colors.GREEN if pnl >= 0 else Colors.RED
            status = color_status(pos_lock)

            print()
            print(colorize("  YOUR POSITION:", Colors.BOLD))
            print(f"    {total_qty} shares total @ ${avg_cost:.2f} avg cost -> ${current:.2f} now")
            print(f"    P&L: {colorize(f'{pnl:+.1f}%', pnl_color)}  |  Days held: {days}  |  {status}")
            if pos_lock == 'PARTIAL_LOCK':
                print(f"    Sellable: {sellable_qty} of {total_qty} shares (FIFO)")

        # Show AI recommendation for this ticker
        actions = recommendation.get('actions', [])
        for action in actions:
            if action.get('ticker', '').upper() == ticker.upper():
                action_type = action.get('type', 'HOLD').upper()
                reasoning = action.get('reasoning', '')

                print()
                if action_type == 'SELL':
                    action_str = colorize(f"RECOMMENDATION: {action_type}", Colors.RED + Colors.BOLD)
                elif action_type == 'BUY':
                    action_str = colorize(f"RECOMMENDATION: {action_type}", Colors.GREEN + Colors.BOLD)
                else:
                    action_str = colorize(f"RECOMMENDATION: {action_type}", Colors.YELLOW + Colors.BOLD)

                print(f"  {action_str}")

                # Word-wrap reasoning
                if reasoning:
                    words = reasoning.split()
                    line = "    "
                    for word in words:
                        if len(line) + len(word) > 70:
                            print(line)
                            line = "    "
                        line += word + " "
                    if line.strip():
                        print(line)
                break

    print()
    print(colorize("=" * 60, Colors.RED + Colors.BOLD))
    print()


# =============================================================================
# Full Dashboard Display
# =============================================================================

def display_full_dashboard(portfolio: dict, context: dict, recommendation: dict) -> None:
    """
    Display the complete advisor dashboard.

    Args:
        portfolio: Portfolio dictionary
        context: Market context from analyzer
        recommendation: AI recommendation
    """
    # Title banner
    print()
    print(colorize("╔" + "═" * 58 + "╗", Colors.CYAN))
    print(colorize("║" + " PORTFOLIO AI ADVISOR ".center(58) + "║", Colors.CYAN + Colors.BOLD))
    print(colorize("║" + f" {date.today().isoformat()} ".center(58) + "║", Colors.CYAN))
    print(colorize("╚" + "═" * 58 + "╝", Colors.CYAN))

    # Display material events FIRST (if any detected)
    display_material_events(context, recommendation)

    # Display standard sections
    display_portfolio_status(portfolio, context)
    display_market_snapshot(context)
    display_news(context)
    display_price_context(context)
    display_earnings_calendar(context)
    display_recommendations(recommendation)

    # Footer
    print()
    print_divider()
    print(colorize("  Remember: Review all recommendations before executing trades.", Colors.DIM))
    print(colorize("  Run 'python advisor.py confirm' after executing trades.", Colors.DIM))
    print()
