# Portfolio AI Agent - Product Proposal

**Version**: 1.0  
**Date**: January 25, 2026  
**Author**: Tobes (Product Owner)

---

## 1. Executive Summary

### 1.1 Product Vision
An AI-powered portfolio advisor that analyzes tech stock positions and prescribes specific buy/sell/hold actions based on fundamental analysis, technical signals, news events, and regulatory constraints. The system uses LLM reasoning (Claude API) to make intelligent decisions that balance ranking quality, transaction costs, timing, and portfolio optimization.

### 1.2 Target User
- **User**: Individual retail investor (Tobes)
- **Investment style**: Medium-term (3-6 months), fundamental-driven
- **Capital**: $300-500/month
- **Universe**: Top 10 technology stocks (FAANG + MSFT, NVDA, TSLA, etc.)
- **Regulatory constraint**: Must hold positions minimum 30 days (FIFO)

### 1.3 Core Value Proposition
Eliminates emotional decision-making and analysis paralysis by providing clear, reasoned recommendations that respect regulatory constraints and optimize for long-term portfolio quality.

---

## 2. Product Features

### 2.1 Portfolio State Management
**Purpose**: Single source of truth for current positions

**Capabilities**:
- Stores positions: ticker, quantity, purchase price, purchase date
- Calculates: days held, P&L, FIFO eligibility (30+ days old)
- Displays: lock status, unlock calendar
- Persists: JSON file format (`portfolio.json`)

**Data Schema**:
```json
{
  "positions": [
    {
      "ticker": "GOOGL",
      "quantity": 28,
      "purchase_price": 155.00,
      "purchase_date": "2025-12-01",
      "notes": "Optional user notes"
    }
  ],
  "cash_available": 450.00,
  "last_updated": "2026-01-22"
}
```

---

### 2.2 Market Intelligence Engine
**Purpose**: Collect and analyze market data for decision-making

**Data Sources** (all free tier):
- **yfinance**: Stock prices, fundamentals (P/E, revenue, FCF), technical data
- **Google News RSS**: Headlines for news scanning
- **Financial Modeling Prep** (optional): Deep fundamental ratios

**Data Collected**:
- Current prices (OHLCV)
- Fundamental metrics: P/E ratio, revenue growth, free cash flow, market cap
- Technical indicators: RSI, support/resistance levels
- News headlines: Last 7 days for 10 tracked stocks
- Earnings calendar: Upcoming earnings dates

**Processing**:
- Calculate fundamental ranking score (1-10) for each stock
- Identify technical entry signals (oversold, support levels)
- Flag material news events
- Compute transaction costs for potential swaps

---

### 2.3 AI Recommendation Engine
**Purpose**: LLM-powered reasoning for portfolio decisions

**Architecture**:
```
Data Layer → Prompt Builder → Claude API → Response Parser → Action Dashboard
```

**LLM Used**: Claude API (Anthropic)
- Model: Claude Sonnet 4 or later
- Cost estimate: $10-20/month for weekly usage

**Prompt Structure**:
```
CONTEXT:
- Strategy principles (from config file)
- Current portfolio state (positions, lock status)
- Market analysis (rankings, news, technicals)
- Regulatory constraints (30-day FIFO rule)

TASK:
Analyze and recommend specific actions (BUY/SELL/HOLD) with reasoning

OUTPUT FORMAT:
Structured JSON with actions, reasoning, risks, confidence
```

**Strategy Principles** (Balanced Pragmatist):
```
REGULATORY CONSTRAINT (IMMUTABLE):
- Minimum 30-day hold from purchase (no exceptions)
- FIFO: Oldest lot must be 30+ days before ANY position sale

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
      "ticker": "GOOGL",
      "amount": "all shares | specific $ amount",
      "reasoning": "Detailed explanation of why this action"
    }
  ],
  "overall_strategy": "Portfolio-level thinking summary",
  "risk_warnings": ["Warning 1", "Warning 2"],
  "confidence": "HIGH|MEDIUM|LOW"
}
```

---

### 2.4 Action Dashboard
**Purpose**: Present recommendations clearly to user

**Output Medium**: Terminal (command-line text output)

**Display Sections**:
1. **Portfolio Status**: Current positions, P&L, lock status, ranking
2. **Market Snapshot**: Top 3 ranked stocks, your holdings' positions
3. **News Alerts**: Material events in last 7 days
4. **Recommended Actions**: Specific steps with reasoning (priority ordered)
5. **Risk Warnings**: Potential downsides, timing concerns
6. **Summary**: One-line takeaway

**Formatting**:
- ASCII tables for structured data
- Color coding: Green (positive), Red (negative), Yellow (warnings)
- Icons: ✓ (good), ⚠️ (warning), 🚨 (urgent)
- Clear sections with separators

---

### 2.5 Execution Confirmation
**Purpose**: Update portfolio state after manual trades

**Workflow**:
```bash
$ python advisor.py confirm

What did you execute?
> sold GOOGL 28 shares at 107.50 on 2026-02-01
✓ Recorded: GOOGL position closed

> bought AMZN 27 shares at 126.50 on 2026-02-01
✓ Recorded: AMZN position opened (locked until March 3)

Portfolio updated successfully.
```

**Updates**:
- Remove sold positions from `portfolio.json`
- Add new positions with purchase date (for FIFO tracking)
- Recalculate available cash
- Update `last_updated` timestamp

---

## 3. User Workflows

### 3.1 Initial Setup (One-time)

**Step 1: Install dependencies**
```bash
pip install yfinance anthropic feedparser pandas
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
  "watchlist": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX", "AMD", "INTC"],
  "monthly_budget": 400,
  "transaction_fee": 10,
  "max_positions": 3
}
```

**Step 4: Initialize portfolio**
Edit `portfolio.json` with current positions (or start empty):
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
  "cash_available": 450.00,
  "last_updated": "2026-01-22"
}
```

**Step 5: Test run**
```bash
$ python advisor.py
[Validates setup, shows recommendations]
```

---

### 3.2 Monthly Investment Routine

**Trigger**: 1st of month, new capital available

```bash
$ python advisor.py
```

**Program flow**:
1. Fetch market data (30-60 seconds)
2. Calculate rankings
3. Scan news
4. Send context to Claude API
5. Parse recommendation
6. Display action dashboard

**User actions**:
1. Review recommendations
2. Verify reasoning makes sense
3. Check broker for current prices
4. Execute trades manually in broker
5. Confirm executions back to program

**Time investment**: 10-15 minutes total

---

### 3.3 Mid-Month Position Check

**Trigger**: Ad-hoc (market volatility, news event, anxiety)

```bash
$ python advisor.py check
```

**Program shows**:
- Current P&L
- Lock status (days until unlock)
- Recent news
- Quick assessment: "Hold all" or "Flag concern"

**User actions**:
- Review status
- Decide if any action needed (usually none)
- Continue monitoring

**Time investment**: 2-3 minutes

---

### 3.4 Emergency Event Response

**Trigger**: Major news (CEO resignation, regulatory action, earnings miss)

```bash
$ python advisor.py check
```

**Program provides**:
- Emergency analysis of news impact
- Recommendation: immediate action or wait
- Options comparison (sell now vs hold through)
- Risk assessment

**User actions**:
- Evaluate AI reasoning
- Decide on action
- Execute if needed
- Confirm to system

**Time investment**: 5-10 minutes

---

### 3.5 Manual Adjustment (Error Correction)

**Trigger**: Discovered error in portfolio.json

**Method**: Direct file edit
```bash
$ nano portfolio.json
[Edit quantity, price, or date]
$ python advisor.py
[Validates changes, continues normally]
```

**Validation**: Program checks JSON syntax and data validity on every run

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
│  - Parse commands                                       │
│  - Coordinate components                                │
│  - Handle errors                                        │
└───┬─────────────┬─────────────┬─────────────┬───────────┘
    │             │             │             │
    ▼             ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
│ DATA    │  │ ANALYSIS│  │ AI       │  │ OUTPUT   │
│ LAYER   │  │ LAYER   │  │ AGENT    │  │ LAYER    │
└─────────┘  └─────────┘  └──────────┘  └──────────┘
```

### 4.2 Data Layer

**Module**: `data_collector.py`

**Responsibilities**:
- Fetch stock prices via yfinance
- Retrieve fundamental metrics
- Scan news via Google RSS
- Load portfolio state from JSON
- Load configuration

**Key Functions**:
```python
def fetch_market_data(tickers: list) -> dict
def get_fundamentals(tickers: list) -> dict
def scan_news(tickers: list, days: int = 7) -> dict
def load_portfolio() -> dict
def load_config() -> dict
```

**Error Handling**:
- Retry on API failures (3 attempts)
- Cache data locally to reduce API calls
- Validate data completeness before proceeding

---

### 4.3 Analysis Layer

**Module**: `analyzer.py`

**Responsibilities**:
- Calculate fundamental ranking scores
- Compute technical indicators (RSI, support/resistance)
- Determine FIFO eligibility (days held vs 30-day minimum)
- Calculate transaction costs for potential actions
- Identify entry/exit signals

**Key Functions**:
```python
def calculate_rankings(fundamentals: dict) -> dict
def calculate_technicals(prices: dict) -> dict
def check_fifo_eligibility(positions: list) -> dict
def calculate_swap_cost(from_ticker, to_ticker, portfolio) -> float
def generate_market_context(data: dict) -> dict
```

**Ranking Algorithm**:
```python
score = (
    0.3 * revenue_growth_score +
    0.25 * fcf_score +
    0.25 * pe_valuation_score +
    0.2 * momentum_score
)
# Normalize to 0-10 scale
# Rank stocks 1-10 by score
```

---

### 4.4 AI Agent Layer

**Module**: `ai_agent.py`

**Responsibilities**:
- Build prompt from market context + portfolio state + strategy rules
- Call Claude API
- Parse JSON response
- Validate recommendations against hard constraints
- Handle API errors

**Key Functions**:
```python
def build_prompt(context: dict, portfolio: dict, config: dict) -> str
def call_claude_api(prompt: str) -> str
def parse_recommendation(response: str) -> dict
def validate_actions(actions: list, portfolio: dict) -> bool
```

**Prompt Template**:
```python
PROMPT = f"""
You are a portfolio advisor managing a tech stock portfolio.

STRATEGY PRINCIPLES:
{config['strategy_principles']}

REGULATORY CONSTRAINT:
- Minimum 30-day hold (FIFO)
- Cannot sell positions held < 30 days under ANY circumstance

CURRENT PORTFOLIO:
{format_portfolio(portfolio)}

MARKET ANALYSIS:
{format_market_context(context)}

CONSTRAINTS:
- Position limit: {config['max_positions']}
- Transaction cost: ${config['transaction_fee']} per trade
- Available capital: ${portfolio['cash_available']}

YOUR TASK:
Recommend specific actions (BUY/SELL/HOLD) with clear reasoning.

RESPONSE FORMAT (JSON):
{{
  "actions": [
    {{"type": "SELL|BUY|HOLD", "ticker": "...", "amount": "...", "reasoning": "..."}},
    ...
  ],
  "overall_strategy": "Brief portfolio-level explanation",
  "risk_warnings": ["...", "..."],
  "confidence": "HIGH|MEDIUM|LOW"
}}
"""
```

**API Configuration**:
```python
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2000,
    temperature=0.3,  # Lower temp for more consistent reasoning
    messages=[
        {"role": "user", "content": prompt}
    ]
)
```

---

### 4.5 Output Layer

**Module**: `display.py`

**Responsibilities**:
- Format recommendations for terminal display
- Generate ASCII tables
- Apply color coding
- Create summary sections

**Key Functions**:
```python
def display_portfolio_status(portfolio: dict, rankings: dict)
def display_market_snapshot(rankings: dict, news: dict)
def display_recommendations(actions: list)
def display_risk_warnings(warnings: list)
def format_table(data: list) -> str
```

**Example Output Format**:
```python
def display_recommendations(actions):
    print("\n" + "="*60)
    print("RECOMMENDED ACTIONS")
    print("="*60 + "\n")
    
    for i, action in enumerate(actions, 1):
        print(f"ACTION {i}: {action['type']} {action['ticker']}")
        print("-"*60)
        print(f"Reasoning:\n{action['reasoning']}\n")
```

---

### 4.6 Storage Layer

**Files**:
- `portfolio.json`: Current positions and cash
- `config.json`: Watchlist, budget, strategy settings
- `.env`: API keys (never committed to git)
- `strategy.txt`: Detailed strategy principles for LLM

**Backup Strategy**:
- Manual: Copy `portfolio.json` before each run
- Git: Track portfolio history (optional)
- Export: Generate CSV of all positions (future feature)

---

## 5. Data Requirements

### 5.1 Input Data

**Stock Price Data** (yfinance):
```python
{
  "GOOGL": {
    "current_price": 173.50,
    "open": 171.20,
    "high": 174.30,
    "low": 170.80,
    "volume": 28500000,
    "52_week_high": 185.40,
    "52_week_low": 121.30
  }
}
```

**Fundamental Data** (yfinance):
```python
{
  "GOOGL": {
    "pe_ratio": 25.3,
    "market_cap": 2150000000000,
    "revenue_ttm": 307500000000,
    "revenue_growth_yoy": 0.08,
    "free_cash_flow": 69800000000,
    "earnings_date": "2026-02-28"
  }
}
```

**Technical Indicators** (calculated):
```python
{
  "GOOGL": {
    "rsi_14": 52.3,
    "sma_20": 170.50,
    "sma_50": 165.20,
    "support_level": 168.00,
    "resistance_level": 178.00
  }
}
```

**News Data** (Google RSS):
```python
{
  "GOOGL": [
    {
      "title": "Google announces AI breakthrough",
      "date": "2026-01-20",
      "url": "https://...",
      "sentiment": "positive"  # future: auto-detect
    }
  ]
}
```

---

### 5.2 Output Data

**Recommendation Structure**:
```json
{
  "timestamp": "2026-01-22T10:30:00Z",
  "actions": [
    {
      "priority": 1,
      "type": "SELL",
      "ticker": "GOOGL",
      "amount": "all",
      "expected_proceeds": 4856.00,
      "reasoning": "Ranking dropped from #3 to #6, regulatory headwinds, held 52 days (eligible), lock in +8% profit before catalyst risk",
      "confidence": "HIGH"
    },
    {
      "priority": 2,
      "type": "BUY",
      "ticker": "AMZN",
      "amount": 5300.00,
      "expected_shares": 42,
      "reasoning": "Top 3 rank (#3), RSI oversold at 38, use GOOGL proceeds + new capital, no earnings for 3 weeks",
      "confidence": "MEDIUM-HIGH"
    }
  ],
  "overall_strategy": "Rotate from weakening GOOGL to strong AMZN, maintain NVDA (still top-ranked)",
  "risk_warnings": [
    "GOOGL antitrust ruling next week could swing ±15%",
    "AMZN will be 48% of portfolio (concentration risk)"
  ],
  "portfolio_impact": {
    "before": {"positions": 2, "cash": 450},
    "after": {"positions": 2, "cash": 6}
  },
  "confidence": "MEDIUM-HIGH"
}
```

---

## 6. Technical Specifications

### 6.1 Technology Stack

**Language**: Python 3.10+

**Core Libraries**:
- `yfinance` (0.2.40+): Market data
- `anthropic` (0.40.0+): Claude API
- `feedparser` (6.0.11+): RSS news parsing
- `pandas` (2.2.0+): Data manipulation
- `python-dotenv` (1.0.0+): Environment variable management
- `requests` (2.31.0+): HTTP requests

**Development Tools**:
- `black`: Code formatting
- `pytest`: Testing framework (future)
- `git`: Version control

---

### 6.2 File Structure

```
portfolio-ai-agent/
├── advisor.py                 # Main entry point
├── data_collector.py          # Market data fetching
├── analyzer.py                # Ranking & technical analysis
├── ai_agent.py                # LLM integration
├── display.py                 # Terminal output formatting
├── utils.py                   # Helper functions
├── requirements.txt           # Python dependencies
├── .env                       # API keys (gitignored)
├── .gitignore
├── README.md
├── config.json                # Watchlist, settings
├── portfolio.json             # Current positions (gitignored)
├── strategy.txt               # Strategy principles for LLM
└── tests/                     # Unit tests (future)
    └── test_analyzer.py
```

---

### 6.3 Command-Line Interface

**Main command**:
```bash
$ python advisor.py [command] [options]
```

**Commands**:

| Command | Description | Example |
|---------|-------------|---------|
| (none) | Run full analysis and recommendations | `python advisor.py` |
| `check` | Quick portfolio status check | `python advisor.py check` |
| `confirm` | Confirm executed trades | `python advisor.py confirm` |
| `init` | Initialize portfolio (first-time setup) | `python advisor.py init` |
| `--help` | Show usage information | `python advisor.py --help` |

**Future commands** (not MVP):
| Command | Description |
|---------|-------------|
| `adjust` | Manual position correction |
| `history` | View transaction history |
| `backtest` | Simulate strategy on historical data |

---

### 6.4 Error Handling

**API Failures**:
```python
try:
    data = yfinance.download(tickers)
except Exception as e:
    logger.error(f"Failed to fetch data: {e}")
    # Retry with exponential backoff
    # Fall back to cached data if available
    # If critical, exit with clear error message
```

**Invalid Portfolio**:
```python
def validate_portfolio(portfolio):
    errors = []
    
    for pos in portfolio['positions']:
        if pos['quantity'] <= 0:
            errors.append(f"{pos['ticker']}: quantity must be positive")
        if not is_valid_date(pos['purchase_date']):
            errors.append(f"{pos['ticker']}: invalid date format")
    
    if errors:
        print("Portfolio validation failed:")
        for error in errors:
            print(f"  ❌ {error}")
        sys.exit(1)
```

**LLM Response Parsing**:
```python
try:
    recommendation = json.loads(response)
    validate_recommendation_schema(recommendation)
except json.JSONDecodeError:
    logger.error("LLM returned invalid JSON")
    # Extract JSON from markdown code blocks
    # Retry with simplified prompt
    # Fall back to manual decision suggestion
```

---

### 6.5 Performance Considerations

**Data Fetching**:
- Cache market data for 1 hour (avoid repeated API calls)
- Parallel fetching for 10 stocks (reduce latency)
- Expected time: 20-40 seconds total

**LLM API**:
- Response time: 5-15 seconds
- Cost per run: ~$0.02-0.05
- Monthly cost estimate: $10-20 (for weekly usage)

**Total execution time**: 30-60 seconds per run

---

## 7. Risk Management

### 7.1 System Risks

| Risk | Mitigation |
|------|------------|
| **API downtime** | Cache last successful data, allow manual override |
| **LLM hallucination** | Validate recommendations against hard constraints, require user confirmation |
| **Data accuracy** | Cross-validate critical data across multiple sources |
| **Portfolio drift** | Regular reconciliation prompts, audit mode (future) |
| **Cost overruns** | Set API budget alerts, cache aggressively |

---

### 7.2 Investment Risks

| Risk | Mitigation |
|------|------------|
| **Bad recommendations** | User always makes final decision, system shows reasoning for review |
| **Locked in bad position** | 30-day constraint is regulatory (unavoidable), AI accounts for this in entry decisions |
| **Missing opportunities** | Weekly check-ins, news monitoring |
| **Concentration risk** | Max 3 positions limit, AI considers diversification |
| **Transaction costs** | $50 minimum benefit threshold for swaps |

---

### 7.3 Compliance

**Regulatory**:
- ✅ System enforces 30-day minimum hold (hard-coded constraint)
- ✅ FIFO tracking for tax compliance
- ✅ No automated execution (user always confirms trades)
- ✅ Audit trail available (transaction history in JSON)

**Privacy**:
- ✅ All data stored locally (no cloud sync)
- ✅ API keys in `.env` (gitignored)
- ✅ Portfolio data in gitignored files

---

## 8. Success Metrics

### 8.1 Product Success Criteria

**Adoption metrics**:
- [ ] Successfully run for 3 consecutive months
- [ ] Zero missed monthly investment decisions
- [ ] User confidence in recommendations > 80%

**Quality metrics**:
- [ ] Recommendation reasoning clarity: User can explain AI's logic
- [ ] False positive rate: < 10% of recommendations regretted
- [ ] System uptime: > 95% (accounting for API failures)

**Efficiency metrics**:
- [ ] Time per monthly decision: < 15 minutes (vs 2+ hours manual)
- [ ] Data freshness: < 1 hour old at decision time
- [ ] Execution speed: < 60 seconds total runtime

---

### 8.2 Investment Performance (Informational Only)

**Not primary success criteria**, but tracked for learning:
- Portfolio return vs S&P 500
- Win rate (profitable positions / total positions)
- Average hold period vs target (3-6 months)
- Transaction cost as % of portfolio value

**Note**: System optimizes for process quality, not guaranteed returns.

---

## 9. Implementation Plan

### 9.1 Phase 1: MVP (Weeks 1-2)

**Goal**: Working end-to-end system with manual portfolio initialization

**Deliverables**:
- [ ] Data collector (yfinance + Google RSS)
- [ ] Basic ranking algorithm
- [ ] Claude API integration
- [ ] Terminal output display
- [ ] Portfolio JSON structure
- [ ] Confirmation workflow

**Definition of Done**:
- User can run `python advisor.py` and get a recommendation
- User can confirm trades and update portfolio
- System validates 30-day FIFO constraint

---

### 9.2 Phase 2: Refinement (Weeks 3-4)

**Goal**: Improve quality and reliability

**Deliverables**:
- [ ] Enhanced ranking algorithm (tune weights)
- [ ] Better error handling
- [ ] Caching layer for API calls
- [ ] Improved prompt engineering for LLM
- [ ] News sentiment analysis (basic)
- [ ] Risk warning generation

**Definition of Done**:
- Recommendations feel high-quality to user
- System handles API failures gracefully
- Runtime < 60 seconds consistently

---

### 9.3 Phase 3: Intelligence (Month 2)

**Goal**: More sophisticated analysis

**Deliverables**:
- [ ] Multi-factor ranking (technical + fundamental + momentum)
- [ ] Better news filtering (remove noise)
- [ ] Earnings calendar integration
- [ ] Position unlock calendar view
- [ ] Transaction cost optimization
- [ ] Opportunity queue (track missed buys)

**Definition of Done**:
- AI considers all relevant factors in recommendations
- User rarely questions AI reasoning
- No manual workarounds needed

---

### 9.4 Phase 4: Maturity (Month 3+)

**Goal**: Long-term sustainability and enhancement

**Deliverables**:
- [ ] Backtesting framework (test strategy on historical data)
- [ ] Performance analytics dashboard
- [ ] Transaction history and audit trail
- [ ] Manual adjustment commands (`adjust`, `remove`)
- [ ] Portfolio reconciliation mode
- [ ] Strategy tuning based on results

**Definition of Done**:
- System has been used for 3+ months successfully
- Strategy weights optimized based on backtesting
- Full audit trail available

---

## 10. Future Enhancements (Post-MVP)

### 10.1 Short-term (3-6 months)

- **Multiple strategies**: Test different strategy principles (aggressive vs conservative)
- **Sector rotation**: Expand beyond tech to other sectors
- **Tax optimization**: Consider long-term vs short-term capital gains
- **Alert system**: Email/SMS notifications for urgent events
- **Web dashboard**: Browser-based UI instead of terminal

---

### 10.2 Long-term (6-12 months)

- **Multi-user support**: Track multiple portfolios
- **Broker integration**: Auto-fetch positions from broker API (read-only)
- **Advanced analytics**: Sharpe ratio, max drawdown, correlation analysis
- **Machine learning**: Train custom models for ranking (vs rule-based)
- **Social features**: Share anonymized strategies with other users

---

## 11. Appendices

### Appendix A: Example Strategy Configuration

**File**: `strategy.txt`

```
PORTFOLIO ADVISOR STRATEGY - Balanced Pragmatist

REGULATORY CONSTRAINTS (IMMUTABLE):
- Minimum hold period: 30 days from purchase (no exceptions, even in -50% scenario)
- FIFO rule: When selling, oldest lot must be 30+ days old before ANY sale of that ticker
- This constraint is a feature: prevents emotional short-term reactions

INVESTMENT PHILOSOPHY:
- Horizon: Medium-term (3-6 months typical hold)
- Focus: Fundamental quality over technical timing
- Risk tolerance: Moderate (willing to hold through -10% drawdowns)
- Style: Concentrated conviction (2-3 positions) over diversification

CORE PRINCIPLES:
1. Quality First: Prefer fundamentally strong businesses (top 3 ranked)
2. Cost Conscious: Only swap positions if improvement justifies transaction costs ($50+ net benefit)
3. Patient Capital: Every entry is a 30-90 day commitment, plan accordingly
4. Disciplined Exits: Lock profits at +20%, stop losses at -10% (after min hold period)
5. News Aware: Major negative catalysts override patience (exit when eligible)

POSITION MANAGEMENT:
- Target: 2-3 positions (equal weight unless high conviction)
- Maximum: 3 positions (hard limit, no exceptions)
- Rebalancing frequency: Monthly review, but only act if significant opportunity
- Concentration limit: No single position > 50% of portfolio

ENTRY CRITERIA:
- Fundamental rank: Must be top 3 in watchlist
- Technical timing: Prefer RSI < 50 or at support levels (not mandatory)
- Earnings proximity: Avoid entry within 7 days of earnings (uncertainty)
- News sentiment: No major negative catalysts in past 7 days
- Capital efficiency: Use new monthly capital first, swap only if compelling

EXIT CRITERIA (All subject to 30-day minimum hold):
- Mandatory exits:
  * Stop-loss: -10% from entry price
  * Profit target: +20% from entry price
- Discretionary exits:
  * Ranking drops below #6 AND held > 45 days
  * Major negative catalyst (regulatory, leadership change, earnings miss)
  * Better opportunity available AND swap benefit > $50 after fees
- Hold through:
  * Normal volatility (-5% to +15% range)
  * Temporary ranking weakness if fundamentals intact
  * Market-wide pullbacks (not stock-specific)

SPECIAL CONSIDERATIONS:
- Lock awareness: If all positions locked (<30 days), can only add new position or hold cash
- Opportunity cost: Missing a great entry due to locked capital is acceptable (discipline > FOMO)
- News interpretation: AI chip export restrictions = headline risk (usually hold), 
  CEO resignation = structural risk (usually exit when eligible)
- Earnings strategy: Hold through earnings if rank top 3, exit before earnings if rank #6+
- Cash buffer: If no compelling opportunities (no top 3 stocks with good entry), hold cash until next month

RISK MANAGEMENT:
- Portfolio volatility: Accept -15% drawdowns as normal (don't panic sell)
- Correlation awareness: Avoid 3 highly correlated stocks (e.g., all semiconductor)
- Sector concentration: Tech focus is intentional, but spread across sub-sectors when possible
- Black swan prep: No position > 40% to limit single-stock catastrophic risk

DECISION FRAMEWORK PRIORITIES (in order):
1. Regulatory compliance (30-day FIFO) - non-negotiable
2. Capital preservation (stop-losses, major risk exits)
3. Ranking quality (stay in top 3)
4. Cost efficiency (minimize transaction fees)
5. Timing optimization (technical entry/exit points)
```

---

### Appendix B: Sample Ranking Algorithm

```python
def calculate_fundamental_score(ticker_data):
    """
    Calculate 0-10 fundamental score for a stock
    
    Factors:
    - Revenue growth (30%)
    - Free cash flow strength (25%)
    - P/E valuation (25%)
    - Momentum/trend (20%)
    """
    
    # Revenue growth score (0-10)
    # > 20% = 10, 15-20% = 8, 10-15% = 6, 5-10% = 4, < 5% = 2
    rev_growth = ticker_data['revenue_growth_yoy']
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
    fcf_margin = ticker_data['free_cash_flow'] / ticker_data['revenue_ttm']
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
    pe = ticker_data['pe_ratio']
    if pe < 20:
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
    price = ticker_data['current_price']
    sma_50 = ticker_data['sma_50']
    momentum = (price - sma_50) / sma_50
    
    if momentum > 0.10:
        momentum_score = 10
    elif momentum > 0.05:
        momentum_score = 8
    elif momentum > 0:
        momentum_score = 6
    elif momentum > -0.05:
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


def rank_stocks(stock_data):
    """
    Rank all stocks 1-10 by fundamental score
    """
    scores = {}
    for ticker, data in stock_data.items():
        scores[ticker] = calculate_fundamental_score(data)
    
    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Assign ranks 1-10
    rankings = {}
    for rank, (ticker, score) in enumerate(ranked, start=1):
        rankings[ticker] = {
            'rank': rank,
            'score': score
        }
    
    return rankings
```

---

### Appendix C: Cost Estimate

**Development Costs**: $0 (self-developed)

**Operating Costs** (Monthly):

| Item | Cost | Notes |
|------|------|-------|
| Claude API | $10-20 | ~20-40 calls/month at $0.02-0.05 each |
| Data APIs | $0 | Free tier (yfinance, Google RSS) |
| Compute | $0 | Run locally on personal machine |
| Storage | $0 | Local JSON files |
| **Total** | **$10-20/month** | |

**Annual cost**: ~$120-240

**ROI Calculation**:
- Time saved: 2 hours/month × 12 months = 24 hours/year
- If valued at $50/hour = $1,200 saved
- ROI: ($1,200 - $240) / $240 = 400% return on investment

---

### Appendix D: Glossary

| Term | Definition |
|------|------------|
| **FIFO** | First-In-First-Out: Tax/regulatory rule requiring oldest shares to be sold first |
| **RSI** | Relative Strength Index: Technical indicator (0-100) measuring overbought/oversold conditions |
| **P/E Ratio** | Price-to-Earnings: Valuation metric (stock price / earnings per share) |
| **FCF** | Free Cash Flow: Cash generated after capital expenditures |
| **YoY** | Year-over-Year: Comparing metric to same period last year |
| **TTM** | Trailing Twelve Months: Data from last 12 months |
| **SMA** | Simple Moving Average: Average price over N days |
| **Lock/Locked** | Position held < 30 days, cannot be sold due to regulatory constraint |
| **SELLABLE** | Position held ≥ 30 days, eligible for sale |

---

## 12. Approval & Sign-off

**Product Owner**: Tobes  
**Date**: January 25, 2026  
**Status**: Draft v1.0 - Ready for Review

**Next Steps**:
1. Review and approve this proposal
2. Set up development environment
3. Begin Phase 1 implementation
4. Target first working version: February 8, 2026

---

**END OF PROPOSAL**