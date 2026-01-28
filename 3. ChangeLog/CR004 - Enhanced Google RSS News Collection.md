# Change Request: CR004 - Enhanced Google RSS News Collection

**Date**: January 27, 2026
**Status**: ✅ Implemented
**Priority**: Medium
**Affects**: `data_collector.py`
**Related**: CR002 (News Clustering & Sentiment)
**Implementation Plan**: [CR004-ImplementationPlan.md](../2.%20Plan/CR004-ImplementationPlan.md)

---

## Code Review Audit (January 28, 2026)

**Reviewer**: Claude Code Assistant

### Key Finding

`scan_news_enhanced()` already exists (lines 774-886) and implements many CR004 features. CR004 scope narrowed to remaining gaps.

### Already Implemented (via CR002)

| Feature | CR004 Proposed | Status | Location |
|---------|----------------|--------|----------|
| 14-day lookback | ✓ | ✅ DONE | `scan_news_enhanced()` line 774 |
| 25 article fetch | ✓ | ✅ DONE | `max_articles=25` parameter |
| Theme clustering | Different approach | ✅ DONE | `cluster_news()` line 633 |
| Noise filtering | Pattern-based | ✅ DONE (theme-based) | `exclude_noise=True` |
| Source quality | Tier-based | ✅ DONE (score-based) | `SOURCE_QUALITY` lines 559-584 |

### Remaining Gaps (New Scope) - ✅ FIXED

| Feature | Status | Description |
|---------|--------|-------------|
| Targeted query | ✅ Fixed | `build_material_events_query()` at line 602 |
| Headline deduplication | ✅ Fixed | `deduplicate_headlines()` at line 621 |

### Existing Constants (Different Names)

| CR004 Names | Actual Names | Lines |
|-------------|--------------|-------|
| `SOURCE_TIERS` | `SOURCE_QUALITY` | 559-584 |
| `MATERIAL_EVENT_KEYWORDS` | `THEME_KEYWORDS` (partial) | 491-557 |

### Corrected Scope

This CR004 now focuses ONLY on:
1. **Add `build_material_events_query()`** - Replace generic query with targeted keywords
2. **Add `deduplicate_headlines()`** - Fuzzy matching to remove duplicate stories

---

## Problem Description

The current Google RSS news collection has several limitations that reduce the quality and relevance of news data provided to the AI recommendation engine:

1. **Poor query specificity**: Generic search terms like "GOOGL stock" return noise
   - Gets: "GOOGL stock rises 2%" (price movement spam)
   - Misses: Targeted searches for material events (earnings, acquisitions, investigations)

2. **No deduplication**: Same story from multiple sources counted as separate articles
   - "DOJ sues Google" (Reuters)
   - "DOJ files Google lawsuit" (Bloomberg)
   - "Google faces DOJ suit" (CNBC)
   - → 3 articles counted when it's really 1 event

3. **No source quality filtering at collection**: All sources treated equally
   - Motley Fool clickbait = Reuters investigation report
   - Results in low signal-to-noise ratio

4. **Inefficient data structure**: Raw RSS feed parsing, not optimized
   - Inconsistent date formats
   - Missing source attribution
   - No URL validation

**Impact**: 
- AI receives 10-15 articles per stock but only 2-3 are material
- Time wasted processing noise articles
- Risk of missing important events buried in spam
- Lower quality recommendations due to noisy input data

---

## Current Behavior

### News Collection Code
```python
# In data_collector.py

def scan_news(tickers, days=7):
    """Current implementation"""
    news = {}
    
    for ticker in tickers:
        # Generic query
        query = f"{ticker} stock"
        url = f"https://news.google.com/rss/search?q={query}"
        
        # Fetch RSS feed
        feed = feedparser.parse(url)
        
        # Take first 10 entries
        articles = []
        for entry in feed.entries[:10]:
            articles.append({
                "headline": entry.title,
                "date": entry.published,
                "url": entry.link
            })
        
        news[ticker] = articles
    
    return news
```

### Example Output
```python
# GOOGL news (10 articles, lots of noise)
[
    {"headline": "Google stock rises 1.5% in trading", ...},  # Noise
    {"headline": "GOOGL shares gain momentum", ...},           # Noise
    {"headline": "Analyst upgrades Google to buy", ...},       # Low value
    {"headline": "DOJ expands antitrust investigation", ...},  # SIGNAL
    {"headline": "Google stock declines on market fears", ...},# Noise
    {"headline": "GOOGL hits new 52-week high", ...},          # Noise
    {"headline": "EU opens probe into Google", ...},           # SIGNAL (duplicate with #4)
    {"headline": "Google shares up after hours", ...},         # Noise
    {"headline": "Is Google stock a buy?", ...},               # Opinion/noise
    {"headline": "Google announces AI product", ...}           # SIGNAL
]

# Only 3-4 material articles out of 10
# Duplicates not removed (DOJ story appears twice)
# Source quality not considered
```

---

## Expected Behavior

### Enhanced News Collection
```python
# In data_collector.py

def scan_news_enhanced(tickers, days=14):
    """Enhanced implementation with better queries and filtering"""
    news = {}
    
    for ticker in tickers:
        # 1. Targeted query (material events only)
        query = build_material_events_query(ticker)
        
        # 2. Fetch more articles to have buffer for filtering
        raw_articles = fetch_google_rss(ticker, query, days=14, max_results=25)
        
        # 3. Deduplicate similar headlines
        unique_articles = deduplicate_headlines(raw_articles)
        
        # 4. Filter by source quality
        quality_articles = filter_by_source_tier(unique_articles)
        
        # 5. Remove price movement spam
        filtered_articles = remove_price_noise(quality_articles)
        
        # 6. Sort by date (most recent first)
        sorted_articles = sort_by_date(filtered_articles)
        
        news[ticker] = sorted_articles[:15]  # Keep top 15 after filtering
    
    return news
```

### Example Output
```python
# GOOGL news (6 high-quality articles, noise removed)
[
    {"headline": "DOJ expands antitrust investigation into Google",
     "date": "2026-01-23",
     "source": "Reuters",
     "url": "...",
     "source_tier": 1},  # ← Deduplicated, tier-1 source
    
    {"headline": "Google announces Gemini AI 2.0 release",
     "date": "2026-01-22", 
     "source": "TechCrunch",
     "url": "...",
     "source_tier": 2},
    
    {"headline": "Google Cloud revenue beats estimates in Q4",
     "date": "2026-01-18",
     "source": "WSJ",
     "url": "...",
     "source_tier": 1},
    
    # ... 3 more material articles
]

# All articles are material events
# No duplicates
# Source quality tracked
# Price movement spam removed
```

---

## Proposed Solution

### Component 1: Targeted Query Building

**Function**: `build_material_events_query(ticker)`

**Implementation**:
```python
MATERIAL_EVENT_KEYWORDS = [
    "earnings",
    "investigation", 
    "lawsuit",
    "acquisition",
    "merger",
    "CEO",
    "CFO",
    "executive",
    "product launch",
    "regulatory",
    "fine",
    "settlement",
    "partnership",
    "layoffs",
    "restructuring",
    "data breach",
    "guidance"
]

def build_material_events_query(ticker):
    """
    Build targeted Google News query for material events only
    
    Returns query string that filters for substantive news
    """
    # Join keywords with OR operator
    keywords = " OR ".join(MATERIAL_EVENT_KEYWORDS)
    
    # Format: "TICKER (keyword1 OR keyword2 OR ...)"
    # This tells Google to only return articles mentioning ticker AND one of the keywords
    query = f"{ticker} ({keywords})"
    
    return query

# Example outputs:
# "GOOGL (earnings OR investigation OR lawsuit OR ...)"
# "NVDA (earnings OR investigation OR lawsuit OR ...)"
```

**Benefit**: Reduces noise at source (Google filters before returning results)

---

### Component 2: Headline Deduplication

**Function**: `deduplicate_headlines(articles)`

**Implementation**:
```python
from difflib import SequenceMatcher

def deduplicate_headlines(articles):
    """
    Remove duplicate articles based on headline similarity
    
    Strategy:
    1. Normalize headlines (lowercase, remove punctuation)
    2. Compare each pair using fuzzy matching
    3. If similarity > 80%, keep only first occurrence
    """
    if not articles:
        return []
    
    unique = []
    seen_normalized = []
    
    for article in articles:
        # Normalize headline
        headline = article['headline'].lower()
        headline = re.sub(r'[^\w\s]', '', headline)  # Remove punctuation
        headline = ' '.join(headline.split())  # Normalize whitespace
        
        # Check similarity against existing headlines
        is_duplicate = False
        for seen in seen_normalized:
            similarity = SequenceMatcher(None, headline, seen).ratio()
            if similarity > 0.8:  # 80% similar = duplicate
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique.append(article)
            seen_normalized.append(headline)
    
    return unique

# Example:
# Input:  ["DOJ sues Google", "DOJ files Google lawsuit", "Google Cloud grows"]
# Output: ["DOJ sues Google", "Google Cloud grows"]  # Second headline removed as duplicate
```

**Benefit**: Reduces article count by ~30-40% by removing redundant coverage

---

### Component 3: Source Quality Filtering

**Function**: `filter_by_source_tier(articles)`

**Implementation**:
```python
SOURCE_TIERS = {
    # Tier 1: Premium financial/tech news (weight: 1.0)
    "tier1": [
        "reuters.com",
        "bloomberg.com", 
        "wsj.com",
        "ft.com",
        "apnews.com"
    ],
    
    # Tier 2: Mainstream business news (weight: 0.8)
    "tier2": [
        "cnbc.com",
        "marketwatch.com",
        "businessinsider.com",
        "forbes.com",
        "fortune.com"
    ],
    
    # Tier 3: Tech-focused outlets (weight: 0.6)
    "tier3": [
        "techcrunch.com",
        "theverge.com",
        "arstechnica.com",
        "wired.com"
    ],
    
    # Noise: Low-quality sources (weight: 0.2, often filtered out)
    "noise": [
        "fool.com",           # Motley Fool (clickbait)
        "seekingalpha.com",   # Opinion pieces
        "benzinga.com",       # Aggregator spam
        "investors.com"       # IBD listicles
    ]
}

def get_source_tier(url):
    """Determine source tier from URL"""
    from urllib.parse import urlparse
    
    domain = urlparse(url).netloc.lower()
    domain = domain.replace('www.', '')
    
    for tier, domains in SOURCE_TIERS.items():
        if any(d in domain for d in domains):
            return tier
    
    return "unknown"  # Default tier

def filter_by_source_tier(articles, min_tier="tier3"):
    """
    Filter articles by source quality
    
    Args:
        articles: List of article dicts with 'url' field
        min_tier: Minimum acceptable tier (tier1/tier2/tier3)
                  "noise" articles always filtered out
    
    Returns:
        Filtered list with source_tier added to each article
    """
    tier_priority = {"tier1": 1, "tier2": 2, "tier3": 3, "noise": 99, "unknown": 50}
    min_priority = tier_priority.get(min_tier, 3)
    
    filtered = []
    for article in articles:
        tier = get_source_tier(article['url'])
        priority = tier_priority.get(tier, 50)
        
        # Filter out noise sources and below minimum tier
        if tier != "noise" and priority <= min_priority:
            article['source_tier'] = tier
            article['source_priority'] = priority
            filtered.append(article)
    
    # Sort by tier (tier1 first) then by date
    filtered.sort(key=lambda x: (x['source_priority'], x.get('date', '')), reverse=True)
    
    return filtered
```

**Benefit**: Prioritizes credible sources, removes clickbait

---

### Component 4: Price Movement Noise Removal

**Function**: `remove_price_noise(articles)`

**Implementation**:
```python
PRICE_NOISE_PATTERNS = [
    r"stock (rises|falls|gains|drops|climbs|tumbles|rallies)",
    r"shares (up|down|higher|lower)",
    r"\d+\.?\d*%",  # Any percentage mention
    r"hits (new )?(high|low)",
    r"52-week (high|low)",
    r"trading (up|down|higher|lower)",
    r"(intraday|after.hours) (trading|gains|losses)",
    r"is .* stock a buy",  # Generic questions
    r"should you buy",
    r"top \d+ stocks",  # Listicles
    r"why .* stock",
    r"what (investors|traders) need to know"
]

def remove_price_noise(articles):
    """
    Remove articles that are just about price movements or generic commentary
    """
    import re
    
    filtered = []
    
    for article in articles:
        headline = article['headline'].lower()
        
        # Check if headline matches noise patterns
        is_noise = False
        for pattern in PRICE_NOISE_PATTERNS:
            if re.search(pattern, headline):
                is_noise = True
                break
        
        if not is_noise:
            filtered.append(article)
    
    return filtered

# Example:
# Input:  ["Google stock rises 3%", "DOJ sues Google", "Is GOOGL a buy?"]
# Output: ["DOJ sues Google"]  # Noise removed
```

**Benefit**: Removes ~40-50% of noise articles about daily price movements

---

### Component 5: Enhanced RSS Fetching

**Function**: `fetch_google_rss(ticker, query, days, max_results)`

**Implementation**:
```python
import feedparser
from datetime import datetime, timedelta
from urllib.parse import quote

def fetch_google_rss(ticker, query, days=14, max_results=25):
    """
    Fetch news from Google RSS with enhanced parameters
    
    Args:
        ticker: Stock ticker symbol
        query: Search query (from build_material_events_query)
        days: Lookback period in days
        max_results: Maximum articles to fetch
    
    Returns:
        List of article dicts with normalized structure
    """
    # Encode query for URL
    encoded_query = quote(query)
    
    # Build Google News RSS URL
    base_url = "https://news.google.com/rss/search"
    url = f"{base_url}?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    # Fetch and parse feed
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"Warning: Failed to fetch news for {ticker}: {e}")
        return []
    
    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=days)
    
    articles = []
    for entry in feed.entries[:max_results]:
        try:
            # Parse publication date
            pub_date = datetime(*entry.published_parsed[:6])
            
            # Skip if older than cutoff
            if pub_date < cutoff_date:
                continue
            
            # Extract source from URL
            source = extract_source_from_url(entry.link)
            
            # Build normalized article structure
            article = {
                "headline": entry.title,
                "date": pub_date.strftime("%Y-%m-%d"),
                "url": entry.link,
                "source": source,
                "ticker": ticker
            }
            
            articles.append(article)
            
        except Exception as e:
            # Skip malformed entries
            continue
    
    return articles

def extract_source_from_url(url):
    """Extract clean source name from URL"""
    from urllib.parse import urlparse
    
    try:
        domain = urlparse(url).netloc
        domain = domain.replace('www.', '')
        
        # Clean up domain to source name
        # "reuters.com" → "Reuters"
        # "techcrunch.com" → "TechCrunch"
        source = domain.split('.')[0].title()
        
        return source
    except:
        return "Unknown"
```

---

### Component 6: Date Normalization & Sorting

**Function**: `sort_by_date(articles)`

**Implementation**:
```python
from datetime import datetime

def sort_by_date(articles):
    """
    Sort articles by date, most recent first
    Handle various date formats from RSS feeds
    """
    def parse_flexible_date(date_str):
        """Parse various date formats"""
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%a, %d %b %Y %H:%M:%S %Z",  # RSS format
            "%Y-%m-%dT%H:%M:%SZ",         # ISO format
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        # Fallback: assume recent if can't parse
        return datetime.now()
    
    # Add parsed datetime for sorting
    for article in articles:
        article['_datetime'] = parse_flexible_date(article.get('date', ''))
    
    # Sort by datetime, most recent first
    sorted_articles = sorted(articles, key=lambda x: x['_datetime'], reverse=True)
    
    # Remove temporary datetime field
    for article in sorted_articles:
        del article['_datetime']
    
    return sorted_articles
```

---

## Integration with CR002

**Relationship**: 
- CR004 enhances **news collection** (better raw data)
- CR002 enhances **news analysis** (clustering, sentiment, narratives)

**Combined workflow**:
```
CR004: Enhanced Collection
  ↓
Better quality articles (15 instead of 10, less noise)
  ↓
CR002: Clustering & Sentiment
  ↓  
Grouped themes with sentiment scores
  ↓
AI Prompt: High-quality, organized news context
```

**Implementation order**:
1. **Implement CR004 first** (better raw data)
2. **Then implement CR002** (better analysis of that data)

**Alternatively**: Implement both in parallel as they don't conflict

---

## Testing Plan

### Unit Tests

```python
# test_news_collection.py

def test_build_material_events_query():
    query = build_material_events_query("GOOGL")
    assert "GOOGL" in query
    assert "earnings" in query.lower()
    assert "investigation" in query.lower()

def test_deduplicate_headlines():
    articles = [
        {"headline": "DOJ sues Google"},
        {"headline": "DOJ files Google lawsuit"},  # Similar
        {"headline": "Google Cloud grows"}
    ]
    result = deduplicate_headlines(articles)
    assert len(result) == 2  # Middle one removed

def test_source_tier_detection():
    assert get_source_tier("https://www.reuters.com/article") == "tier1"
    assert get_source_tier("https://techcrunch.com/article") == "tier3"
    assert get_source_tier("https://fool.com/article") == "noise"

def test_price_noise_removal():
    articles = [
        {"headline": "Google stock rises 3%"},  # Noise
        {"headline": "DOJ investigation expands"},  # Signal
        {"headline": "Is GOOGL a buy?"}  # Noise
    ]
    result = remove_price_noise(articles)
    assert len(result) == 1
    assert "DOJ" in result[0]['headline']

def test_date_sorting():
    articles = [
        {"headline": "Old news", "date": "2026-01-10"},
        {"headline": "New news", "date": "2026-01-25"},
        {"headline": "Middle news", "date": "2026-01-20"}
    ]
    result = sort_by_date(articles)
    assert result[0]['headline'] == "New news"
    assert result[2]['headline'] == "Old news"
```

### Integration Tests

```python
def test_full_enhanced_collection():
    """Test complete enhanced news collection pipeline"""
    news = scan_news_enhanced(['GOOGL'], days=14)
    
    assert 'GOOGL' in news
    articles = news['GOOGL']
    
    # Should have filtered down to quality articles
    assert len(articles) <= 15
    
    # All should have source tier
    assert all('source_tier' in a for a in articles)
    
    # No noise sources
    assert all(a['source_tier'] != 'noise' for a in articles)
    
    # Sorted by date (most recent first)
    dates = [a['date'] for a in articles]
    assert dates == sorted(dates, reverse=True)
```

### Manual Testing

1. **Before/After comparison**:
   ```bash
   # Run current implementation
   $ python -c "from data_collector import scan_news; print(len(scan_news(['GOOGL'])[0]))"
   # Output: 10 articles (mixed quality)
   
   # Run enhanced implementation  
   $ python -c "from data_collector import scan_news_enhanced; print(len(scan_news_enhanced(['GOOGL'])[0]))"
   # Output: 6-8 articles (high quality only)
   ```

2. **Quality check**: Manually review articles for one ticker
   - Verify no price movement spam
   - Verify no duplicates
   - Verify tier-1 sources prioritized

3. **Coverage check**: Ensure no major events missed
   - Pick recent major event (e.g., NVDA earnings)
   - Verify it appears in enhanced collection
   - Verify it was in original collection too (or note if new)

---

## Performance Impact

### Current Implementation:
- **Time**: ~3-5 seconds per ticker (10 articles)
- **Total**: ~30-50 seconds for 10 tickers
- **Memory**: Minimal (~100KB for 100 articles)

### Enhanced Implementation:
- **Time**: ~4-7 seconds per ticker (fetch 25, filter to 15)
  - +1-2 seconds for deduplication
  - +0.5 seconds for filtering
- **Total**: ~40-70 seconds for 10 tickers
- **Memory**: Minimal (~200KB for 250 raw articles)

**Impact**: +10-20 seconds total execution time (acceptable for on-demand tool)

---

## Acceptance Criteria

**Data Collection** - DONE when:
- [ ] `build_material_events_query()` implemented
- [ ] Query includes all material event keywords
- [ ] Generic "stock" query replaced with targeted query
- [ ] Fetch increased to 25 articles (before filtering)
- [ ] Lookback increased to 14 days

**Deduplication** - DONE when:
- [ ] `deduplicate_headlines()` implemented
- [ ] Fuzzy matching detects 80%+ similar headlines
- [ ] Duplicates removed (first occurrence kept)
- [ ] Test: "DOJ sues Google" + "DOJ files lawsuit" → 1 article

**Source Filtering** - DONE when:
- [ ] SOURCE_TIERS defined (tier1/tier2/tier3/noise)
- [ ] `get_source_tier()` extracts tier from URL
- [ ] `filter_by_source_tier()` removes noise sources
- [ ] Articles sorted by tier then date
- [ ] source_tier field added to each article

**Noise Removal** - DONE when:
- [ ] PRICE_NOISE_PATTERNS defined
- [ ] `remove_price_noise()` filters generic headlines
- [ ] Test: "Stock rises 3%" removed, "DOJ lawsuit" kept

**Date Handling** - DONE when:
- [ ] `sort_by_date()` handles multiple date formats
- [ ] Articles sorted most recent first
- [ ] Cutoff date respected (only articles within N days)

**Integration** - DONE when:
- [ ] `scan_news_enhanced()` orchestrates all components
- [ ] Returns 6-15 high-quality articles per ticker
- [ ] Replaces `scan_news()` in main data collection
- [ ] No regressions in downstream code

**Quality Validation** - DONE when:
- [ ] Manual review: No price movement spam in output
- [ ] Manual review: No duplicate stories
- [ ] Manual review: Tier-1 sources appear first
- [ ] Coverage: Recent major events still captured
- [ ] Noise reduction: ~40-60% fewer articles, higher relevance

---

## Future Enhancements (Not in this CR)

### Phase 2: Additional News Sources

**NewsAPI Integration** (when needed):
- Add as supplementary source for low-coverage stocks
- Use only when Google RSS returns <5 articles
- Free tier: 100 requests/day limit
- Implementation:
  ```python
  def fetch_newsapi(ticker, days=7):
      """Fetch from NewsAPI as supplement to Google RSS"""
      # Only call if Google RSS insufficient
      # Rate limited: track daily request count
  ```

**When to add**:
- After 1 month of CR004 usage
- If discovering missed major events
- If consistent low coverage (<5 articles) for certain stocks

**Cost**: $0 (free tier sufficient for 10 stocks)

---

### Phase 3: Social Media Signals

**Reddit Sentiment**:
- Monitor r/wallstreetbets, r/stocks for retail sentiment
- Detect unusual mention spikes (momentum/hype indicator)
- Contrarian signal (extreme bullishness = caution)

**Twitter/X Monitoring**:
- Track finance influencers
- Early detection of breaking news
- Sentiment shifts before mainstream media

**Complexity**: High (noise filtering, API management)
**Value**: Medium (useful for momentum detection, not fundamentals)

---

### Phase 4: Historical News Database

**Store news over time**:
- Build local database of collected news
- Enable trend analysis (sentiment over 3-6 months)
- Pattern recognition (how stock reacted to past similar events)

**Storage**: SQLite or JSON files
**Value**: High (after 6+ months of data accumulated)

---

## Rollback Plan

**If enhanced collection causes issues**:

1. **Revert to basic collection**:
   ```python
   # In data_collector.py, comment out:
   # return scan_news_enhanced(tickers, days)
   
   # Restore:
   return scan_news(tickers, days=7)  # Original implementation
   ```

2. **Impact**: Back to current 10-article noisy collection

**No data loss**: All changes are in data collection logic, portfolio.json untouched

**Rollback time**: <2 minutes (comment 1 line, uncomment 1 line)

---

## Documentation Updates

**README.md** - Add section:
```markdown
### Enhanced News Collection

The system collects news from Google RSS with intelligent filtering:

**Quality improvements**:
- Targeted queries for material events (earnings, acquisitions, investigations)
- Deduplication of similar headlines (removes redundant coverage)
- Source quality tiers (Reuters/Bloomberg prioritized over Motley Fool)
- Noise filtering (removes "stock up 2%" spam)

**Coverage**:
- 14-day lookback window (vs 7 days previously)
- Fetches 25 articles, filters to 6-15 high-quality items
- Material events only (no generic price commentary)

**Source tiers**:
- Tier 1: Reuters, Bloomberg, WSJ, Financial Times
- Tier 2: CNBC, MarketWatch, Forbes
- Tier 3: TechCrunch, The Verge
- Filtered: Motley Fool, Seeking Alpha (opinion/clickbait)
```

---

## Dependencies

**Python libraries** (already installed):
- `feedparser` - RSS feed parsing
- `urllib` - URL encoding
- `datetime` - Date handling
- `difflib` - Fuzzy string matching (for deduplication)
- `re` - Regular expressions (for noise filtering)

**No new dependencies required**

---

## Approval

- [x] Change documented
- [ ] Solution reviewed and approved
- [ ] Implementation complete
- [ ] Unit tests complete
- [ ] Integration tests complete
- [ ] Manual quality validation complete
- [ ] Documentation updated

**Product Owner**: Tobes  
**Implementation Target**: Week of Jan 27, 2026  
**Priority**: Medium  
**Estimated Effort**: 6-8 hours  
**Dependencies**: None (standalone enhancement)

---

**END OF CHANGE REQUEST**