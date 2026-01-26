# Change Request: CR002 - Enhanced News Analysis with Price Context

**Date**: January 26, 2026
**Status**: Approved (Implementation Plan Ready)
**Priority**: High
**Affects**: `data_collector.py`, `ai_agent.py`, `analyzer.py`, `narrative_manager.py` (new)
**Implementation Plan**: [CR002-ImplementationPlan.md](../2.%20Plan/CR002-ImplementationPlan.md)

---

## Problem Description

The current news analysis system has three key limitations that reduce AI recommendation quality:

1. **Limited lookback window**: Only scans last 7 days of news, missing important trend context
   - Example: AI sees "regulatory investigation" headline but doesn't know this is an escalating 30-day trend

2. **No noise filtering**: Fetches all articles indiscriminately, including low-quality clickbait
   - Example: "GOOGL stock moves 2%" articles mixed with material news like earnings or regulatory actions

3. **Missing market context**: AI doesn't know if news has been priced in or if stock is weakening
   - Example: December regulatory news caused -8% drop, but AI in January doesn't know if this impact persists or has been absorbed

**Impact**: AI recommendations lack context to distinguish between:
- New material events vs ongoing narratives
- Priced-in news vs unresolved concerns  
- Stock-specific weakness vs market-wide moves
- High-signal events vs noise

**User consequence**: Recommendations may overreact to old news or miss deteriorating trends.

---

## Current Behavior

### News Collection
```python
# Current implementation
def scan_news(tickers, days=7):
    # Fetches 10 articles per ticker from last 7 days
    # Returns raw headlines with dates
    # No filtering, clustering, or context
```

**Output to AI**:
```
GOOGL recent news:
- "DOJ investigation continues" (2026-01-23)
- "Google stock down 2%" (2026-01-22)  
- "Analyst upgrades GOOGL" (2026-01-21)
- "Google launches new feature" (2026-01-20)
...10 articles total
```

### Price Context
- **None** - AI receives current price and P/E but no trend information
- No relative performance vs market
- No indication of stock strength/weakness

### Narrative Memory
- **None** - Each run treats all news as fresh
- No context on ongoing themes
- No "priced in" awareness

---

## Expected Behavior

### Phase 1: Enhanced News Analysis

**Improved news collection**:
```python
def scan_news_enhanced(tickers, days=14):
    # Fetch 20-30 articles per ticker from last 14 days
    # Filter: Remove price movement spam, low-quality sources
    # Cluster: Group similar headlines into themes
    # Rank: Prioritize major outlets (Reuters, Bloomberg, WSJ)
    # Return: Top 5 material themes per stock with context
```

**Output to AI**:
```
GOOGL recent news (14 days, filtered for materiality):

Theme: Regulatory pressure (HIGH frequency - 4 articles)
  - "DOJ antitrust case expands to Android" (Jan 15, Reuters)
  - "EU opens parallel investigation" (Jan 12, Bloomberg)
  Status: ONGOING, unresolved
  Trend: ESCALATING (started Dec 2025, intensifying)
  
Theme: Product launch (LOW frequency - 1 article)
  - "Gemini AI 2.0 announced" (Jan 20, TechCrunch)
  Status: COMPLETE, one-time event
  Trend: ISOLATED

Theme: Earnings (MEDIUM frequency - 2 articles)
  - "Q4 revenue beats estimates" (Jan 18, WSJ)
  Status: COMPLETE, priced in
  Trend: POSITIVE reaction, then faded
```

### Phase 2: Price Context

**Add market performance tracking**:
```python
def calculate_price_context(ticker, market_data):
    # Calculate 30-day stock return
    # Calculate 30-day S&P 500 return (benchmark)
    # Determine relative performance
    # Classify trend: outperforming | neutral | underperforming
```

**Output to AI**:
```
GOOGL price context (30 days):
  Stock return: -8.2%
  Market return (SPY): -3.1%
  Relative performance: -5.1% (UNDERPERFORMING)
  Trend classification: WEAKENING
  
  Interpretation: Stock has underperformed market by 5% over past month,
  suggesting market concern beyond general conditions.
```

### Phase 3: Narrative Memory Storage

**Store ongoing narratives**:
```json
// narratives.json
{
  "GOOGL": {
    "active_narratives": [
      {
        "theme": "regulatory_risk",
        "first_seen": "2025-12-15",
        "last_updated": "2026-01-26",
        "summary": "DOJ + EU antitrust investigations ongoing, expanding scope",
        "sentiment": "negative",
        "status": "unresolved",
        "materiality": "high",
        "initial_market_reaction": "-8% on Dec 15 announcement",
        "is_priced_in": false
      }
    ],
    "price_context": {
      "30d_return": "-8.2%",
      "30d_vs_market": "-5.1%",
      "trend": "underperforming"
    },
    "resolved_narratives": [
      {
        "theme": "earnings_concern",
        "resolved_date": "2026-01-18",
        "resolution": "Q4 beat expectations, concern cleared"
      }
    ]
  }
}
```

**AI receives context on first run**:
```
No prior narratives (first run)
```

**AI receives context on subsequent runs**:
```
ONGOING NARRATIVES (from previous analysis):

GOOGL:
  [ACTIVE] Regulatory investigations (since Dec 2025)
    - This is an ESCALATING situation (expanded Jan 15)
    - Initial impact: -8%, stock has NOT recovered
    - Status: Unresolved, ongoing concern
    
  [RESOLVED] Q4 earnings concerns
    - Resolved: Jan 18 earnings beat
    - No longer a factor in investment case
```

---

## Proposed Solution

### Component 1: Enhanced News Fetching

**File**: `data_collector.py`

**Changes**:

1. **Expand lookback window**
   - Current: 7 days
   - New: 14 days
   - Rationale: Captures weekly trends, not just daily headlines

2. **Increase article volume**
   - Current: 10 articles per ticker
   - New: 20-30 articles per ticker (before filtering)
   - Rationale: Need larger sample to cluster and filter effectively

3. **Add source quality filtering**
   - Priority tier 1: Reuters, Bloomberg, WSJ, CNBC, Financial Times
   - Priority tier 2: TechCrunch, The Verge, MarketWatch
   - Filter out: Motley Fool, Seeking Alpha opinion pieces, generic "stock moves" articles
   - Implementation: Maintain source whitelist/scoring

4. **Add headline clustering**
   - Group articles by keyword similarity
   - Example: All "DOJ", "antitrust", "investigation" → "regulatory_risk" theme
   - Use simple keyword matching (no ML needed for MVP)
   - Return 1 representative article per cluster + article count

5. **Add frequency detection**
   - Count articles per theme over 14-day window
   - Classify: HIGH (5+ articles), MEDIUM (2-4), LOW (1 article)
   - Use to distinguish trends vs isolated events

**New function signature**:
```python
def scan_news_enhanced(tickers, days=14, max_articles=25):
    """
    Scan news with clustering and filtering
    
    Returns:
    {
      "GOOGL": {
        "themes": [
          {
            "name": "regulatory_pressure",
            "headline": "DOJ expands antitrust investigation",
            "date": "2026-01-15",
            "source": "Reuters",
            "article_count": 4,
            "frequency": "HIGH",
            "sentiment": "negative",
            "urls": [...]
          }
        ]
      }
    }
    """
```

---

### Component 2: Price Context Calculation

**File**: `analyzer.py`

**New function**:
```python
def calculate_price_context(ticker, market_data, benchmark="SPY"):
    """
    Calculate 30-day performance vs market
    
    Returns:
    {
      "30d_return": -0.082,  # -8.2%
      "30d_vs_market": -0.051,  # -5.1% underperformance
      "trend": "underperforming",  # outperforming | neutral | underperforming
      "interpretation": "Stock weakening relative to market"
    }
    """
    
    # Fetch 30-day historical prices for ticker and SPY
    # Calculate returns
    # Determine relative performance
    # Classify trend:
    #   - outperforming: relative > +3%
    #   - underperforming: relative < -3%  
    #   - neutral: within ±3%
```

**Integration**: Call for each ticker in portfolio + top 3 ranked stocks

---

### Component 3: Narrative Storage

**New file**: `narratives.json` (gitignored, user-specific)

**Schema**:
```json
{
  "version": "1.0",
  "last_updated": "2026-01-26T10:30:00Z",
  "stocks": {
    "TICKER": {
      "active_narratives": [
        {
          "theme": "string",
          "first_seen": "YYYY-MM-DD",
          "last_updated": "YYYY-MM-DD",
          "summary": "string",
          "sentiment": "positive|negative|neutral",
          "status": "unresolved|resolved",
          "materiality": "high|medium|low",
          "initial_market_reaction": "string (e.g., '-8%')",
          "is_priced_in": boolean
        }
      ],
      "price_context": {
        "30d_return": "string",
        "30d_vs_market": "string",
        "trend": "outperforming|neutral|underperforming"
      },
      "resolved_narratives": [
        {
          "theme": "string",
          "resolved_date": "YYYY-MM-DD",
          "resolution": "string"
        }
      ]
    }
  }
}
```

**Management**:
- Created automatically on first run if missing
- Updated after each AI recommendation
- Pruned: Remove resolved narratives older than 30 days
- Limit: Max 5 active narratives per stock (prevent bloat)

---

### Component 4: AI Prompt Enhancement

**File**: `ai_agent.py`

**Additions to prompt**:

1. **Enhanced news section**
```python
RECENT NEWS (14-day analysis, clustered themes):

{for each ticker}
{ticker} - Top material themes:
  
  Theme: {theme_name} ({frequency} frequency - {article_count} articles)
    Representative: "{headline}" ({date}, {source})
    Status: {ONGOING/COMPLETE}
    Trend: {ESCALATING/STABLE/ISOLATED}
{end for}
```

2. **Price context section**
```python
MARKET PERFORMANCE (30-day context):

{ticker}: {30d_return} (vs market {30d_vs_market})
  Trend: {OUTPERFORMING/NEUTRAL/UNDERPERFORMING}
  Interpretation: {interpretation_text}
```

3. **Narrative context section** (if narratives.json exists)
```python
ONGOING NARRATIVES (from previous analysis):

{ticker}:
  [ACTIVE] {theme} (since {first_seen})
    - Summary: {summary}
    - Initial market reaction: {reaction}
    - Current status: {is_priced_in ? "Priced in" : "Unresolved concern"}
    - Stock trend: {trend}
    
  [RESOLVED] {theme} (resolved {resolved_date})
    - {resolution}
```

4. **Instructions for narrative updates**
```python
YOUR TASK (in addition to recommendations):

After analyzing current conditions, update narratives:

For each stock, determine:
1. Are there NEW material themes to track? (add to active_narratives)
2. Have any ACTIVE themes resolved or changed? (update or move to resolved)
3. Are any narratives stale (>30 days, no new developments)? (mark for removal)

Include in your JSON response:
{
  "actions": [...],
  "narrative_updates": {
    "TICKER": {
      "add": [{new narrative object}],
      "update": [{updated narrative object}],
      "resolve": ["theme_name"]
    }
  }
}
```

---

### Component 5: Narrative Update Handler

**New file**: `narrative_manager.py`

**Functions**:
```python
def load_narratives():
    """Load narratives.json or create empty structure"""
    
def save_narratives(narratives):
    """Save updated narratives to file"""
    
def update_narratives(current_narratives, ai_updates):
    """Apply AI-suggested updates to narrative structure"""
    
def prune_old_narratives(narratives, days=30):
    """Remove resolved narratives older than N days"""
    
def format_narratives_for_prompt(narratives, tickers):
    """Format narratives into prompt text"""
```

**Integration**:
- Load narratives at start of run
- Pass to AI in prompt
- Parse AI's narrative_updates from response
- Apply updates and save to file

---

## Implementation Phases

### Phase 1A: Enhanced News (Week 1) - **PRIORITY**

**Deliverables**:
- [ ] Expand news lookback to 14 days
- [ ] Increase fetch to 25 articles per ticker
- [ ] Implement basic source filtering (tier 1 vs tier 2)
- [ ] Implement simple keyword clustering (group by common terms)
- [ ] Add frequency detection (count articles per theme)
- [ ] Update prompt with enhanced news format

**Testing**:
- Verify clustering groups related articles correctly
- Confirm frequency detection (HIGH/MEDIUM/LOW) is accurate
- Check AI receives cleaner, more contextual news

**Success criteria**:
- AI can distinguish "ongoing trend" from "isolated event"
- Number of articles shown to AI reduced from 100 to ~30 (10 stocks × 3-5 themes)
- News quality subjectively improved (less noise)

---

### Phase 1B: Price Context (Week 1-2)

**Deliverables**:
- [ ] Implement `calculate_price_context()` function
- [ ] Fetch SPY benchmark data
- [ ] Calculate 30-day relative performance
- [ ] Classify trend (outperforming/neutral/underperforming)
- [ ] Add price context section to prompt
- [ ] Display price context in output dashboard

**Testing**:
- Verify calculations: spot-check returns vs broker data
- Confirm relative performance math (stock return - SPY return)
- Test trend classification boundaries (±3%)

**Success criteria**:
- AI knows if stock is strengthening or weakening
- Output shows "GOOGL underperforming market by -5.1%"
- AI reasoning references price trends ("stock has weakened...")

---

### Phase 2: Narrative Storage (Week 3-4)

**Deliverables**:
- [ ] Define `narratives.json` schema
- [ ] Implement `narrative_manager.py` module
- [ ] Update AI prompt to request narrative updates
- [ ] Parse AI narrative_updates from response
- [ ] Apply updates and save to file
- [ ] Add narrative context to prompt (ongoing/resolved themes)

**Testing**:
- Create test narrative, verify it persists across runs
- Update narrative, verify changes saved correctly
- Resolve narrative, verify it moves to resolved_narratives
- Test pruning of old resolved narratives (30+ days)

**Success criteria**:
- Narratives survive across program restarts
- AI references "ongoing since Dec 2025" context
- Resolved narratives automatically archived
- File size stays manageable (<100KB)

---

### Phase 3: Refinement (Week 5+)

**Deliverables**:
- [ ] Improve clustering algorithm (if needed)
- [ ] Add event-specific price reactions to narratives
- [ ] Fine-tune materiality classification
- [ ] Add narrative visualization in output (timeline view)

---

## Data Requirements

### Additional Data Sources

**Already available** (no new dependencies):
- Historical prices: yfinance (already using)
- SPY benchmark: yfinance (add to fetch)
- News: Google RSS (already using)

**New storage**:
- `narratives.json`: Local file, ~10-50KB
- Cached news: Optional temporary cache (reduce API calls)

### API Impact

**News fetching**:
- Current: ~10 requests/run (1 per ticker)
- New: ~10 requests/run (same, just fetch more results per request)
- Impact: Minimal (same request count, slightly larger responses)

**Price data**:
- Current: Fetch current prices only
- New: Fetch 30-day history + SPY
- Impact: +2 additional API calls per run (ticker history + SPY)
- Cost: $0 (yfinance free tier sufficient)

**Claude API**:
- Current: ~800 tokens prompt
- New: ~1200-1500 tokens prompt (enhanced news + narratives)
- Impact: +50% prompt size = +$0.01 per run
- Cost: Still within acceptable range ($10-20/month)

---

## Impact Analysis

### Benefits

**For AI Quality**:
- Distinguishes trends from noise → Better recommendations
- Knows if news is "priced in" → Avoids double-counting
- Has memory of context → More sophisticated reasoning
- Tracks stock strength → Earlier weakness detection

**For User Experience**:
- More confident in AI reasoning (shows context awareness)
- Fewer "where did this come from?" questions
- Clearer understanding of why stocks are ranked as they are
- Better crisis response (AI knows ongoing vs new issues)

**For Investment Outcomes**:
- Earlier detection of deteriorating positions
- Better entry timing (avoid catching falling knives)
- More appropriate reaction to news (major vs minor)
- Reduced emotional decision-making (AI provides rational context)

### Risks

**Complexity**:
- Moderate: Adding 3 new components (news enhancement, price context, narratives)
- Mitigation: Implement in phases, each standalone

**Data accuracy**:
- Price calculations must be correct (affects recommendations)
- Mitigation: Unit tests for performance calculations, manual spot-checks

**Narrative drift**:
- AI might update narratives incorrectly over time
- Mitigation: User can edit narratives.json manually if needed

**Storage bloat**:
- Narratives could grow unbounded
- Mitigation: 30-day pruning, 5-narrative limit per stock

**API costs**:
- Larger prompts = higher costs
- Mitigation: Still well within budget, ~+$5/month maximum

---

## Testing Plan

### Unit Tests

```python
# test_news_clustering.py
def test_cluster_similar_headlines():
    headlines = [
        "DOJ sues Google",
        "DOJ expands Google investigation", 
        "EU probes Google"
    ]
    clusters = cluster_headlines(headlines)
    assert len(clusters) == 1
    assert clusters[0]['theme'] == 'regulatory'

# test_price_context.py  
def test_calculate_relative_performance():
    stock_return = -0.08  # -8%
    market_return = -0.03  # -3%
    context = calculate_price_context(stock_return, market_return)
    assert context['30d_vs_market'] == -0.05
    assert context['trend'] == 'underperforming'

# test_narrative_manager.py
def test_narrative_persistence():
    narrative = create_test_narrative()
    save_narratives({"GOOGL": narrative})
    loaded = load_narratives()
    assert loaded["GOOGL"] == narrative
```

### Integration Tests

1. **Full run with news enhancement**
   - Run program with current portfolio
   - Verify news themes are clustered
   - Check frequency detection
   - Confirm AI receives enhanced format

2. **Full run with price context**
   - Run program with holdings
   - Verify price calculations match broker
   - Check trend classification is reasonable
   - Confirm AI references price trends in reasoning

3. **Narrative lifecycle**
   - First run: Create new narrative
   - Second run: Update existing narrative
   - Third run: Resolve narrative
   - Fourth run: Verify resolved narrative archived

### Manual Validation

- [ ] Compare news themes to manual review of Google News (spot check)
- [ ] Verify price calculations against broker/Yahoo Finance
- [ ] Review AI reasoning quality improvement (subjective assessment)
- [ ] Check narratives.json content makes sense

---

## Acceptance Criteria

**Phase 1A (Enhanced News)** - DONE when:
- [ ] News lookback is 14 days (verified in code)
- [ ] Articles are clustered into themes (max 5 themes per stock)
- [ ] Frequency is detected (HIGH/MEDIUM/LOW shown in output)
- [ ] Source quality filtering active (tier 1 sources prioritized)
- [ ] AI prompt includes enhanced news format
- [ ] Test run shows improved news quality (subjective review)

**Phase 1B (Price Context)** - DONE when:
- [ ] 30-day returns calculated for all stocks
- [ ] Relative performance vs SPY shown
- [ ] Trend classification working (outperforming/neutral/underperforming)
- [ ] AI prompt includes price context section
- [ ] Output dashboard shows price trends
- [ ] Spot-check confirms calculation accuracy

**Phase 2 (Narratives)** - DONE when:
- [ ] narratives.json file created and loaded
- [ ] AI can add new narratives
- [ ] AI can update existing narratives
- [ ] AI can resolve narratives
- [ ] Narratives persist across runs
- [ ] Pruning removes old resolved narratives (30+ days)
- [ ] Narrative context shown in AI prompt
- [ ] File size stays reasonable (<100KB)

**Overall Success** - DONE when:
- [ ] All phase acceptance criteria met
- [ ] End-to-end test passes with current portfolio
- [ ] AI recommendations show improved context awareness
- [ ] No regressions in existing functionality
- [ ] Documentation updated (README mentions narratives.json)

---

## Rollback Plan

**If Phase 1A causes issues**:
- Revert news fetching to 7 days, 10 articles
- Remove clustering/filtering code
- Restore original prompt format
- Impact: Back to current behavior

**If Phase 1B causes issues**:
- Remove price context section from prompt
- Skip price calculations
- Impact: No price trend context, but news still enhanced

**If Phase 2 causes issues**:
- Delete narratives.json file
- Remove narrative sections from prompt
- Skip narrative update parsing
- Impact: No memory across runs, but other enhancements remain

**No data loss risk**: All changes additive, portfolio.json untouched

---

## Future Enhancements (Not in this CR)

- Sentiment analysis on news (positive/negative/neutral scoring)
- News alerts (notify user of breaking material news)
- Narrative visualization (timeline view of theme evolution)
- Sector-level news (tech sector trends affecting all stocks)
- Earnings calendar integration (flag upcoming events in narratives)
- News source credibility scoring (learn which sources are most accurate)

---

## Approval

- [x] Change documented
- [x] Solution reviewed and approved
- [x] Implementation plan created
- [x] Phase 1A implementation complete
- [x] Phase 1A testing complete
- [x] Phase 1B implementation complete
- [x] Phase 1B testing complete
- [ ] Phase 2 implementation complete
- [ ] Phase 2 testing complete
- [ ] Overall acceptance criteria met

**Product Owner**: Tobes
**Reviewed by**: Claude (AI Assistant)
**Approved Date**: January 26, 2026
**Implementation Target**: Phase 1A (Week 1), Phase 1B (Week 2), Phase 2 (Week 3-4)
**Priority**: High (significantly improves AI recommendation quality)

---
