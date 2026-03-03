# Portfolio AI Agent - Product Requirement

**Version**: 2.0
**Date**: February 7, 2026
**Author**: Tobes (Product Owner)
**Previous Version**: 1.0 (January 25, 2026)

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-25 | Initial product proposal |
| 2.0 | 2026-02-07 | Incorporated CR001-CR006 implementations |

---

## 1. Executive Summary

### 1.1 Product Vision
An AI-powered portfolio advisor that analyzes tech stock positions and prescribes specific buy/sell/hold actions based on fundamental analysis, technical signals, news events, earnings calendar, and regulatory constraints. The system uses LLM reasoning (Claude API) to make intelligent decisions that balance ranking quality, transaction costs, timing, and portfolio optimization.

### 1.2 Target User
- **User**: Individual retail investor (Tobes)
- **Investment style**: Medium-term (3-6 months), fundamental-driven
- **Capital**: $300-500/month
- **Universe**: Top 10 technology stocks (FAANG + MSFT, NVDA, TSLA, etc.)
- **Regulatory constraint**: Must hold positions minimum 30 days (FIFO lot-based)

### 1.3 Core Value Proposition
Eliminates emotional decision-making and analysis paralysis by providing clear, reasoned recommendations that respect regulatory constraints, detect material events affecting holdings, and optimize for long-term portfolio quality.

---

## 2. Product Features

### 2.1 Portfolio State Management

**Purpose**: Single source of truth for current positions with lot-based tracking

**Capabilities**:
- Stores positions with lot-based structure (each ticker once, multiple lots underneath)
- Tracks per-lot: quantity, purchase_price, purchase_date
- Calculates at runtime: total_quantity, average_cost, sellable_quantity, lock_status
- Supports FIFO (First-In-First-Out) sell order
- Displays: lock status (SELLABLE, PARTIAL_LOCK, LOCKED), unlock calendar
- Persists: JSON file format (`portfolio.json`)
- Auto-migration from legacy flat format to lot-based format

**Data Schema**:
```json
{
  "positions": [
    {
      "ticker": "MSFT",
      "lots": [
        {
          "quantity": 1.5,
          "purchase_price": 507.60,
          "purchase_date": "2025-11-18",
          "notes": "Initial position"
        },
        {
          "quantity": 1.0,
          "purchase_price": 434.00,
          "purchase_date": "2026-01-30"
        }
      ]
    },
    {
      "ticker": "NVDA",
      "lots": [
        {
          "quantity": 1.0,
          "purchase_price": 191.83,
          "purchase_date": "2026-01-30"
        }
      ]
    }
  ],
  "cash_available": 274.17,
  "last_updated": "2026-02-07"
}
```

**Runtime Consolidation**:
The system computes aggregates at runtime (not stored):
- `total_quantity`: Sum of all lot quantities
- `average_cost`: Weighted average of lot purchase prices
- `sellable_quantity`: Sum of lots held 30+ days
- `lock_status`: SELLABLE | PARTIAL_LOCK | LOCKED

---

### 2.2 Market Intelligence Engine

**Purpose**: Collect and analyze market data for decision-making

**Data Sources** (all free tier):
- **yfinance**: Stock prices, fundamentals (P/E, revenue, FCF), technical data, earnings calendar
- **Google News RSS**: Headlines for news scanning with enhanced filtering
- **SPY Benchmark**: 30-day relative performance tracking

**Data Collected**:
- Current prices (OHLCV)
- Fundamental metrics: P/E ratio, revenue growth, free cash flow, market cap
- Technical indicators: RSI, support/resistance levels
- **Enhanced News** (14-day lookback):
  - Clustered by theme (earnings, regulatory, M&A, leadership, product)
  - Filtered by source quality (tier 1-3)
  - Deduplicated headlines
  - Frequency classification (HIGH/MEDIUM/LOW)
- **Earnings calendar**: Days until earnings, trading restrictions
- **Price context**: 30-day return vs SPY benchmark

**Processing**:
- Calculate fundamental ranking score (1-10) for each stock
- Identify technical entry signals (oversold, support levels)
- Cluster and filter news into material themes
- Calculate 30-day performance vs market benchmark
- Detect material events affecting holdings
- Compute transaction costs for potential swaps

---

### 2.3 AI Recommendation Engine

**Purpose**: LLM-powered reasoning for portfolio decisions

**Architecture**:
```
Data Layer → Analyzer → Prompt Builder → Claude API → Response Parser → Validator → Dashboard
```

**LLM Used**: Claude API (Anthropic)
- Model: Claude Opus 4.5 (`claude-opus-4-5-20251101`)
- Temperature: 0.3 (consistent reasoning)
- Max tokens: 2000
- Cost estimate: $10-20/month for weekly usage

**Sequential Cash Flow Logic**:
- AI calculates expected proceeds from SELL actions
- Proceeds accumulate into available cash for subsequent BUY actions
- Formula: `proceeds = (quantity × current_price) - transaction_fee`
- Validation tracks running cash balance across action sequence

**Prompt Structure**:
```
CONTEXT:
- Strategy principles (from config file)
- Current portfolio state (consolidated positions with lots)
- Market analysis (rankings, news themes, technicals)
- Price context (30-day vs SPY benchmark)
- Earnings calendar (trading restrictions)
- Material events (if detected for holdings)
- Regulatory constraints (30-day FIFO rule)
- Ongoing narratives (from previous analysis)

TASK:
Analyze and recommend specific actions (BUY/SELL/HOLD) with reasoning

OUTPUT FORMAT:
Structured JSON with actions, reasoning, risks, confidence, narrative_updates
```

**Strategy Principles** (Balanced Pragmatist):
```
REGULATORY CONSTRAINT (IMMUTABLE):
- Minimum 30-day hold from purchase (no exceptions)
- FIFO: Oldest lot must be 30+ days before ANY position sale
- Lot-based tracking: Each purchase is a separate lot

EARNINGS PROXIMITY RULES (IMMUTABLE):
- DO NOT sell within 3 days before earnings (gap risk)
- DO NOT buy within 7 days before earnings (volatility risk)
- These rules override other considerations

STRATEGY PHILOSOPHY:
- Investment horizon: 3-6 months (medium-term)
- Position limit: Max 3 stocks simultaneously
- Entry criteria: Top 3 fundamental rank + technical timing + cost consideration
- Exit criteria: After 30 days, consider stop-loss (-10%), profit target (+20%),
  ranking deterioration (drops below #6), or major negative catalyst
- Transaction cost filter: Only swap if net benefit > $50 after fees
- Portfolio optimization: Equal weight preferred, concentrate if high conviction
```

**Output Format**:
```json
{
  "actions": [
    {
      "type": "SELL|BUY|HOLD",
      "ticker": "MSFT",
      "amount": "1.5 shares | $500",
      "reasoning": "Detailed explanation including lot-level analysis",
      "expected_proceeds": 650.00,
      "cash_source": "MSFT sale proceeds"
    }
  ],
  "overall_strategy": "Portfolio-level thinking summary",
  "risk_warnings": ["Warning 1", "Warning 2"],
  "confidence": "HIGH|MEDIUM|LOW",
  "narrative_updates": {
    "MSFT": {
      "add": [],
      "update": [],
      "resolve": []
    }
  }
}
```

---

### 2.4 Material Events Detection

**Purpose**: Automatically detect when material events affect holdings and provide deep analysis

**Tier 1 Material Events** (triggers deep analysis):
1. **Earnings Results**: Reported within last 2 days
2. **Regulatory Actions**: HIGH frequency (4+ articles in 14 days) or major announcement
3. **Leadership Changes**: CEO, CFO, or founder departure
4. **Major M&A Activity**: Company being acquired or making major acquisition
5. **Guidance Changes**: Mid-quarter warnings or pre-announcements

**Deep Analysis Framework**:
```
Section A: Event Context
- What happened, when, initial market reaction

Section B: Position Context
- Your holdings, entry price, P&L, days held, portfolio weight

Section C: Thesis Validation
- Original investment case
- What validates thesis (✓)
- What contradicts thesis (✗)
- Overall status: VALIDATED | PARTIALLY VALIDATED | INVALIDATED

Section D: Decision Framework
- Option A: EXIT (reasoning, expected outcome, risks)
- Option B: HOLD (reasoning, expected outcome, risks)

Section E: Clear Recommendation
- Recommended action with rationale
- Confidence level
```

**Display Priority**: Material Events section appears FIRST in output when events detected

---

### 2.5 Action Dashboard

**Purpose**: Present recommendations clearly to user

**Output Medium**: Terminal (command-line text output)

**Display Sections** (in order):
1. **Material Events** (if detected): Deep analysis for holdings with events
2. **Portfolio Status**: Consolidated positions with lot breakdown, P&L, lock status
3. **Market Snapshot**: Top-ranked stocks with scores, P/E, RSI, earnings
4. **Entry Opportunities**: Top 3 stocks not held with entry signals
5. **Recent News**: Clustered themes by ticker with frequency
6. **Price Context**: 30-day performance vs SPY benchmark
7. **Earnings Calendar**: Upcoming earnings with trading restrictions
8. **AI Recommendations**: Specific actions with reasoning
9. **Risk Warnings**: Potential downsides, timing concerns

**Formatting**:
- ASCII tables for structured data
- Color coding: Green (positive/sellable), Red (negative/locked), Yellow (warnings)
- Tree-style lot breakdown for multi-lot positions:
  ```
  MSFT     2.5   478.08   433.50   -9.3%    PARTIAL_LOCK
    ├─ Lot 1: 1.5 @ 507.60 (73d, -14.6%)  SELLABLE
    └─ Lot 2: 1.0 @ 434.00 (0d, -0.1%)    LOCKED
  ```
- Icons: [+] (valid), [X] (invalid), [!] (warning)
- Clear sections with headers and dividers

---

### 2.6 Execution Confirmation

**Purpose**: Update portfolio state after manual trades

**FIFO Sell Processing**:
- Lots consumed oldest-first (FIFO order)
- Partial lot consumption reduces quantity
- Full lot consumption removes the lot
- Position removed if all lots consumed

**Workflow**:
```bash
$ python -m src.advisor confirm

What did you execute?
> sold MSFT 1.5 shares at 433.50 on 2026-02-07
✓ Recorded: MSFT Lot 1 closed (1.5 shares consumed via FIFO)
  Remaining: 1.0 shares in Lot 2

> bought NVDA 2 shares at 185.00 on 2026-02-07
✓ Recorded: NVDA Lot 2 added (locked until March 9)

Portfolio updated successfully.
```

**Updates**:
- FIFO lot consumption for sells
- Add new lot to existing position for buys (or create new position)
- Recalculate available cash
- Update `last_updated` timestamp

---

### 2.7 Narrative Memory

**Purpose**: Track ongoing themes and context across runs

**Storage**: `narratives.json` (gitignored, user-specific)

**Schema**:
```json
{
  "version": "1.0",
  "last_updated": "2026-02-07T10:30:00Z",
  "stocks": {
    "MSFT": {
      "active_narratives": [
        {
          "theme": "regulatory_risk",
          "first_seen": "2025-12-15",
          "last_updated": "2026-02-07",
          "summary": "DOJ investigation ongoing",
          "sentiment": "negative",
          "status": "unresolved",
          "materiality": "high"
        }
      ],
      "resolved_narratives": []
    }
  }
}
```

**AI Integration**:
- Narratives loaded and passed to AI in prompt
- AI can add, update, or resolve narratives
- Resolved narratives pruned after 30 days
- Maximum 5 active narratives per stock

---

## 3. User Workflows

### 3.1 Initial Setup (One-time)

**Step 1: Install dependencies**
```bash
pip install yfinance anthropic feedparser pandas python-dotenv requests
```

**Step 2: Configure API keys**
Create `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

**Step 3: Define watchlist**
Create `config.json`:
```json
{
  "watchlist": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX", "AMD", "CRWV"],
  "monthly_budget": 400,
  "transaction_fee": 1,
  "max_positions": 3,
  "stop_loss_percent": -10,
  "profit_target_percent": 20,
  "min_hold_days": 30
}
```

**Step 4: Initialize portfolio**
Edit `portfolio.json` with current positions (lot-based format):
```json
{
  "positions": [],
  "cash_available": 500.00,
  "last_updated": "2026-02-07"
}
```

**Step 5: Test run**
```bash
$ python -m src.advisor
[Validates setup, shows recommendations]
```

---

### 3.2 Monthly Investment Routine

**Trigger**: 1st of month, new capital available

```bash
$ python -m src.advisor
```

**Program flow**:
1. Load portfolio and configuration
2. Check for legacy format, auto-migrate if needed
3. Fetch market data (prices, fundamentals, technicals, news, earnings)
4. Calculate 30-day price context vs SPY
5. Detect material events for holdings
6. Generate market context with consolidated positions
7. Build AI prompt with all context
8. Send to Claude API, parse response
9. Validate actions against constraints
10. Display full dashboard

**User actions**:
1. Review material events analysis (if any)
2. Review recommendations and reasoning
3. Check broker for current prices
4. Execute trades manually in broker
5. Confirm executions back to program

**Time investment**: 10-15 minutes total

---

### 3.3 Mid-Month Position Check

**Trigger**: Ad-hoc (market volatility, news event, anxiety)

```bash
$ python -m src.advisor check
```

**Program shows**:
- Current P&L per position
- Lock status with lot breakdown
- Recent news themes
- Quick assessment: "Hold all" or "Flag concern"
- Upcoming earnings dates

**Time investment**: 2-3 minutes

---

### 3.4 Portfolio Migration (One-time)

**Trigger**: Upgrading from legacy flat format

```bash
$ python -m src.advisor migrate
```

**Process**:
1. Detects legacy format (positions without `lots` key)
2. Creates backup (`portfolio.json.backup`)
3. Groups positions by ticker
4. Creates lot-based structure
5. Validates migration
6. Reports result

**Note**: Auto-migration also runs on any advisor command if legacy format detected.

---

## 4. System Architecture

### 4.1 Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     USER                                │
│  (Command line interaction)                             │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              MAIN ORCHESTRATOR                          │
│  (advisor.py)                                           │
│  - Parse commands (check, confirm, migrate)             │
│  - Coordinate components                                │
│  - Handle FIFO sell processing                          │
│  - Handle lot-aware buy processing                      │
└───┬─────────────┬─────────────┬─────────────┬───────────┘
    │             │             │             │
    ▼             ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
│ DATA    │  │ ANALYSIS│  │ AI       │  │ OUTPUT   │
│ LAYER   │  │ LAYER   │  │ AGENT    │  │ LAYER    │
└─────────┘  └─────────┘  └──────────┘  └──────────┘
    │             │             │             │
    ▼             ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
│ UTILS   │  │ EVENT   │  │ NARRATIVE│  │          │
│ (lots)  │  │ DETECTOR│  │ MANAGER  │  │          │
└─────────┘  └─────────┘  └──────────┘  └──────────┘
```

### 4.2 Module Structure

```
App/
├── src/
│   ├── advisor.py           # Main entry point, CLI commands
│   ├── data_collector.py    # Market data fetching
│   ├── analyzer.py          # Ranking, technicals, context generation
│   ├── ai_agent.py          # LLM integration, prompt building
│   ├── display.py           # Terminal output formatting
│   ├── event_detector.py    # Material event detection
│   └── utils.py             # Helpers, lot consolidation, validation
├── config/
│   ├── portfolio.json       # User positions (gitignored)
│   ├── config.json          # Watchlist, settings
│   ├── strategy.txt         # Strategy principles for LLM
│   └── narratives.json      # Narrative storage (gitignored)
└── tests/
    ├── test_analyzer.py
    ├── test_ai_agent.py
    └── ...
```

---

### 4.3 Data Layer

**Module**: `data_collector.py`

**Key Functions**:
```python
def fetch_all_market_data(tickers: list) -> dict
def get_fundamentals(tickers: list) -> dict
def scan_news_enhanced(tickers: list, days: int = 14) -> dict
def calculate_earnings_proximity(earnings_date_str: str) -> dict
```

**Enhanced News Collection**:
- 14-day lookback window
- 25 articles fetched per ticker
- Theme clustering (earnings, regulatory, M&A, leadership, product)
- Source quality filtering (tier 1-3)
- Headline deduplication (80% similarity threshold)
- Frequency classification (HIGH/MEDIUM/LOW)

---

### 4.4 Analysis Layer

**Module**: `analyzer.py`

**Key Functions**:
```python
def calculate_rankings(fundamentals: dict) -> dict
def calculate_technicals(prices: dict) -> dict
def check_fifo_eligibility(positions: list) -> dict
def calculate_price_context(tickers: list, market_data: dict) -> dict
def analyze_exit_signals(position: dict, current_price: float, config: dict) -> dict
def generate_market_context(market_data: dict, portfolio: dict, config: dict) -> dict
```

**Price Context Calculation**:
- 30-day stock return
- 30-day SPY benchmark return
- Relative performance (stock - SPY)
- Trend classification: OUTPERFORMING | NEUTRAL | UNDERPERFORMING

**Lot-Aware Exit Signals**:
- Stop-loss checked per lot (individual cost basis)
- Profit target checked per lot
- Returns lot-specific signals: "STOP LOSS Lot 1: 1.5 shares @ $507.60, -14.6%"

---

### 4.5 AI Agent Layer

**Module**: `ai_agent.py`

**Key Functions**:
```python
def build_prompt(context: dict, strategy: str, narratives: dict, market_data: dict) -> str
def get_recommendation(context: dict, strategy: str, narratives: dict, market_data: dict) -> dict
def parse_recommendation(response: str) -> dict
def validate_actions(actions: list, context: dict) -> list
```

**Prompt Sections**:
1. Strategy principles
2. Regulatory constraints (FIFO, earnings blackout)
3. Current holdings (consolidated with lot breakdown)
4. Sequential cash flow instructions
5. Market rankings
6. Entry opportunities
7. Price context (30-day vs SPY)
8. Earnings calendar
9. Material events (if detected)
10. Ongoing narratives
11. Recent news themes
12. Response format instructions

**Validation Features**:
- Tracks running cash (SELL proceeds available for BUY)
- Validates against sellable_quantity (not total)
- Checks earnings proximity restrictions
- Verifies cash sufficiency including fees

---

### 4.6 Event Detection Layer

**Module**: `event_detector.py`

**Key Functions**:
```python
def detect_material_events(context: dict, market_data: dict) -> list
def build_event_analysis(events: list, context: dict, market_data: dict) -> list
```

**Event Types Detected**:
- EARNINGS: Reported within 2 days
- REGULATORY: HIGH frequency legal/regulatory news
- LEADERSHIP: CEO/CFO departure keywords
- MA: Merger/acquisition news
- GUIDANCE: Mid-quarter warnings

---

### 4.7 Utils Layer

**Module**: `utils.py`

**Key Functions**:
```python
def load_portfolio() -> dict  # Auto-migrates legacy format
def save_portfolio(portfolio: dict) -> None
def consolidate_positions(raw_positions: list, min_hold_days: int = 30) -> list
def validate_portfolio(portfolio: dict) -> list
def validate_position(position: dict) -> list
def validate_lot(lot: dict) -> list
def is_lot_based_format(portfolio: dict) -> bool
def migrate_portfolio_to_lots(portfolio: dict) -> dict
```

**Consolidation Output**:
```python
{
    "ticker": "MSFT",
    "total_quantity": 2.5,
    "average_cost": 478.08,
    "sellable_quantity": 1.5,
    "locked_quantity": 1.0,
    "lock_status": "PARTIAL_LOCK",
    "lots": [
        {
            "quantity": 1.5,
            "purchase_price": 507.60,
            "purchase_date": "2025-11-18",
            "days_held": 73,
            "is_sellable": True,
            "unlock_date": None
        },
        {
            "quantity": 1.0,
            "purchase_price": 434.00,
            "purchase_date": "2026-01-30",
            "days_held": 8,
            "is_sellable": False,
            "unlock_date": "2026-03-01"
        }
    ]
}
```

---

### 4.8 Output Layer

**Module**: `display.py`

**Key Functions**:
```python
def display_full_dashboard(portfolio: dict, context: dict, recommendation: dict) -> None
def display_portfolio_status(portfolio: dict, context: dict) -> None
def display_market_snapshot(context: dict) -> None
def display_material_events(context: dict, recommendation: dict) -> None
def display_recommendations(recommendation: dict) -> None
def display_price_context(context: dict) -> None
def display_earnings_calendar(context: dict) -> None
```

**Display Features**:
- Tree-style lot breakdown (├─ / └─ prefixes)
- Color-coded lock status
- Lot-specific exit signals
- Consolidated position summary
- Material events with recommendations

---

## 5. Command-Line Interface

**Main command**:
```bash
$ python -m src.advisor [command]
```

**Commands**:

| Command | Description | Example |
|---------|-------------|---------|
| (none) | Full analysis and recommendations | `python -m src.advisor` |
| `check` | Quick portfolio status check | `python -m src.advisor check` |
| `confirm` | Confirm executed trades | `python -m src.advisor confirm` |
| `migrate` | Migrate legacy portfolio format | `python -m src.advisor migrate` |
| `--help` | Show usage information | `python -m src.advisor --help` |

---

## 6. Technical Specifications

### 6.1 Technology Stack

**Language**: Python 3.10+

**Core Libraries**:
- `yfinance` (0.2.40+): Market data, fundamentals, earnings calendar
- `anthropic` (0.40.0+): Claude API (Opus 4.5)
- `feedparser` (6.0.11+): RSS news parsing
- `pandas` (2.2.0+): Data manipulation
- `python-dotenv` (1.0.0+): Environment variable management
- `requests` (2.31.0+): HTTP requests
- `difflib`: Headline deduplication (fuzzy matching)

**Development Tools**:
- `pytest`: Testing framework (67+ tests)
- `git`: Version control

---

### 6.2 Performance Considerations

**Data Fetching**:
- Parallel fetching for watchlist stocks
- 14-day news lookback with filtering
- Expected time: 30-60 seconds total

**LLM API**:
- Response time: 5-15 seconds
- Cost per run: ~$0.02-0.05 (Opus 4.5)
- Monthly cost estimate: $10-20 (for weekly usage)

**Total execution time**: 45-90 seconds per run

---

## 7. Risk Management

### 7.1 System Safeguards

| Safeguard | Implementation |
|-----------|----------------|
| FIFO enforcement | Lots sold oldest-first automatically |
| 30-day lock | Validation prevents selling locked lots |
| Earnings blackout | 3-day sell / 7-day buy restrictions |
| Cash flow validation | SELL proceeds tracked for BUY validation |
| Position validation | No duplicate tickers in positions array |
| Auto-backup | Portfolio backed up before migration |

### 7.2 Compliance

- FIFO tracking for regulatory compliance
- Lot-level cost basis for tax reporting
- No automated execution (user always confirms trades)
- Audit trail available (transaction history in JSON)

---

## 8. Success Metrics

### 8.1 Product Success Criteria

**Correctness**:
- [x] Portfolio displays correct number of stocks (not duplicate entries)
- [x] Sellability validation is accurate (FIFO-aware)
- [x] AI receives consolidated position data
- [x] Material events detected for holdings
- [x] Earnings restrictions enforced

**Usability**:
- [x] Clear lot breakdown when needed
- [x] Weighted average cost displayed
- [x] 30-day price context vs benchmark
- [x] Deep analysis for material events

---

## 9. Implemented Change Requests

### CR001: Cash Flow Logic Enhancement
- Sequential cash flow calculation in AI prompt
- SELL proceeds available for subsequent BUY actions
- Running cash validation in action validator

### CR002: Enhanced News Analysis with Price Context
- 14-day news lookback with clustering
- Source quality filtering (tier 1-3)
- 30-day price context vs SPY benchmark
- Narrative storage and updates

### CR003: Earnings Calendar Integration
- Automatic earnings date detection
- 3-day sell restriction / 7-day buy restriction
- Earnings calendar display section

### CR004: Enhanced Google RSS News Collection
- Targeted material event queries
- Headline deduplication (80% similarity)
- Noise pattern filtering

### CR005: Position Event Monitor & Deep Analysis
- Material event detection for holdings
- Deep analysis templates (earnings, regulatory, leadership, M&A)
- Hold vs exit decision framework
- Event-specific recommendations

### CR006: Lot-Based Position Tracking
- Lot-based portfolio data model
- Runtime consolidation (total_quantity, average_cost, sellable_quantity)
- FIFO sell processing
- Lot-aware validation and display
- Auto-migration from legacy format

---

## 10. Approval & Sign-off

**Product Owner**: Tobes
**Date**: February 7, 2026
**Status**: v2.0 - Reflects Current Implementation

---

**END OF PRODUCT REQUIREMENT**
