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
import re
from difflib import SequenceMatcher
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


def calculate_earnings_proximity(earnings_date_str: Optional[str]) -> Optional[dict]:
    """
    Calculate days until earnings and determine trading restrictions.

    Args:
        earnings_date_str: Date string in YYYY-MM-DD format (from fundamentals)

    Returns:
        Dict with earnings proximity info or None if invalid/not applicable
        {
            'date': str,              # YYYY-MM-DD
            'days_until': int,        # Days from today
            'sell_restricted': bool,  # True if within 3-day blackout
            'buy_restricted': bool,   # True if within 7-day window
            'status': str             # 'IMMINENT', 'UPCOMING', or 'SAFE'
        }
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

        # Determine restrictions based on strategy rules
        sell_restricted = days_until <= 3  # 3-day sell blackout
        buy_restricted = days_until <= 7   # 7-day buy restriction

        # Classify status
        if days_until <= 7:
            status = 'IMMINENT'
        elif days_until <= 30:
            status = 'UPCOMING'
        else:
            status = 'SAFE'

        return {
            'date': earnings_date_str,
            'days_until': days_until,
            'sell_restricted': sell_restricted,
            'buy_restricted': buy_restricted,
            'status': status
        }
    except (ValueError, TypeError):
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
# Benchmark & Price Context
# =============================================================================

BENCHMARK_TICKER = "SPY"  # S&P 500 ETF as market benchmark


def fetch_benchmark_data(period: str = "3mo") -> dict:
    """
    Fetch benchmark (SPY) historical data for price context calculations.

    Args:
        period: Time period to fetch (default 3mo for 30-day calculations)

    Returns:
        Dictionary with benchmark data including 30-day return
    """
    try:
        stock = yf.Ticker(BENCHMARK_TICKER)
        hist = stock.history(period=period)

        if hist.empty or len(hist) < 22:  # Need ~22 trading days for 30-day return
            return {'error': 'Insufficient benchmark data', 'return_30d': 0}

        close_prices = hist['Close']

        # Calculate 30-day return (approximately 22 trading days)
        current_price = close_prices.iloc[-1]
        price_30d_ago = close_prices.iloc[-22] if len(close_prices) >= 22 else close_prices.iloc[0]
        return_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100

        return {
            'ticker': BENCHMARK_TICKER,
            'current_price': current_price,
            'price_30d_ago': price_30d_ago,
            'return_30d': round(return_30d, 2),
        }

    except Exception as e:
        print(f"Warning: Failed to fetch benchmark data: {e}")
        return {'error': str(e), 'return_30d': 0}


def calculate_price_context(ticker: str, benchmark_return: float) -> dict:
    """
    Calculate 30-day price context for a ticker vs benchmark.

    Args:
        ticker: Stock ticker symbol
        benchmark_return: 30-day return of benchmark (SPY)

    Returns:
        Dictionary with price context including trend classification
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")

        if hist.empty or len(hist) < 22:
            return {
                'ticker': ticker,
                'return_30d': 0,
                'benchmark_return': benchmark_return,
                'relative_performance': 0,
                'trend': 'UNKNOWN',
                'error': 'Insufficient data'
            }

        close_prices = hist['Close']

        # Calculate 30-day return
        current_price = close_prices.iloc[-1]
        price_30d_ago = close_prices.iloc[-22] if len(close_prices) >= 22 else close_prices.iloc[0]
        return_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100

        # Calculate relative performance vs benchmark
        relative_performance = return_30d - benchmark_return

        # Classify trend (±3% threshold)
        if relative_performance > 3:
            trend = 'OUTPERFORMING'
        elif relative_performance < -3:
            trend = 'UNDERPERFORMING'
        else:
            trend = 'NEUTRAL'

        return {
            'ticker': ticker,
            'current_price': round(current_price, 2),
            'return_30d': round(return_30d, 2),
            'benchmark_return': round(benchmark_return, 2),
            'relative_performance': round(relative_performance, 2),
            'trend': trend,
        }

    except Exception as e:
        return {
            'ticker': ticker,
            'return_30d': 0,
            'benchmark_return': benchmark_return,
            'relative_performance': 0,
            'trend': 'UNKNOWN',
            'error': str(e)
        }


# =============================================================================
# News Data - Theme Keywords & Source Quality
# =============================================================================

THEME_KEYWORDS = {
    "regulatory": {
        "primary": ["antitrust", "investigation", "doj", "ftc", "lawsuit", "probe",
                   "eu commission", "fine", "penalty"],
        "secondary": ["regulation", "regulators", "legal action", "government suit", "monopoly"],
        "priority": 1  # Check first (most important)
    },
    "earnings": {
        "primary": ["earnings", "revenue", "profit", "eps", "quarterly results",
                   "q1", "q2", "q3", "q4", "beat", "miss", "guidance"],
        "secondary": ["sales", "income", "forecast", "outlook", "analyst estimates"],
        "priority": 2
    },
    "product": {
        "primary": ["launch", "release", "announcement", "unveils", "introduces",
                   "new product", "update", "version"],
        "secondary": ["features", "beta", "rollout", "availability", "upgrade"],
        "priority": 3
    },
    "leadership": {
        "primary": ["ceo", "cfo", "executive", "resignation", "appointed",
                   "steps down", "fires", "hires", "management change"],
        "secondary": ["leadership", "departure", "promotes", "board", "founder"],
        "priority": 4
    },
    "legal": {
        "primary": ["lawsuit", "litigation", "settlement", "court", "ruling",
                   "verdict", "judge", "plaintiff"],
        "secondary": ["case", "trial", "appeal", "damages", "injunction"],
        "priority": 5
    },
    "acquisition": {
        "primary": ["acquires", "merger", "acquisition", "buys", "takeover", "deal", "purchase"],
        "secondary": ["m&a", "consolidation", "buyout", "combines"],
        "priority": 6
    },
    "partnership": {
        "primary": ["partnership", "collaboration", "teams up", "alliance",
                   "joint venture", "partnership with"],
        "secondary": ["partners", "cooperates", "works with", "agreement"],
        "priority": 7
    },
    "layoffs": {
        "primary": ["layoffs", "job cuts", "fires", "workforce reduction",
                   "downsizing", "restructuring"],
        "secondary": ["cutting jobs", "eliminates positions", "headcount"],
        "priority": 8
    },
    "data_breach": {
        "primary": ["breach", "hack", "cyberattack", "data leak",
                   "security incident", "compromised"],
        "secondary": ["hacked", "stolen data", "vulnerability", "ransomware"],
        "priority": 9
    },
    "analyst": {
        "primary": ["upgrade", "downgrade", "price target", "analyst rating",
                   "buy rating", "sell rating"],
        "secondary": ["initiates coverage", "maintains", "raises target", "lowers target"],
        "priority": 10
    },
    "stock_movement": {
        "primary": ["stock rises", "stock falls", "shares up", "shares down",
                   "gains", "losses", "rallies", "drops"],
        "secondary": ["climbs", "jumps", "plunges", "surges", "tumbles"],
        "priority": 99  # Check last (usually noise)
    }
}

SOURCE_QUALITY = {
    # Tier 1 - Most reliable (1.0)
    "reuters": 1.0,
    "bloomberg": 1.0,
    "wsj": 1.0,
    "wall street journal": 1.0,
    "financial times": 1.0,
    "ft": 1.0,
    # Tier 2 - Reliable (0.9)
    "cnbc": 0.9,
    "barron's": 0.9,
    "marketwatch": 0.8,
    # Tier 3 - Tech-focused (0.7)
    "techcrunch": 0.7,
    "the verge": 0.7,
    "wired": 0.7,
    "ars technica": 0.7,
    # Tier 4 - Lower quality (0.3-0.5)
    "motley fool": 0.3,
    "fool": 0.3,
    "seeking alpha": 0.3,
    "investorplace": 0.3,
    "benzinga": 0.4,
    # Default for unknown sources
    "_default": 0.5
}


# Material event keywords for targeted Google News queries
# These filter out price movement noise at the source
MATERIAL_EVENT_KEYWORDS = [
    "earnings", "revenue", "profit", "quarterly",
    "investigation", "lawsuit", "antitrust", "probe",
    "acquisition", "merger", "partnership", "deal",
    "CEO", "CFO", "executive", "leadership",
    "layoffs", "restructuring", "job cuts",
    "product launch", "announces", "unveils",
    "regulatory", "fine", "settlement",
    "data breach", "security", "hack",
    "guidance", "forecast", "outlook"
]


def build_material_events_query(ticker: str) -> str:
    """
    Build targeted Google News query for material events only.

    Instead of generic "{ticker} stock" which returns price movement noise,
    this creates a query like "{ticker} (earnings OR acquisition OR lawsuit OR ...)"

    Args:
        ticker: Stock ticker symbol (e.g., "GOOGL")

    Returns:
        Formatted query string for Google News RSS
    """
    keywords = " OR ".join(MATERIAL_EVENT_KEYWORDS)
    return f"{ticker} ({keywords})"


def deduplicate_headlines(articles: list, threshold: float = 0.6) -> tuple[list, int]:
    """
    Remove duplicate articles based on headline similarity.

    Uses fuzzy matching to identify and remove duplicate stories that appear
    from multiple sources (e.g., "DOJ sues Google" and "DOJ files Google lawsuit").

    Args:
        articles: List of article dicts with 'title' field
        threshold: Similarity ratio (0-1) above which articles are considered duplicates.
                   Default 0.6 catches rewrites while keeping distinct stories.

    Returns:
        Tuple of (deduplicated_articles, removed_count)
    """
    if not articles:
        return [], 0

    unique = []
    seen_normalized = []

    for article in articles:
        # Normalize headline for comparison
        headline = article.get('title', '').lower()
        headline = re.sub(r'[^\w\s]', '', headline)  # Remove punctuation
        headline = ' '.join(headline.split())  # Normalize whitespace

        # Check against all seen headlines
        is_duplicate = False
        for seen in seen_normalized:
            if SequenceMatcher(None, headline, seen).ratio() > threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique.append(article)
            seen_normalized.append(headline)

    removed_count = len(articles) - len(unique)
    return unique, removed_count


def get_source_quality(source: str) -> float:
    """Get quality score for a news source."""
    if not source:
        return SOURCE_QUALITY["_default"]

    source_lower = source.lower()
    for key, score in SOURCE_QUALITY.items():
        if key != "_default" and key in source_lower:
            return score
    return SOURCE_QUALITY["_default"]


def classify_headline(headline: str, url: str = "") -> str:
    """
    Classify a news headline into a theme.

    Args:
        headline: The headline text
        url: Optional URL for additional context

    Returns:
        theme name (str) or "other"
    """
    # Normalize
    text = headline.lower()

    # Sort themes by priority
    sorted_themes = sorted(THEME_KEYWORDS.items(),
                          key=lambda x: x[1]['priority'])

    # Check each theme
    for theme_name, keywords in sorted_themes:
        # Check primary keywords first (higher weight)
        for keyword in keywords['primary']:
            if keyword in text:
                return theme_name

        # Check secondary keywords
        for keyword in keywords['secondary']:
            if keyword in text:
                return theme_name

    # No match
    return "other"


def cluster_news(articles: list) -> dict:
    """
    Cluster articles by theme.

    Args:
        articles: List of {title, published, link, source}

    Returns:
        Dict of {theme: [articles]}
    """
    clusters = {}

    for article in articles:
        headline = article.get('title', '')
        theme = classify_headline(headline, article.get('link', ''))

        if theme not in clusters:
            clusters[theme] = []

        clusters[theme].append(article)

    return clusters


def get_top_themes(clusters: dict, max_themes: int = 5, exclude_noise: bool = True) -> list:
    """
    Get top N themes by article count, excluding noise.

    Args:
        clusters: Dict from cluster_news()
        max_themes: Max themes to return
        exclude_noise: Whether to filter out stock_movement and analyst themes

    Returns:
        List of (theme, articles) sorted by article count
    """
    # Filter noise if requested
    if exclude_noise:
        noise_themes = ['stock_movement', 'analyst', 'other']
        filtered = {k: v for k, v in clusters.items() if k not in noise_themes}
    else:
        filtered = clusters

    # Sort by article count (weighted by source quality)
    def theme_importance(item):
        theme, articles = item
        count = len(articles)
        quality_sum = sum(get_source_quality(a.get('source', '')) for a in articles)
        return count + (quality_sum * 0.5)  # Count matters more, quality is bonus

    sorted_themes = sorted(filtered.items(), key=theme_importance, reverse=True)

    # Return top N
    return sorted_themes[:max_themes]


def classify_frequency(article_count: int, days: int) -> str:
    """
    Classify frequency based on article count.

    Args:
        article_count: Number of articles on this theme
        days: Lookback period in days

    Returns:
        "HIGH", "MEDIUM", or "LOW"
    """
    articles_per_week = (article_count / days) * 7

    if articles_per_week >= 3:
        return "HIGH"
    elif articles_per_week >= 1:
        return "MEDIUM"
    else:
        return "LOW"


# =============================================================================
# News Data - Fetching
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


def scan_news_enhanced(tickers: list[str], days: int = 14, max_articles: int = 25) -> dict:
    """
    Scan news with clustering and filtering for enhanced context.

    Args:
        tickers: List of stock ticker symbols
        days: Number of days to look back (default 14 for better trend detection)
        max_articles: Maximum articles to fetch per ticker before filtering

    Returns:
        Dictionary with enhanced news structure:
        {
            "TICKER": {
                "themes": [
                    {
                        "name": "regulatory",
                        "headline": "DOJ expands investigation",
                        "date": "2026-01-23",
                        "source": "Reuters",
                        "article_count": 4,
                        "frequency": "HIGH",
                        "urls": [...]
                    }
                ],
                "raw_articles": [...],  # Deduplicated articles for reference
                "stats": {
                    "total_fetched": 25,
                    "duplicates_removed": 3,
                    "themes_found": 3,
                    "noise_filtered": 12
                }
            }
        }
    """
    result = {}
    cutoff_date = datetime.now() - timedelta(days=days)

    for ticker in tickers:
        try:
            # Build Google News RSS URL with targeted material events query
            query = quote_plus(build_material_events_query(ticker))
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

            feed = feedparser.parse(url)
            raw_articles = []

            for entry in feed.entries[:max_articles]:
                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])

                # Skip old articles
                if pub_date and pub_date < cutoff_date:
                    continue

                raw_articles.append({
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': pub_date.strftime('%Y-%m-%d') if pub_date else '',
                    'source': _extract_source(entry.get('source', {}).get('title', '')),
                })

            # Deduplicate similar headlines before clustering
            total_before_dedup = len(raw_articles)
            raw_articles, dedup_count = deduplicate_headlines(raw_articles)

            # Cluster articles by theme
            clusters = cluster_news(raw_articles)

            # Get top material themes (excludes noise)
            top_themes = get_top_themes(clusters, max_themes=5, exclude_noise=True)

            # Format themes for output
            themes = []
            for theme_name, articles in top_themes:
                # Pick most recent article as representative
                sorted_articles = sorted(articles,
                                        key=lambda x: x.get('published', ''),
                                        reverse=True)
                representative = sorted_articles[0] if sorted_articles else {}

                themes.append({
                    "name": theme_name,
                    "headline": representative.get('title', ''),
                    "date": representative.get('published', ''),
                    "source": representative.get('source', 'Unknown'),
                    "article_count": len(articles),
                    "frequency": classify_frequency(len(articles), days),
                    "urls": [a.get('link', '') for a in articles]
                })

            # Calculate noise filtered count
            noise_count = sum(len(v) for k, v in clusters.items()
                            if k in ['stock_movement', 'analyst', 'other'])

            result[ticker] = {
                "themes": themes,
                "raw_articles": raw_articles,
                "stats": {
                    "total_fetched": total_before_dedup,
                    "duplicates_removed": dedup_count,
                    "themes_found": len(themes),
                    "noise_filtered": noise_count
                }
            }

            # Small delay to avoid rate limiting
            time.sleep(0.2)

        except Exception as e:
            print(f"Warning: Failed to fetch enhanced news for {ticker}: {e}")
            result[ticker] = {
                "themes": [],
                "raw_articles": [],
                "stats": {"total_fetched": 0, "duplicates_removed": 0, "themes_found": 0, "noise_filtered": 0}
            }

    return result


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

    # Fetch benchmark data for price context
    print("  - Fetching benchmark (SPY) data...")
    benchmark = fetch_benchmark_data()
    benchmark_return = benchmark.get('return_30d', 0)

    # Calculate price context for each ticker
    print("  - Calculating price context...")
    price_context = {}
    for ticker in tickers:
        price_context[ticker] = calculate_price_context(ticker, benchmark_return)

    # Fetch news (optional)
    news = {}
    if include_news:
        print("  - Scanning news (enhanced clustering)...")
        news = scan_news_enhanced(tickers)

    # Combine all data
    result = {
        'timestamp': datetime.now().isoformat(),
        'benchmark': benchmark,
        'tickers': {}
    }

    for ticker in tickers:
        # Get fundamentals data for this ticker
        ticker_fundamentals = fundamentals.get(ticker, {})

        # Calculate earnings proximity from existing earnings_date
        earnings_date = ticker_fundamentals.get('earnings_date')
        earnings_proximity = calculate_earnings_proximity(earnings_date)

        result['tickers'][ticker] = {
            'price': prices.get(ticker, {}),
            'fundamentals': ticker_fundamentals,
            'technicals': technicals.get(ticker, {}),
            'price_context': price_context.get(ticker, {}),
            'news': news.get(ticker, {"themes": [], "raw_articles": [], "stats": {}}),
            'earnings': earnings_proximity,  # NEW: Earnings proximity data
        }

    print("Data fetching complete.")
    return result
