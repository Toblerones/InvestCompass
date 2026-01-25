"""
data_collector.py - Market Data Fetching

Responsibilities:
- Fetch stock prices via yfinance
- Retrieve fundamental metrics
- Scan news via Google RSS
- Load portfolio state from JSON
- Load configuration

Key Functions:
- fetch_market_data(tickers: list) -> dict
- get_fundamentals(tickers: list) -> dict
- scan_news(tickers: list, days: int = 7) -> dict
"""

import yfinance as yf
import feedparser
from datetime import datetime, date, timedelta
from typing import Optional
from urllib.parse import quote_plus
import time
import functools


# =============================================================================
# Retry Decorator
# =============================================================================

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"  [!] {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        print(f"      Retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"  [X] {func.__name__} failed after {max_retries + 1} attempts")

            raise last_exception
        return wrapper
    return decorator


# =============================================================================
# Price Data Fetching
# =============================================================================

@retry_on_failure(max_retries=2, delay=1.0)
def _fetch_single_ticker_data(ticker: str) -> dict:
    """Fetch market data for a single ticker with retry support."""
    stock = yf.Ticker(ticker)
    info = stock.info

    # Validate we got real data
    price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
    if price == 0:
        raise ValueError(f"No price data available for {ticker}")

    return {
        'current_price': price,
        'previous_close': info.get('previousClose', 0),
        'open': info.get('open') or info.get('regularMarketOpen', 0),
        'day_high': info.get('dayHigh') or info.get('regularMarketDayHigh', 0),
        'day_low': info.get('dayLow') or info.get('regularMarketDayLow', 0),
        'volume': info.get('volume') or info.get('regularMarketVolume', 0),
        '52_week_high': info.get('fiftyTwoWeekHigh', 0),
        '52_week_low': info.get('fiftyTwoWeekLow', 0),
        'market_cap': info.get('marketCap', 0),
        'currency': info.get('currency', 'USD'),
        'exchange': info.get('exchange', ''),
    }


def fetch_market_data(tickers: list[str]) -> dict:
    """
    Fetch current market data for a list of tickers.

    Args:
        tickers: List of stock ticker symbols

    Returns:
        Dictionary with ticker as key and price data as value
    """
    result = {}
    failed_tickers = []

    for ticker in tickers:
        try:
            result[ticker] = _fetch_single_ticker_data(ticker)
        except Exception as e:
            print(f"Warning: Failed to fetch data for {ticker}: {e}")
            result[ticker] = {
                'current_price': 0,
                'error': str(e)
            }
            failed_tickers.append(ticker)

    if failed_tickers:
        print(f"  [!] Failed to fetch data for: {', '.join(failed_tickers)}")

    return result


def fetch_historical_prices(ticker: str, period: str = "3mo") -> dict:
    """
    Fetch historical price data for technical analysis.

    Args:
        ticker: Stock ticker symbol
        period: Time period (1mo, 3mo, 6mo, 1y, etc.)

    Returns:
        Dictionary with OHLCV data
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            return {'error': 'No historical data available'}

        return {
            'dates': hist.index.strftime('%Y-%m-%d').tolist(),
            'open': hist['Open'].tolist(),
            'high': hist['High'].tolist(),
            'low': hist['Low'].tolist(),
            'close': hist['Close'].tolist(),
            'volume': hist['Volume'].tolist(),
        }

    except Exception as e:
        return {'error': str(e)}


# =============================================================================
# Fundamental Data
# =============================================================================

def get_fundamentals(tickers: list[str]) -> dict:
    """
    Fetch fundamental metrics for a list of tickers.

    Args:
        tickers: List of stock ticker symbols

    Returns:
        Dictionary with ticker as key and fundamental data as value
    """
    result = {}

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Calculate revenue growth if we have the data
            revenue_growth = info.get('revenueGrowth', 0) or 0

            # Get trailing and forward P/E
            trailing_pe = info.get('trailingPE', 0) or 0
            forward_pe = info.get('forwardPE', 0) or 0

            result[ticker] = {
                # Valuation
                'pe_ratio': trailing_pe,
                'forward_pe': forward_pe,
                'peg_ratio': info.get('pegRatio', 0) or 0,
                'price_to_book': info.get('priceToBook', 0) or 0,
                'price_to_sales': info.get('priceToSalesTrailing12Months', 0) or 0,

                # Growth & Profitability
                'revenue_ttm': info.get('totalRevenue', 0) or 0,
                'revenue_growth_yoy': revenue_growth,
                'earnings_growth': info.get('earningsGrowth', 0) or 0,
                'profit_margin': info.get('profitMargins', 0) or 0,
                'operating_margin': info.get('operatingMargins', 0) or 0,

                # Cash Flow
                'free_cash_flow': info.get('freeCashflow', 0) or 0,
                'operating_cash_flow': info.get('operatingCashflow', 0) or 0,

                # Balance Sheet
                'total_cash': info.get('totalCash', 0) or 0,
                'total_debt': info.get('totalDebt', 0) or 0,
                'debt_to_equity': info.get('debtToEquity', 0) or 0,

                # Other
                'market_cap': info.get('marketCap', 0) or 0,
                'enterprise_value': info.get('enterpriseValue', 0) or 0,
                'beta': info.get('beta', 0) or 0,
                'dividend_yield': info.get('dividendYield', 0) or 0,

                # Earnings
                'earnings_date': _get_earnings_date(info),

                # Company Info
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'company_name': info.get('shortName', ticker),
            }

        except Exception as e:
            print(f"Warning: Failed to fetch fundamentals for {ticker}: {e}")
            result[ticker] = {
                'error': str(e),
                'pe_ratio': 0,
                'revenue_growth_yoy': 0,
                'free_cash_flow': 0,
            }

    return result


def _get_earnings_date(info: dict) -> Optional[str]:
    """Extract next earnings date from stock info."""
    try:
        # yfinance returns earnings dates as timestamps
        earnings_dates = info.get('earningsTimestamp')
        if earnings_dates:
            return datetime.fromtimestamp(earnings_dates).strftime('%Y-%m-%d')

        # Try alternative field
        earnings_dates = info.get('earningsDates')
        if earnings_dates and len(earnings_dates) > 0:
            return earnings_dates[0].strftime('%Y-%m-%d')

    except Exception:
        pass

    return None


# =============================================================================
# Technical Data
# =============================================================================

def calculate_technical_indicators(ticker: str) -> dict:
    """
    Calculate technical indicators for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with technical indicators
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")

        if hist.empty or len(hist) < 14:
            return {'error': 'Insufficient historical data'}

        close_prices = hist['Close']

        # Simple Moving Averages
        sma_20 = close_prices.rolling(window=20).mean().iloc[-1] if len(close_prices) >= 20 else 0
        sma_50 = close_prices.rolling(window=50).mean().iloc[-1] if len(close_prices) >= 50 else 0

        # RSI Calculation (14-day)
        rsi = _calculate_rsi(close_prices, period=14)

        # Support and Resistance (simple: recent lows/highs)
        recent_prices = close_prices.tail(20)
        support = recent_prices.min()
        resistance = recent_prices.max()

        current_price = close_prices.iloc[-1]

        return {
            'current_price': current_price,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'rsi_14': rsi,
            'support_level': support,
            'resistance_level': resistance,
            'price_vs_sma20': ((current_price - sma_20) / sma_20 * 100) if sma_20 > 0 else 0,
            'price_vs_sma50': ((current_price - sma_50) / sma_50 * 100) if sma_50 > 0 else 0,
        }

    except Exception as e:
        return {'error': str(e)}


def _calculate_rsi(prices, period: int = 14) -> float:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return 50.0  # Default neutral value

    # Calculate price changes
    delta = prices.diff()

    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = (-delta).where(delta < 0, 0)

    # Calculate average gains and losses
    avg_gain = gains.rolling(window=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)


# =============================================================================
# News Data
# =============================================================================

def scan_news(tickers: list[str], days: int = 7) -> dict:
    """
    Scan Google News RSS for recent headlines about tickers.

    Args:
        tickers: List of stock ticker symbols
        days: Number of days to look back

    Returns:
        Dictionary with ticker as key and list of news items as value
    """
    result = {}
    cutoff_date = datetime.now() - timedelta(days=days)

    for ticker in tickers:
        try:
            # Build Google News RSS URL (URL-encode the query)
            query = quote_plus(f"{ticker} stock")
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

            feed = feedparser.parse(url)
            news_items = []

            for entry in feed.entries[:10]:  # Limit to 10 articles
                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])

                # Skip old articles
                if pub_date and pub_date < cutoff_date:
                    continue

                news_items.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': pub_date.strftime('%Y-%m-%d') if pub_date else '',
                    'source': _extract_source(entry.get('source', {}).get('title', '')),
                })

            result[ticker] = news_items

            # Small delay to avoid rate limiting
            time.sleep(0.2)

        except Exception as e:
            print(f"Warning: Failed to fetch news for {ticker}: {e}")
            result[ticker] = []

    return result


def _extract_source(source_text: str) -> str:
    """Extract clean source name from RSS source field."""
    if not source_text:
        return 'Unknown'
    # Google News format often includes source in specific format
    return source_text.split(' - ')[-1] if ' - ' in source_text else source_text


# =============================================================================
# Combined Data Fetching
# =============================================================================

def fetch_all_market_data(tickers: list[str], include_news: bool = True) -> dict:
    """
    Fetch all market data for a list of tickers.

    Args:
        tickers: List of stock ticker symbols
        include_news: Whether to fetch news (slower)

    Returns:
        Combined dictionary with all market data
    """
    print(f"Fetching market data for {len(tickers)} stocks...")

    # Fetch price data
    print("  - Fetching prices...")
    prices = fetch_market_data(tickers)

    # Fetch fundamentals
    print("  - Fetching fundamentals...")
    fundamentals = get_fundamentals(tickers)

    # Fetch technical indicators
    print("  - Calculating technicals...")
    technicals = {}
    for ticker in tickers:
        technicals[ticker] = calculate_technical_indicators(ticker)

    # Fetch news (optional)
    news = {}
    if include_news:
        print("  - Scanning news...")
        news = scan_news(tickers)

    # Combine all data
    result = {
        'timestamp': datetime.now().isoformat(),
        'tickers': {}
    }

    for ticker in tickers:
        result['tickers'][ticker] = {
            'price': prices.get(ticker, {}),
            'fundamentals': fundamentals.get(ticker, {}),
            'technicals': technicals.get(ticker, {}),
            'news': news.get(ticker, []),
        }

    print("Data fetching complete.")
    return result
