"""
analyzer.py - Ranking & Technical Analysis

Responsibilities:
- Calculate fundamental ranking scores
- Compute technical indicators (RSI, support/resistance)
- Determine FIFO eligibility (days held vs 30-day minimum)
- Calculate transaction costs for potential actions
- Identify entry/exit signals

Key Functions:
- calculate_rankings(fundamentals: dict) -> dict
- check_fifo_eligibility(positions: list) -> dict
- analyze_entry_signals(ticker: str, data: dict) -> dict
- analyze_exit_signals(position: dict, data: dict, config: dict) -> dict
- generate_market_context(market_data: dict, portfolio: dict, config: dict) -> dict
"""

from datetime import date
from typing import Optional
from .utils import (
    days_held, is_sellable, days_until_sellable, unlock_date,
    calculate_pnl_percent, format_currency, format_percent
)
from .event_detector import detect_material_events


# =============================================================================
# Fundamental Ranking
# =============================================================================

def calculate_fundamental_score(ticker_data: dict) -> float:
    """
    Calculate 0-10 fundamental score for a stock.

    Factors:
    - Revenue growth (30%)
    - Free cash flow strength (25%)
    - P/E valuation (25%)
    - Momentum/trend (20%)

    Args:
        ticker_data: Dictionary with fundamentals and technicals

    Returns:
        Composite score from 0-10
    """
    fundamentals = ticker_data.get('fundamentals', {})
    technicals = ticker_data.get('technicals', {})

    # Revenue growth score (0-10)
    # > 20% = 10, 15-20% = 8, 10-15% = 6, 5-10% = 4, < 5% = 2
    rev_growth = fundamentals.get('revenue_growth_yoy', 0) or 0
    if rev_growth > 0.20:
        revenue_score = 10
    elif rev_growth > 0.15:
        revenue_score = 8
    elif rev_growth > 0.10:
        revenue_score = 6
    elif rev_growth > 0.05:
        revenue_score = 4
    else:
        revenue_score = 2

    # FCF score (0-10)
    # FCF margin > 25% = 10, 20-25% = 8, 15-20% = 6, 10-15% = 4, < 10% = 2
    revenue = fundamentals.get('revenue_ttm', 0) or 1  # Avoid division by zero
    fcf = fundamentals.get('free_cash_flow', 0) or 0
    fcf_margin = fcf / revenue if revenue > 0 else 0

    if fcf_margin > 0.25:
        fcf_score = 10
    elif fcf_margin > 0.20:
        fcf_score = 8
    elif fcf_margin > 0.15:
        fcf_score = 6
    elif fcf_margin > 0.10:
        fcf_score = 4
    else:
        fcf_score = 2

    # P/E valuation score (0-10)
    # Lower P/E relative to tech sector average (35) is better
    # P/E < 20 = 10, 20-25 = 8, 25-30 = 6, 30-40 = 4, > 40 = 2
    pe = fundamentals.get('pe_ratio', 0) or 0
    if pe <= 0:  # No earnings or data
        pe_score = 5  # Neutral
    elif pe < 20:
        pe_score = 10
    elif pe < 25:
        pe_score = 8
    elif pe < 30:
        pe_score = 6
    elif pe < 40:
        pe_score = 4
    else:
        pe_score = 2

    # Momentum score (0-10)
    # Price vs 50-day MA: > 10% = 10, 5-10% = 8, 0-5% = 6, -5-0% = 4, < -5% = 2
    momentum = technicals.get('price_vs_sma50', 0) or 0

    if momentum > 10:
        momentum_score = 10
    elif momentum > 5:
        momentum_score = 8
    elif momentum > 0:
        momentum_score = 6
    elif momentum > -5:
        momentum_score = 4
    else:
        momentum_score = 2

    # Weighted composite score
    composite = (
        0.30 * revenue_score +
        0.25 * fcf_score +
        0.25 * pe_score +
        0.20 * momentum_score
    )

    return round(composite, 1)


def calculate_rankings(market_data: dict) -> dict:
    """
    Rank all stocks 1-N by fundamental score.

    Args:
        market_data: Dictionary with ticker data from data_collector

    Returns:
        Dictionary with rankings for each ticker
    """
    tickers_data = market_data.get('tickers', {})
    scores = {}

    # Calculate score for each ticker
    for ticker, data in tickers_data.items():
        scores[ticker] = {
            'score': calculate_fundamental_score(data),
            'fundamentals': data.get('fundamentals', {}),
            'technicals': data.get('technicals', {}),
        }

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)

    # Assign ranks 1-N
    rankings = {}
    for rank, (ticker, data) in enumerate(ranked, start=1):
        rankings[ticker] = {
            'rank': rank,
            'score': data['score'],
            'fundamentals': data['fundamentals'],
            'technicals': data['technicals'],
            'is_top_3': rank <= 3,
        }

    return rankings


# =============================================================================
# FIFO Eligibility
# =============================================================================

def check_fifo_eligibility(positions: list, min_hold_days: int = 30) -> dict:
    """
    Check FIFO eligibility for all positions.

    Args:
        positions: List of position dictionaries
        min_hold_days: Minimum days to hold (default 30)

    Returns:
        Dictionary with eligibility info for each position
    """
    result = {}

    for pos in positions:
        ticker = pos.get('ticker', 'UNKNOWN')
        purchase_date = pos.get('purchase_date', '')

        held = days_held(purchase_date)
        sellable = is_sellable(purchase_date, min_hold_days)
        days_remaining = days_until_sellable(purchase_date, min_hold_days)
        unlock = unlock_date(purchase_date, min_hold_days)

        result[ticker] = {
            'days_held': held,
            'is_sellable': sellable,
            'days_until_sellable': days_remaining,
            'unlock_date': unlock.isoformat(),
            'status': 'SELLABLE' if sellable else 'LOCKED',
            'purchase_date': purchase_date,
        }

    return result


def get_portfolio_lock_status(positions: list, min_hold_days: int = 30) -> dict:
    """
    Get overall portfolio lock status summary.

    Args:
        positions: List of position dictionaries
        min_hold_days: Minimum days to hold

    Returns:
        Summary of portfolio lock status
    """
    eligibility = check_fifo_eligibility(positions, min_hold_days)

    total = len(positions)
    sellable = sum(1 for e in eligibility.values() if e['is_sellable'])
    locked = total - sellable

    # Find next unlock date
    next_unlock = None
    for ticker, info in eligibility.items():
        if not info['is_sellable']:
            unlock = info['unlock_date']
            if next_unlock is None or unlock < next_unlock:
                next_unlock = unlock

    return {
        'total_positions': total,
        'sellable_count': sellable,
        'locked_count': locked,
        'all_locked': locked == total and total > 0,
        'all_sellable': sellable == total,
        'next_unlock_date': next_unlock,
        'positions': eligibility,
    }


# =============================================================================
# Entry/Exit Signal Analysis
# =============================================================================

def analyze_entry_signals(ticker: str, data: dict, config: dict) -> dict:
    """
    Analyze entry signals for a potential buy.

    Args:
        ticker: Stock ticker symbol
        data: Ticker data from market_data
        config: Configuration dictionary

    Returns:
        Entry signal analysis
    """
    technicals = data.get('technicals', {})
    fundamentals = data.get('fundamentals', {})
    news = data.get('news', {})

    signals = []
    warnings = []

    # RSI Analysis
    rsi = technicals.get('rsi_14', 50)
    if rsi < 30:
        signals.append(f"RSI oversold ({rsi:.1f}) - strong buy signal")
    elif rsi < 50:
        signals.append(f"RSI favorable ({rsi:.1f}) - good entry zone")
    elif rsi > 70:
        warnings.append(f"RSI overbought ({rsi:.1f}) - consider waiting")

    # Support Level Analysis
    current_price = technicals.get('current_price', 0)
    support = technicals.get('support_level', 0)
    resistance = technicals.get('resistance_level', 0)

    if current_price > 0 and support > 0:
        distance_to_support = ((current_price - support) / current_price) * 100
        if distance_to_support < 3:
            signals.append(f"Near support level ({format_currency(support)})")

    # SMA Analysis
    price_vs_sma20 = technicals.get('price_vs_sma20', 0)
    if price_vs_sma20 < -5:
        signals.append(f"Below 20-day SMA by {abs(price_vs_sma20):.1f}%")

    # Earnings Proximity Warning
    earnings_date = fundamentals.get('earnings_date')
    if earnings_date:
        from datetime import datetime
        try:
            earnings = datetime.strptime(earnings_date, '%Y-%m-%d').date()
            days_to_earnings = (earnings - date.today()).days
            if 0 < days_to_earnings <= 7:
                warnings.append(f"Earnings in {days_to_earnings} days - higher uncertainty")
        except ValueError:
            pass

    # News Check (handle both old list format and new enhanced format)
    if news:
        # Determine if news is enhanced dict or old list format
        if isinstance(news, dict):
            # Enhanced format - check themes
            themes = news.get('themes', [])
            negative_themes = ['legal', 'regulatory', 'layoffs', 'data_breach']
            for theme in themes[:3]:
                theme_name = theme.get('name', '')
                if theme_name in negative_themes:
                    headline = theme.get('headline', '')
                    warnings.append(f"Negative news ({theme_name}): {headline[:60]}...")
                    break
        else:
            # Old format - check article titles
            negative_keywords = ['lawsuit', 'investigation', 'layoff', 'miss', 'decline', 'fall', 'drop', 'crash']
            for article in news[:5]:
                title = article.get('title', '').lower()
                if any(kw in title for kw in negative_keywords):
                    warnings.append(f"Negative news: {article.get('title', '')[:60]}...")
                    break

    # Overall assessment
    signal_strength = len(signals) - len(warnings)
    if signal_strength >= 2:
        recommendation = 'FAVORABLE'
    elif signal_strength >= 0:
        recommendation = 'NEUTRAL'
    else:
        recommendation = 'CAUTION'

    return {
        'ticker': ticker,
        'recommendation': recommendation,
        'signals': signals,
        'warnings': warnings,
        'rsi': rsi,
        'current_price': current_price,
        'support': support,
        'resistance': resistance,
    }


def analyze_exit_signals(position: dict, data: dict, config: dict) -> dict:
    """
    Analyze exit signals for a held position.

    Args:
        position: Position dictionary
        data: Ticker data from market_data
        config: Configuration dictionary

    Returns:
        Exit signal analysis
    """
    ticker = position.get('ticker', '')
    purchase_price = position.get('purchase_price', 0)
    purchase_date = position.get('purchase_date', '')

    price_data = data.get('price', {})
    current_price = price_data.get('current_price', 0)

    # Calculate P&L
    pnl_percent = calculate_pnl_percent(purchase_price, current_price)

    # Get config thresholds
    stop_loss = config.get('stop_loss_percent', -10)
    profit_target = config.get('profit_target_percent', 20)
    min_hold = config.get('min_hold_days', 30)

    signals = []
    warnings = []

    # Check FIFO eligibility first
    held = days_held(purchase_date)
    sellable = is_sellable(purchase_date, min_hold)

    if not sellable:
        days_left = days_until_sellable(purchase_date, min_hold)
        warnings.append(f"LOCKED: Cannot sell for {days_left} more days (FIFO rule)")

    # Stop Loss Check
    if pnl_percent <= stop_loss:
        if sellable:
            signals.append(f"STOP LOSS triggered: {format_percent(pnl_percent)} (threshold: {stop_loss}%)")
        else:
            warnings.append(f"Stop loss would trigger ({format_percent(pnl_percent)}) but position is LOCKED")

    # Profit Target Check
    if pnl_percent >= profit_target:
        if sellable:
            signals.append(f"PROFIT TARGET reached: {format_percent(pnl_percent)} (threshold: +{profit_target}%)")
        else:
            warnings.append(f"Profit target reached ({format_percent(pnl_percent)}) but position is LOCKED")

    # Overall assessment
    if not sellable:
        recommendation = 'HOLD (LOCKED)'
    elif signals:
        recommendation = 'CONSIDER EXIT'
    else:
        recommendation = 'HOLD'

    return {
        'ticker': ticker,
        'recommendation': recommendation,
        'signals': signals,
        'warnings': warnings,
        'pnl_percent': pnl_percent,
        'current_price': current_price,
        'purchase_price': purchase_price,
        'days_held': held,
        'is_sellable': sellable,
    }


# =============================================================================
# Market Context Generation
# =============================================================================

def generate_market_context(market_data: dict, portfolio: dict, config: dict) -> dict:
    """
    Generate comprehensive market context for AI recommendation.

    Args:
        market_data: Full market data from data_collector
        portfolio: Portfolio dictionary
        config: Configuration dictionary

    Returns:
        Structured context for AI prompt
    """
    # Calculate rankings
    rankings = calculate_rankings(market_data)

    # Get top 3 stocks
    top_3 = [t for t, r in rankings.items() if r['is_top_3']]

    # Analyze current positions
    positions = portfolio.get('positions', [])
    position_analysis = []

    for pos in positions:
        ticker = pos.get('ticker', '')
        ticker_data = market_data.get('tickers', {}).get(ticker, {})

        # Get ranking info
        rank_info = rankings.get(ticker, {'rank': 'N/A', 'score': 0})

        # Get exit signals
        exit_analysis = analyze_exit_signals(pos, ticker_data, config)

        # Get price context
        price_ctx = ticker_data.get('price_context', {})

        position_analysis.append({
            'ticker': ticker,
            'quantity': pos.get('quantity', 0),
            'purchase_price': pos.get('purchase_price', 0),
            'purchase_date': pos.get('purchase_date', ''),
            'current_price': ticker_data.get('price', {}).get('current_price', 0),
            'rank': rank_info.get('rank', 'N/A'),
            'score': rank_info.get('score', 0),
            'pnl_percent': exit_analysis.get('pnl_percent', 0),
            'days_held': exit_analysis.get('days_held', 0),
            'is_sellable': exit_analysis.get('is_sellable', False),
            'exit_signals': exit_analysis.get('signals', []),
            'exit_warnings': exit_analysis.get('warnings', []),
            'return_30d': price_ctx.get('return_30d', 0),
            'relative_performance': price_ctx.get('relative_performance', 0),
            'trend': price_ctx.get('trend', 'UNKNOWN'),
            'earnings': ticker_data.get('earnings'),  # Earnings proximity data
        })

    # Analyze entry opportunities for top 3 not in portfolio
    held_tickers = [p.get('ticker') for p in positions]
    entry_opportunities = []

    for ticker in top_3:
        if ticker not in held_tickers:
            ticker_data = market_data.get('tickers', {}).get(ticker, {})
            entry_analysis = analyze_entry_signals(ticker, ticker_data, config)
            rank_info = rankings.get(ticker, {})
            price_ctx = ticker_data.get('price_context', {})

            entry_opportunities.append({
                'ticker': ticker,
                'rank': rank_info.get('rank', 0),
                'score': rank_info.get('score', 0),
                'current_price': ticker_data.get('price', {}).get('current_price', 0),
                'entry_recommendation': entry_analysis.get('recommendation', ''),
                'entry_signals': entry_analysis.get('signals', []),
                'entry_warnings': entry_analysis.get('warnings', []),
                'rsi': entry_analysis.get('rsi', 50),
                'return_30d': price_ctx.get('return_30d', 0),
                'relative_performance': price_ctx.get('relative_performance', 0),
                'trend': price_ctx.get('trend', 'UNKNOWN'),
                'earnings': ticker_data.get('earnings'),  # Earnings proximity data
            })

    # Portfolio lock status
    lock_status = get_portfolio_lock_status(positions, config.get('min_hold_days', 30))

    # Compile news highlights (enhanced with themes)
    news_highlights = []
    for ticker in held_tickers + top_3[:3]:
        ticker_news = market_data.get('tickers', {}).get(ticker, {}).get('news', {})
        themes = ticker_news.get('themes', [])
        # Add top 3 material themes per ticker
        for theme in themes[:3]:
            news_highlights.append({
                'ticker': ticker,
                'theme_name': theme.get('name', 'unknown'),
                'headline': theme.get('headline', ''),
                'date': theme.get('date', ''),
                'source': theme.get('source', 'Unknown'),
                'article_count': theme.get('article_count', 1),
                'frequency': theme.get('frequency', 'LOW'),
            })

    # Get benchmark data for context
    benchmark = market_data.get('benchmark', {})

    # Detect material events for holdings
    material_events = detect_material_events(market_data, portfolio)

    return {
        'timestamp': market_data.get('timestamp', ''),
        'benchmark': benchmark,
        'rankings': rankings,
        'top_3_tickers': top_3,
        'current_positions': position_analysis,
        'entry_opportunities': entry_opportunities,
        'portfolio_lock_status': lock_status,
        'cash_available': portfolio.get('cash_available', 0),
        'news_highlights': news_highlights[:10],  # Limit to 10
        'material_events': material_events,
        'config': {
            'max_positions': config.get('max_positions', 3),
            'transaction_fee': config.get('transaction_fee', 10),
            'monthly_budget': config.get('monthly_budget', 400),
            'min_hold_days': config.get('min_hold_days', 30),
            'stop_loss_percent': config.get('stop_loss_percent', -10),
            'profit_target_percent': config.get('profit_target_percent', 20),
        },
    }


def format_rankings_table(rankings: dict) -> str:
    """Format rankings as a text table for display."""
    lines = []
    lines.append("STOCK RANKINGS")
    lines.append("-" * 60)
    lines.append(f"{'Rank':<6}{'Ticker':<8}{'Score':<8}{'P/E':<10}{'Rev Growth':<12}{'RSI':<8}")
    lines.append("-" * 60)

    # Sort by rank
    sorted_rankings = sorted(rankings.items(), key=lambda x: x[1]['rank'])

    for ticker, data in sorted_rankings:
        rank = data['rank']
        score = data['score']
        pe = data['fundamentals'].get('pe_ratio', 0)
        rev_growth = data['fundamentals'].get('revenue_growth_yoy', 0) * 100
        rsi = data['technicals'].get('rsi_14', 0)

        lines.append(
            f"{rank:<6}{ticker:<8}{score:<8.1f}{pe:<10.1f}{rev_growth:<12.1f}%{rsi:<8.1f}"
        )

    return "\n".join(lines)
