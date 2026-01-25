# Financial Data & Fundamentals
1. Yahoo Finance API (yfinance - Python library)

What you get: Historical prices, P/E ratios, market cap, revenue, EPS, free cash flow, balance sheets
Usage: pip install yfinance - fully free, no API key needed
Limitations: 15-20 min delayed data, rate limits on excessive requests
Best for: Your monthly fundamental screening and daily price tracking

2. Alpha Vantage (Free tier)

What you get: Real-time quotes, technical indicators, fundamental data, earnings dates
Usage: Free API key (500 requests/day, 5 requests/minute)
URL: alphavantage.co
Best for: Supplementing yfinance data, getting earnings calendars

3. Financial Modeling Prep (Free tier)

What you get: Income statements, balance sheets, cash flow statements, ratios
Usage: Free API key (250 requests/day)
URL: financialmodelingprep.com
Best for: Detailed quarterly/annual financials for your scoring model

# News & Sentiment
4. Google News RSS Feeds

What you get: Latest news for specific stock tickers or keywords
Usage: RSS feed parsers (Python: feedparser library)
Example URL: https://news.google.com/rss/search?q=MSFT+stock
Best for: Free, real-time news monitoring without API limits

5. NewsAPI (Free tier)

What you get: News articles from 80,000+ sources, search by company/ticker
Usage: Free API key (100 requests/day, last 30 days of news only)
URL: newsapi.org
Best for: Structured news data with sentiment analysis potential

6. Reddit API (PRAW - Python)

What you get: Discussions from r/stocks, r/investing, r/technology
Usage: Free API access with Reddit account
Best for: Retail sentiment gauge (use cautiously, high noise)

# Market Data & Technical Analysis
7. Yahoo Finance (again)

What you get: RSI, MACD, moving averages via yfinance or direct scraping
Usage: Can calculate indicators yourself from OHLCV data
Best for: All your technical indicators

8. TradingView (manual/scraping)

What you get: Charts, technical analysis, economic calendar
Usage: Free account for viewing, or scrape public charts (check ToS)
Best for: Visual verification of your programmatic signals

# Economic Calendar & Events
9. Yahoo Finance Events Calendar

What you get: Earnings dates, ex-dividend dates, stock splits
Usage: Accessible via yfinance library
Best for: Planning entries/exits around earnings

10. Federal Reserve Economic Data (FRED)

What you get: Interest rates, GDP, inflation, employment data
Usage: Free API from stlouisfed.org
Best for: Macro context for tech sector rotation