# Portfolio AI Agent - Product Requirement

**Version**: 3.0
**Date**: March 27, 2026
**Author**: Tobes (Product Owner)
**Previous Version**: 2.0 (February 7, 2026)

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-25 | Initial product proposal |
| 2.0 | 2026-02-07 | Incorporated CR001-CR006 implementations |
| 3.0 | 2026-03-27 | Incorporated CR007-CR013 implementations |

---

## 1. Executive Summary

### 1.1 Product Vision
An AI-powered portfolio advisor that analyzes tech stock positions and prescribes specific buy/sell/hold/wait actions based on fundamental analysis, technical signals, news events, earnings calendar, and regulatory constraints. The system uses LLM reasoning (Claude API) to make intelligent, personalised decisions that balance ranking quality, transaction costs, timing, investor profile, and portfolio-level capital efficiency.

### 1.2 Target User
- **User**: Individual retail investor (Tobes)
- **Investment style**: Medium-term (3-6 months), fundamental-driven
- **Capital**: $300/month deposit budget (new external capital — not part of existing cash)
- **Universe**: Top 10 technology stocks (watchlist configurable)
- **Regulatory constraint**: Must hold positions minimum 30 days (FIFO lot-based)

### 1.3 Core Value Proposition
Eliminates emotional decision-making and analysis paralysis by providing clear, personalised, reasoned recommendations that respect regulatory constraints, detect material events affecting holdings, track ongoing themes across runs, deploy capital efficiently, and adapt to the investor's individual risk profile.

---

## 2. Product Features

### 2.1 Portfolio State Management

**Purpose**: Single source of truth for current positions with lot-based tracking

**Capabilities**:
- Stores positions with lot-based structure (each ticker once, multiple lots underneath)
- Tracks per-lot: quantity, purchase_price (per-share), purchase_date
- Calculates at runtime: total_quantity, average_cost, sellable_quantity, lock_status
- Supports FIFO (First-In-First-Out) sell order
- Displays: lock status (SELLABLE, PARTIAL_LOCK, LOCKED), unlock calendar
- Persists: JSON file format (`portfolio.json`) — gitignored (personal financial data)
- Auto-migration from legacy flat format to lot-based format

**Data Schema**:
```json
{
  "positions": [
    {
      "ticker": "NVDA",
      "lots": [
        {
          "quantity": 1.0,
          "purchase_price": 191.83,
          "purchase_date": "2026-01-30",
          "notes": "Initial position"
        }
      ]
    }
  ],
  "cash_available": 1275.78,
  "last_updated": "2026-03-20"
}
```

**Note on `purchase_price`**: This is the **per-share** price paid. Total cost = `quantity × purchase_price`. When confirming a buy, always enter the per-share price, not the total cost.

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

---

### 2.3 AI Recommendation Engine

**Purpose**: LLM-powered reasoning for portfolio decisions

**Architecture**:
```
Data Layer → Analyzer → Prompt Builder → Claude API (or Manual Mode) → Response Parser → Validator → Dashboard
```

**LLM Used**: Claude API (Anthropic)
- Model: Claude Opus 4.5 (`claude-opus-4-5-20251101`)
- Temperature: 0.3 (consistent reasoning)
- Max tokens: 4000
- Retry logic: 3 attempts with exponential backoff

**Manual Mode** (cost-saving alternative to API):
When run with `--manual` flag, the program builds the full prompt and saves it to `App/output/prompt_YYYYMMDD_HHMMSS.md`, then waits for the user to paste the LLM JSON response into the terminal. All downstream steps (parse, validate, display, record) run identically.

**Prompt Architecture** (four-layer strategy):

```
INVESTOR PROFILE (active values from config.json)

STRATEGY PRINCIPLES (from strategy.txt):
  Layer 0 — Investor Profile definitions
  Layer 1 — Hard Constraints (non-negotiable)
  Layer 2 — Principles (judgment guides)
  Layer 3 — Reasoning Frameworks (A/B/C/D/E + Signal Hierarchy)

REGULATORY CONSTRAINT
CURRENT PORTFOLIO
LOCK STATUS
STOCK RANKINGS
ENTRY OPPORTUNITIES
RECENT NEWS
PRICE CONTEXT
EARNINGS CALENDAR
ONGOING NARRATIVES
CONSTRAINTS
SEQUENTIAL CASH FLOW CALCULATION
MATERIAL EVENTS (if detected)
YOUR TASK
PORTFOLIO VS NARRATIVE CONFLICT CHECK
NARRATIVE BOUNDARY RULE
NARRATIVE UPDATES instructions
RESPONSE FORMAT
```

**Strategy Architecture — Three-Layer Judgment Model** (CR009-CR013):

*Layer 0 — Investor Profile* (from config.json, injected at prompt top):
Personalises all recommendations for this specific investor across 6 dimensions:
risk_tolerance, ai_thesis_conviction, lock_period_comfort, cash_buffer_preference,
portfolio_significance, drawdown_behaviour. See Section 2.9 for details.

*Layer 1 — Hard Constraints* (non-negotiable):
- 30-day FIFO hold rule (regulatory)
- Maximum 3 positions
- No single position > 50% of portfolio (adjusted by profile significance)
- Hard stop-loss at -10% from entry price
- Profit target exit at +20%
- No BUY within 7 days before earnings
- No SELL within 3 days before earnings

*Layer 2 — Principles* (guide judgment, not conditions to check):
1. Price drop ≠ thesis broken
2. Cost of inaction is real
3. Conviction before swap
4. Macro ≠ stock-specific risk
5. Averaging down is a valid tool
6. Patience beats FOMO
7. Concentrated conviction (2-3 positions)
8. Capital efficiency (monthly deposit is external, not existing cash)
9. Cash drag is a risk, not a safe default (>50% cash requires justification)

*Layer 3 — Reasoning Frameworks*:
- **Signal Hierarchy**: Priority 1 (hard constraints) → 2 (material events) → 3 (rank) → 4 (thesis) → 5 (portfolio) → 6 (RSI/technicals). Higher priority always wins silently.
- **Framework A**: Should I exit? (why falling / thesis signals / loss level / opportunity cost)
- **Framework B**: Should I average down? (root cause / thesis change / risk-reward / cash + scale)
- **Framework C**: Should I enter? (rank / material signal first / then RSI / portfolio fit / capital)
- **Framework D**: Is this news material or noise? (fundamental impact / source count / market reaction)
- **Framework E**: Is my cash position justified? (triggers at >50% cash; options: average down, enter despite RSI, or hold with written justification + opportunity cost stated)

**Action Types**:
| Type | Meaning |
|------|---------|
| BUY | Enter or add to a position |
| SELL | Exit or reduce a position |
| HOLD | You own this stock — keep it |
| WAIT | You do not own this stock — entry deferred, conditions not yet right |

**Sequential Cash Flow Logic**:
- AI calculates expected proceeds from SELL actions first
- Proceeds accumulate into available cash for subsequent BUY actions
- Formula: `proceeds = (quantity × current_price) - transaction_fee`
- Validation tracks running cash balance across action sequence

**Narrative Boundary Rule** (CR011):
Narratives track market intelligence only. They must never contain: cost basis, stop-loss price levels, share counts, trade execution confirmations, or cash calculations. These belong exclusively in the portfolio data block. If narrative and portfolio block conflict, portfolio block is always correct.

**Output Format**:
```json
{
  "actions": [
    {
      "type": "SELL|BUY|HOLD|WAIT",
      "ticker": "NVDA",
      "amount": "1 shares | $300",
      "reasoning": "Detailed explanation including signal hierarchy and profile influence",
      "expected_proceeds": 178.56,
      "cash_source": "existing cash"
    }
  ],
  "overall_strategy": "Portfolio-level thinking summary",
  "risk_warnings": ["Warning 1"],
  "confidence": "HIGH|MEDIUM|LOW",
  "narrative_updates": {
    "NVDA": {
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
2. **Regulatory Actions**: HIGH frequency (4+ articles) or major announcement
3. **Leadership Changes**: CEO, CFO, or founder departure
4. **Major M&A Activity**: Company being acquired or making major acquisition
5. **Guidance Changes**: Mid-quarter warnings or pre-announcements

**Signal Hierarchy Integration** (CR010):
Material fundamental events are **Priority 2** in the signal hierarchy — they override technical timing signals (RSI, support levels). A major positive catalyst means enter even if RSI > 50. A major negative catalyst means do not enter/hold even if RSI appears oversold.

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

---

### 2.6 Execution Confirmation

**Purpose**: Update portfolio state after manual trades

**Confirmation Echo** (CR bug fix):
Before writing any BUY to portfolio, the system displays a summary and asks for explicit confirmation:
```
About to record: BUY NVDA 2 share(s) @ $179.00/share
Total cost: $358.00  |  Cash after: $917.78
Confirm? (y/n):
```
This prevents the common mistake of entering total cost instead of per-share price.

**Workflow**:
```bash
$ python -m src.advisor confirm

What did you execute?
> bought NVDA 2 shares at 179.00 on 2026-03-20
  About to record: BUY NVDA 2 share(s) @ $179.00/share
  Total cost: $358.00  |  Cash after: $917.78
  Confirm? (y/n): y
✓ Recorded: NVDA Lot 2 added (locked until April 19)

> sold MSFT 1.5 shares at 433.50 on 2026-02-07
✓ Recorded: MSFT Lot 1 closed via FIFO

> set cash 666
✓ Cash set to $666.00 (was $917.78)

> add cash 100
✓ Added $100.00 cash. New balance: $766.00

> done
Portfolio saved.
```

**Cash Commands**:
| Command | Effect |
|---------|--------|
| `add cash AMOUNT` | Increments cash by AMOUNT |
| `set cash AMOUNT` | Sets cash to exact AMOUNT (use for currency conversion corrections) |

**FIFO Sell Processing**:
- Lots consumed oldest-first
- Partial lot consumption reduces quantity
- Full lot consumption removes the lot
- Position removed if all lots consumed

---

### 2.7 Narrative Memory

**Purpose**: Track ongoing market themes and context across runs

**Storage**: `narratives.json` (gitignored, user-specific)

**Boundary Rule** (CR011):
Narratives contain market intelligence only:
- ✅ News events and significance
- ✅ Analyst price targets and ratings
- ✅ Thesis assessment (strengthening/intact/weakening)
- ✅ Market price levels as external reference (e.g. "trading near $178 support")
- ✅ RSI and technical observations as market data
- ❌ Cost basis or average cost
- ❌ Stop-loss price levels (derived from cost basis)
- ❌ Position size or share counts
- ❌ Trade execution confirmations
- ❌ Cash balance or proceeds calculations

---

### 2.8 Recommendation Ledger & Simulation (CR007)

**Purpose**: Record every recommendation with portfolio/market snapshots for performance tracking and learning

**Storage**: `recommendations_ledger.json` (gitignored, personal financial data)

**What is Recorded** (each run):
```json
{
  "id": "rec_20260320_172442",
  "timestamp": "2026-03-20T17:24:42",
  "outcome": "pending",
  "portfolio_snapshot": {
    "positions": [...],
    "cash_available": 1275.78,
    "total_value": 1454.34
  },
  "market_snapshot": {
    "top_3": ["NVDA", "MSFT", "LITE"],
    "rankings": {...},
    "benchmark_spy_30d": -3.86
  },
  "recommendation": {
    "actions": [...],
    "overall_strategy": "...",
    "confidence": "HIGH",
    "risk_warnings": [...]
  }
}
```

**Simulation Command** (`python -m src.advisor sim`):
Evaluates past recommendations by comparing against current prices. Shows: what was recommended, what the price was then, what it is now, and what the outcome would have been.

**Outcome Tracking**:
| Outcome | Meaning |
|---------|---------|
| pending | Not yet confirmed or evaluated |
| accepted | User executed all recommended trades |
| partial | User executed some trades |
| skipped | User did not execute; recommendation expired |

---

### 2.9 Investor Profile (CR013)

**Purpose**: Personalise all recommendations for this specific investor rather than a generic moderate-risk investor

**Storage**: `config.json` under `investor_profile` key

**Configuration**:
```json
"investor_profile": {
  "risk_tolerance": "Moderate",
  "ai_thesis_conviction": "High",
  "lock_period_comfort": "Medium",
  "cash_buffer_preference": "Moderate",
  "portfolio_significance": "Meaningful",
  "drawdown_behaviour": "Hold through"
}
```

**Dimensions and Valid Values**:

| Dimension | Options | Effect |
|-----------|---------|--------|
| risk_tolerance | Conservative / Moderate / Aggressive | Framework B max cash%, Framework E trigger%, Framework C RSI threshold |
| ai_thesis_conviction | Low / Medium / High | Weighting of sector thesis in Framework B and E Option B |
| lock_period_comfort | Low / Medium / High | Averaging down scale reduction when macro is deteriorating |
| cash_buffer_preference | Minimal / Moderate / Substantial | Framework E trigger threshold (50% / 50% / 65%) |
| portfolio_significance | Discretionary / Meaningful / Primary | Concentration limit (50% / 40% / 35%) |
| drawdown_behaviour | Hold through / Tighten gradually / Exit early | Framework A early exit trigger levels |

**How It Works**:
- Values are injected at the top of the prompt as the `INVESTOR PROFILE` block
- Layer 0 in `strategy.txt` defines what each value means and how it modifies framework thresholds
- When profile moderates a recommendation, the LLM must state this explicitly in reasoning:
  *"Given your Conservative risk tolerance, I am recommending 1 share rather than 3 which market signals alone would suggest."*
- Layer 1 hard constraints are never overridden by profile

**Changing Your Profile**:
Edit `App/config/config.json` and change any value in `investor_profile`. Takes effect on next run.

---

## 3. User Workflows

### 3.1 Initial Setup (One-time)

**Step 1: Install dependencies**
```bash
pip install yfinance anthropic feedparser pandas python-dotenv requests
```

**Step 2: Configure API key**
Create `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

**Step 3: Configure watchlist and profile**
Edit `App/config/config.json`:
```json
{
  "watchlist": ["MSFT", "GOOGL", "AMZN", "NVDA", "LITE", "NBIS", "CRWV"],
  "monthly_budget": 300,
  "transaction_fee": 1,
  "max_positions": 3,
  "stop_loss_percent": -10,
  "profit_target_percent": 20,
  "min_hold_days": 31,
  "investor_profile": {
    "risk_tolerance": "Moderate",
    "ai_thesis_conviction": "High",
    "lock_period_comfort": "Medium",
    "cash_buffer_preference": "Moderate",
    "portfolio_significance": "Meaningful",
    "drawdown_behaviour": "Hold through"
  }
}
```

**Step 4: Initialize portfolio**
Create `App/config/portfolio.json`:
```json
{
  "positions": [],
  "cash_available": 500.00,
  "last_updated": "2026-03-01"
}
```

**Step 5: Test run**
```bash
cd App && python -m src.advisor
```

---

### 3.2 Regular Investment Analysis

**Standard mode** (uses Claude API):
```bash
cd App && python -m src.advisor
```

**Manual mode** (saves API cost — paste prompt into Claude.ai yourself):
```bash
cd App && python -m src.advisor --manual
```
1. Program builds full prompt, saves to `App/output/prompt_YYYYMMDD_HHMMSS.md`
2. Copy prompt content into Claude.ai (or any LLM)
3. Copy the JSON response back into the terminal
4. Press Ctrl+Z then Enter (Windows) or Ctrl+D (Mac/Linux)
5. Program continues: validates, displays dashboard, records to ledger

**Program flow** (both modes):
1. Load portfolio, config, strategy, narratives
2. Fetch market data (prices, fundamentals, technicals, news, earnings)
3. Generate market context with consolidated positions
4. Build AI prompt including investor profile and all context sections
5. Get recommendation (API or manual)
6. Validate actions against constraints
7. Update and save narratives
8. Display full dashboard
9. Record recommendation to ledger

---

### 3.3 Trade Confirmation

After executing trades manually in your broker:
```bash
cd App && python -m src.advisor confirm
```

Key commands:
- `bought TICKER QTY shares at PRICE on DATE` — enter per-share price (not total cost)
- `sold TICKER QTY shares at PRICE on DATE`
- `add cash AMOUNT` — adds to cash balance
- `set cash AMOUNT` — sets cash to exact value (use for AUD→USD conversion corrections)
- `done` — saves and exits

---

### 3.4 Portfolio Status Check

Ad-hoc check during market volatility or news events:
```bash
cd App && python -m src.advisor check
```

Shows: current P&L, lock status, recent news themes, upcoming earnings.

---

### 3.5 Recommendation Simulation

Review past recommendation performance:
```bash
cd App && python -m src.advisor sim          # Simulate most recent
cd App && python -m src.advisor sim --list   # List all recorded recommendations
cd App && python -m src.advisor sim --summary # Statistics
cd App && python -m src.advisor sim rec_20260320_172442  # Specific recommendation
```

---

## 4. System Architecture

### 4.1 Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│                        USER                              │
│  (Command line: run / check / confirm / sim / review)    │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│                MAIN ORCHESTRATOR                         │
│  (advisor.py)                                            │
│  - Parse commands and flags (--manual)                   │
│  - Coordinate all components                             │
│  - Handle FIFO sell and lot-aware buy processing         │
│  - Route: API mode or manual mode                        │
└──────┬──────────┬──────────┬──────────┬──────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌─────────┐ ┌──────────┐ ┌──────────────────┐
│ DATA     │ │ANALYSIS │ │ AI AGENT │ │ RECOMMENDATIONS  │
│ LAYER    │ │ LAYER   │ │          │ │ MANAGER          │
└──────────┘ └─────────┘ └──────────┘ └──────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌─────────┐ ┌──────────┐ ┌──────────────────┐
│ UTILS    │ │ EVENT   │ │NARRATIVE │ │ OUTPUT / DISPLAY │
│ (lots)   │ │DETECTOR │ │ MANAGER  │ │                  │
└──────────┘ └─────────┘ └──────────┘ └──────────────────┘
```

### 4.2 Module Structure

```
App/
├── src/
│   ├── advisor.py               # Main entry point, CLI commands
│   ├── data_collector.py        # Market data fetching
│   ├── analyzer.py              # Ranking, technicals, context generation
│   ├── ai_agent.py              # LLM integration, prompt building, manual mode
│   ├── display.py               # Terminal output formatting
│   ├── event_detector.py        # Material event detection
│   ├── narrative_manager.py     # Narrative CRUD and formatting
│   ├── recommendations_manager.py # Ledger recording, simulation, trade matching
│   └── utils.py                 # Helpers, lot consolidation, validation
├── config/
│   ├── portfolio.json           # User positions (gitignored)
│   ├── config.json              # Watchlist, settings, investor profile
│   ├── strategy.txt             # Strategy principles for LLM (Layers 0-3)
│   ├── narratives.json          # Narrative storage (gitignored)
│   └── recommendations_ledger.json  # Recommendation history (gitignored)
└── output/
    └── prompt_YYYYMMDD_HHMMSS.md    # Manual mode prompt files (gitignored)
```

---

### 4.3 AI Agent Layer

**Module**: `ai_agent.py`

**Key Functions**:
```python
def build_prompt(context, strategy, narratives, market_data) -> str
def get_recommendation(context, strategy, narratives, market_data, manual_mode=False) -> dict
def parse_recommendation(response) -> dict
def validate_actions(actions, context) -> list
def _format_investor_profile(config) -> str
def _format_positions(positions) -> str
def _format_rankings(rankings) -> str
def _format_opportunities(opportunities) -> str
def _format_lock_status(lock_status) -> str
def _format_news(news) -> str
def _format_price_context(context) -> str
def _format_earnings_calendar(context) -> str
def _format_holdings_for_cashflow(positions, transaction_fee) -> str
```

**Manual Mode Flow**:
1. `build_prompt()` runs as normal
2. Prompt written to `output/prompt_YYYYMMDD_HHMMSS.md`
3. User pastes LLM response to stdin
4. `parse_recommendation()` + `validate_actions()` run as normal
5. All downstream steps (display, ledger, narratives) unchanged

---

### 4.4 Recommendations Manager

**Module**: `recommendations_manager.py`

**Key Functions**:
```python
def record_recommendation(portfolio, context, recommendation, market_data) -> str
def match_trade_to_recommendations(trade, portfolio) -> None
def simulate_recommendation(rec_id, current_prices) -> dict
def list_recommendations() -> list
def get_ledger_summary() -> dict
```

**Storage**: `recommendations_ledger.json` (gitignored)
- Max 100 entries (auto-pruned)
- Each entry: snapshot of portfolio state, market state, recommendation, outcome tracking

---

## 5. Command-Line Interface

**Main command**:
```bash
cd App && python -m src.advisor [command] [flags]
```

**Commands**:

| Command | Description |
|---------|-------------|
| *(none)* | Full analysis and AI recommendations |
| `check` | Quick portfolio status check |
| `confirm` | Record executed trades |
| `sim` | Simulate past recommendations |
| `sim --list` | List all recorded recommendations |
| `sim --summary` | Show ledger statistics |
| `review` | AI-assisted strategy review (20+ recommendations required) |
| `init` | Initialize portfolio (first-time setup) |
| `migrate` | Convert legacy portfolio to lot-based format |
| `help` | Show usage information |

**Flags**:

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--manual` | run (default) | Skip API call — save prompt to file, read response from stdin |

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
- `difflib`: Headline deduplication

### 6.2 Data Files

| File | Gitignored | Purpose |
|------|-----------|---------|
| `.env` | ✅ | API key |
| `config/portfolio.json` | ✅ | Current positions |
| `config/narratives.json` | ✅ | Narrative memory |
| `config/recommendations_ledger.json` | ✅ | Recommendation history |
| `output/` | ✅ | Manual mode prompt files |
| `config/config.json` | ❌ | Settings (no sensitive data) |
| `config/strategy.txt` | ❌ | Strategy principles |

### 6.3 Performance

- Data fetch: 30-60 seconds
- API call: 5-15 seconds (Opus 4.5, 4000 max tokens)
- Manual mode: No API cost; total time depends on user
- Monthly API cost estimate: ~$5-15 for weekly usage (Opus 4.5)

---

## 7. Risk Management

### 7.1 System Safeguards

| Safeguard | Implementation |
|-----------|----------------|
| FIFO enforcement | Lots sold oldest-first automatically |
| 30-day lock | Validation prevents selling locked lots |
| Earnings blackout | 3-day sell / 7-day buy restrictions enforced |
| Cash flow validation | SELL proceeds tracked for BUY validation |
| BUY confirmation echo | Shows per-share price, total cost, cash after — user confirms before write |
| Portfolio vs narrative conflict | LLM instructed to detect and correct at each run |
| Position validation | No duplicate tickers; per-share price enforcement |

### 7.2 Compliance

- FIFO tracking for regulatory compliance
- Lot-level cost basis for tax reporting
- No automated execution (user always confirms trades)
- Recommendation audit trail in ledger (gitignored, local only)

---

## 8. Success Metrics

**Correctness**:
- [x] Portfolio displays correct consolidated positions (not duplicate entries)
- [x] Sellability validation is accurate (FIFO-aware)
- [x] AI receives consolidated position data including lot breakdown
- [x] Material events detected for holdings with deep analysis
- [x] Earnings restrictions enforced
- [x] Monthly budget correctly treated as external capital (not existing cash)
- [x] WAIT action distinguishes deferred entry from existing holding
- [x] Profile settings demonstrably change recommendation sizing

**Decision Quality**:
- [x] Signal hierarchy prevents RSI from blocking strong fundamental signals
- [x] Framework E triggers when cash > 50% and evaluates deployment options
- [x] Narratives never contain portfolio state (cost basis, stop-loss, share counts)
- [x] Averaging down correctly evaluated using Framework B + cash scale guidance

---

## 9. Implemented Change Requests

### CR001: Cash Flow Logic Enhancement
Sequential cash flow calculation in AI prompt. SELL proceeds available for subsequent BUY actions. Running cash validation in action validator.

### CR002: Enhanced News Analysis with Price Context
14-day news lookback with clustering. Source quality filtering. 30-day price context vs SPY benchmark. Narrative storage and updates.

### CR003: Earnings Calendar Integration
Automatic earnings date detection. 3-day sell restriction / 7-day buy restriction. Earnings calendar display section.

### CR004: Enhanced Google RSS News Collection
Targeted material event queries. Headline deduplication (80% similarity). Noise pattern filtering.

### CR005: Position Event Monitor & Deep Analysis
Material event detection for holdings. Deep analysis templates. Hold vs exit decision framework.

### CR006: Lot-Based Position Tracking
Lot-based portfolio data model. Runtime consolidation. FIFO sell processing. Auto-migration from legacy format.

### CR007: Recommendation Ledger & Simulation
Auto-record every recommendation with portfolio/market snapshots. Simulation command to evaluate past advice against current prices. Outcome tracking (pending/accepted/partial/skipped). Trade matching when user confirms execution.

### CR008: Monthly Budget Misinterpretation Fix
Renamed `monthly_budget` label to `Monthly deposit budget` in prompt. Added explicit rule: this is external capital not in the portfolio; never subtract from or add to available cash. Only surface in risk_warnings when confidence=HIGH and existing cash is insufficient.

### CR009: Judgment-Based Advisor Strategy Redesign
Replaced rules-engine strategy.txt with three-layer judgment architecture. Layer 1 (hard constraints), Layer 2 (8 guiding principles), Layer 3 (4 named reasoning frameworks A-D). Introduced WAIT action type to correctly represent deferred entries vs held positions.

### CR010: Signal Hierarchy for Conflicting Inputs
Added explicit Signal Hierarchy to Layer 3. Material fundamental events (Priority 2) explicitly override technical timing (Priority 6 — RSI). Framework C updated: check material signal before checking RSI.

### CR011: Narrative/Portfolio State Separation
Added NARRATIVE BOUNDARY RULE to prompt. Narratives must never contain cost basis, stop-loss levels, share counts, or trade confirmations. Added PORTFOLIO VS NARRATIVE CONFLICT CHECK instruction. Tightened narrative update wording to "market intelligence only."

### CR012: Cash Efficiency — Portfolio-Level Capital Deployment
Added Principle 9 (cash drag is a risk) to Layer 2. Added Framework E (Is my cash position justified?) to Layer 3 — triggers at >50% cash. Added scale guidance step to Framework B: how much to average down based on current cash/equity ratio.

### CR013: Personal Investor Profile
Added Layer 0 (investor profile definitions) to strategy.txt. Added `investor_profile` object to config.json with 6 dimensions and defaults. Added `_format_investor_profile()` helper to ai_agent.py. Profile values injected as first prompt section. LLM must state explicitly when profile moderates a recommendation.

### CR (Confirm improvements): BUY Confirmation Echo + Set Cash Command
Added confirmation echo before writing any BUY (shows per-share price, total cost, cash after). Added `set cash AMOUNT` command to `confirm` for direct cash override (handles AUD→USD conversion corrections). Updated confirm help text.

---

## 10. Approval & Sign-off

**Product Owner**: Tobes
**Date**: March 27, 2026
**Status**: v3.0 — Reflects Current Implementation (CR007-CR013 + confirm improvements)

---

**END OF PRODUCT REQUIREMENT**
