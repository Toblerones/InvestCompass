# InvestCompass - Portfolio AI Agent

An AI-powered portfolio advisor that analyzes tech stock positions and provides buy/sell/hold recommendations using Claude API.

## Features

- **Portfolio Management**: Track positions with FIFO compliance (30-day minimum hold)
- **Market Intelligence**: Fetch prices, fundamentals, technicals, and news via yfinance and RSS
- **AI Recommendations**: LLM-powered analysis with clear reasoning and confidence levels
- **Terminal Dashboard**: Clean CLI output with actionable insights
- **Trade Recording**: Interactive workflow to record executed trades
- **Retry Logic**: Automatic retry with exponential backoff for API failures

## Project Structure

```
InvestCompass/
├── 1. Requirement/
│   └── ProductRequirement.md    # Full product specification
├── 2. Plan/
│   └── ImplementationPlan.md    # Sprint-based implementation plan
├── App/
│   ├── src/
│   │   ├── advisor.py           # Main CLI entry point
│   │   ├── data_collector.py    # Market data fetching
│   │   ├── analyzer.py          # Ranking and analysis
│   │   ├── ai_agent.py          # Claude API integration
│   │   ├── display.py           # Terminal formatting
│   │   └── utils.py             # Helper functions
│   ├── config/
│   │   ├── config.json          # Watchlist and settings
│   │   ├── portfolio.json       # Your positions
│   │   └── strategy.txt         # Investment strategy for AI
│   └── requirements.txt         # Python dependencies
├── .gitignore
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
cd App
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the App directory with your Anthropic API key:

```bash
# App/.env
ANTHROPIC_API_KEY=your-api-key-here
```

Or set it as an environment variable:

```bash
# Windows
set ANTHROPIC_API_KEY=your-api-key-here

# macOS/Linux
export ANTHROPIC_API_KEY=your-api-key-here
```

### 3. Initialize Portfolio

```bash
cd App
python -m src.advisor init
```

Or edit `App/config/portfolio.json` directly:

```json
{
  "positions": [
    {
      "ticker": "GOOGL",
      "quantity": 28,
      "purchase_price": 155.00,
      "purchase_date": "2025-12-01"
    }
  ],
  "cash_available": 400.00,
  "last_updated": "2026-01-26"
}
```

### 4. Run the Advisor

```bash
cd App

# Full analysis with AI recommendations
python -m src.advisor

# Quick portfolio status (no AI call)
python -m src.advisor check

# Record executed trades
python -m src.advisor confirm

# Show help
python -m src.advisor help
```

## Commands

### `run` (default)
Full analysis workflow:
1. Loads configuration and portfolio
2. Fetches market data for watchlist stocks
3. Calculates fundamental rankings and technical indicators
4. Scans recent news
5. Calls Claude API for recommendations
6. Displays full dashboard with actions

### `check`
Quick portfolio status:
- Shows current positions with P&L
- Displays FIFO lock status
- No AI call (faster)

### `confirm`
Record executed trades interactively:
```
> bought NVDA 10 shares at 450.00
> sold GOOGL 28 shares at 175.50
> add cash 500
> done
```

### `init`
Initialize or reset portfolio with starting cash.

## Configuration

### config.json

```json
{
  "watchlist": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMZN", "AMD", "TSLA", "CRM", "INTC"],
  "monthly_budget": 400,
  "transaction_fee": 10,
  "max_positions": 3,
  "stop_loss_percent": -10,
  "profit_target_percent": 20,
  "min_hold_days": 30
}
```

| Field | Description |
|-------|-------------|
| `watchlist` | Stock tickers to analyze (uppercase) |
| `monthly_budget` | New capital available monthly |
| `transaction_fee` | Cost per trade (buy/sell) |
| `max_positions` | Maximum concurrent positions |
| `stop_loss_percent` | Trigger for stop-loss alert (negative) |
| `profit_target_percent` | Trigger for profit-taking alert |
| `min_hold_days` | FIFO minimum hold period |

### strategy.txt

The strategy file contains investment principles that guide the AI's recommendations. Edit to match your investment style:

- Risk tolerance
- Hold period preferences
- Entry/exit criteria
- Position sizing rules

## How It Works

### Data Collection
- **Prices**: Real-time via yfinance
- **Fundamentals**: P/E, revenue growth, FCF, margins
- **Technicals**: RSI, SMA, support/resistance
- **News**: Google News RSS (last 7 days)

### Ranking Algorithm
Stocks are ranked by a composite fundamental score:
- 30% Revenue Growth (YoY)
- 25% Free Cash Flow Yield
- 25% P/E Ratio (inverted, lower is better)
- 20% 3-Month Price Momentum

### AI Recommendations
Claude analyzes:
1. Current positions and P&L
2. FIFO lock status (cannot sell positions held < 30 days)
3. Stock rankings and entry opportunities
4. Recent news sentiment
5. Your strategy principles

Returns structured actions (BUY/SELL/HOLD) with reasoning.

### FIFO Compliance
The 30-day minimum hold rule is enforced at multiple levels:
- Positions are marked as LOCKED/SELLABLE in the display
- AI receives lock status and cannot recommend selling locked positions
- Validation layer blocks invalid sell actions

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
Set your API key in `.env` file or as environment variable.

### "Config file not found"
Run from the App directory, or ensure config files exist in `App/config/`.

### "No price data available for TICKER"
- Check ticker symbol is valid
- yfinance may have temporary issues; retry later
- Market may be closed (no real-time data)

### Unicode/Encoding errors on Windows
The display uses ASCII-safe characters. If you still see encoding issues, ensure your terminal supports UTF-8 or try:
```bash
chcp 65001
```

### API rate limits
The advisor includes automatic retry with exponential backoff. If rate limited:
- Wait and retry
- Reduce request frequency
- Check your API usage limits

## Tech Stack

- Python 3.10+
- [Claude API](https://www.anthropic.com/api) (Anthropic) - AI recommendations
- [yfinance](https://github.com/ranaroussi/yfinance) - Market data
- [feedparser](https://feedparser.readthedocs.io/) - News RSS parsing
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment management

## Documentation

- [Product Requirements](1.%20Requirement/ProductRequirement.md) - Full product specification
- [Implementation Plan](2.%20Plan/ImplementationPlan.md) - Sprint breakdown and tasks

## License

Personal use only.
