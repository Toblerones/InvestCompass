# InvestCompass - Portfolio AI Agent

An AI-powered portfolio advisor that analyzes tech stock positions and provides buy/sell/hold recommendations using Claude API.

## Project Structure

```
InvestCompass/
├── 1. Requirement/
│   └── ProductRequirement.md    # Full product specification
├── 2. Plan/
│   └── ImplementationPlan.md    # Sprint-based implementation plan
├── App/
│   ├── src/                     # Python source code
│   ├── config/                  # Configuration files
│   ├── tests/                   # Unit tests
│   └── requirements.txt         # Python dependencies
```

## Features

- **Portfolio Management**: Track positions with FIFO compliance (30-day minimum hold)
- **Market Intelligence**: Fetch prices, fundamentals, and news via yfinance and RSS
- **AI Recommendations**: LLM-powered analysis with clear reasoning
- **Terminal Dashboard**: Clean CLI output with actionable insights

## Quick Start

### 1. Install Dependencies

```bash
cd App
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp App/.env.example App/.env
# Edit App/.env and add your Anthropic API key
```

### 3. Initialize Portfolio

Edit `App/config/portfolio.json` with your current positions, or start empty.

### 4. Run

```bash
cd App
python src/advisor.py          # Full analysis
python src/advisor.py check    # Quick status
python src/advisor.py confirm  # Record trades
```

## Documentation

- [Product Requirements](1.%20Requirement/ProductRequirement.md) - Full product specification
- [Implementation Plan](2.%20Plan/ImplementationPlan.md) - Sprint breakdown and tasks

## Tech Stack

- Python 3.10+
- Claude API (Anthropic)
- yfinance (market data)
- feedparser (news RSS)
- pandas (data processing)

## License

Personal use only.
