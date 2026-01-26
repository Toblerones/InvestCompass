## ADDENDUM TO CR002: News Clustering Keyword Specification

**Section**: Component 1: Enhanced News Fetching  
**Subsection**: Add headline clustering  
**Status**: Specification clarification

---

### Keyword Clustering Implementation

**Approach**: Rule-based keyword matching (deterministic, no ML required)

**Algorithm**:
1. Normalize headline (lowercase, remove punctuation)
2. Check against keyword groups (in priority order)
3. Assign to first matching theme
4. If no match, categorize as "other"

---

### Theme Keyword Mapping Table

| Theme | Primary Keywords | Secondary Keywords | Example Headlines |
|-------|-----------------|-------------------|-------------------|
| **regulatory** | antitrust, investigation, DOJ, FTC, lawsuit, probe, EU commission, fine, penalty | regulation, regulators, legal action, government suit, monopoly | "DOJ sues Google", "EU fines Meta", "FTC investigation expands" |
| **earnings** | earnings, revenue, profit, EPS, quarterly results, Q1/Q2/Q3/Q4, beat, miss, guidance | sales, income, forecast, outlook, analyst estimates | "Q4 earnings beat", "Revenue misses expectations", "Guidance raised" |
| **product** | launch, release, announcement, unveils, introduces, new product, update, version | features, beta, rollout, availability, upgrade | "Apple unveils iPhone 16", "Tesla launches FSD v12", "Microsoft releases Copilot" |
| **leadership** | CEO, CFO, executive, resignation, appointed, steps down, fires, hires, management change | leadership, departure, promotes, board, founder | "CEO resigns", "Microsoft appoints new CFO", "Musk fires executive" |
| **legal** | lawsuit, litigation, settlement, court, ruling, verdict, judge, plaintiff | case, trial, appeal, damages, injunction | "Apple settles lawsuit", "Court rules against Google", "Patent litigation" |
| **acquisition** | acquires, merger, acquisition, buys, takeover, deal, purchase | M&A, consolidation, buyout, combines | "Microsoft acquires Activision", "Amazon buys Whole Foods" |
| **partnership** | partnership, collaboration, teams up, alliance, joint venture, partnership with | partners, cooperates, works with, agreement | "NVDA partners with Toyota", "Google teams up with Samsung" |
| **layoffs** | layoffs, job cuts, fires, workforce reduction, downsizing, restructuring | cutting jobs, eliminates positions, headcount | "Meta announces layoffs", "Amazon cuts 10,000 jobs" |
| **data_breach** | breach, hack, cyberattack, data leak, security incident, compromised | hacked, stolen data, vulnerability, ransomware | "Microsoft data breach", "Meta user data exposed" |
| **analyst** | upgrade, downgrade, price target, analyst rating, buy rating, sell rating | initiates coverage, maintains, raises target, lowers target | "Analyst upgrades NVDA to buy", "Goldman raises price target" |
| **stock_movement** | stock rises, stock falls, shares up, shares down, gains, losses, rallies, drops | climbs, jumps, plunges, surges, tumbles | "Tesla stock jumps 5%", "Google shares fall" |

---

### Implementation Code

```python
# In data_collector.py

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

def classify_headline(headline, url=""):
    """
    Classify a news headline into a theme
    
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


def cluster_news(articles):
    """
    Cluster articles by theme
    
    Args:
        articles: List of {headline, date, url, source}
        
    Returns:
        Dict of {theme: [articles]}
    """
    clusters = {}
    
    for article in articles:
        theme = classify_headline(article['headline'], article.get('url', ''))
        
        if theme not in clusters:
            clusters[theme] = []
        
        clusters[theme].append(article)
    
    return clusters


def get_top_themes(clusters, max_themes=5, exclude_noise=True):
    """
    Get top N themes by article count, excluding noise
    
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
    
    # Sort by article count
    sorted_themes = sorted(filtered.items(), 
                          key=lambda x: len(x[1]), 
                          reverse=True)
    
    # Return top N
    return sorted_themes[:max_themes]
```

---

### Usage Example

```python
# In data_collector.py - scan_news_enhanced()

def scan_news_enhanced(tickers, days=14, max_articles=25):
    results = {}
    
    for ticker in tickers:
        # Fetch raw articles (existing code)
        raw_articles = fetch_news_from_rss(ticker, days, max_articles)
        
        # NEW: Cluster articles
        clusters = cluster_news(raw_articles)
        
        # NEW: Get top themes (excluding noise)
        top_themes = get_top_themes(clusters, max_themes=5, exclude_noise=True)
        
        # Format for output
        themes = []
        for theme_name, articles in top_themes:
            # Pick most recent article as representative
            representative = max(articles, key=lambda x: x['date'])
            
            themes.append({
                "name": theme_name,
                "headline": representative['headline'],
                "date": representative['date'],
                "source": representative['source'],
                "article_count": len(articles),
                "frequency": classify_frequency(len(articles), days),
                "urls": [a['url'] for a in articles]
            })
        
        results[ticker] = {"themes": themes}
    
    return results


def classify_frequency(article_count, days):
    """Classify frequency based on article count"""
    articles_per_week = (article_count / days) * 7
    
    if articles_per_week >= 3:
        return "HIGH"
    elif articles_per_week >= 1:
        return "MEDIUM"
    else:
        return "LOW"
```

---

### Filter Rules for Noise Reduction

**Always exclude from top themes** (unless explicitly material):
- `stock_movement` - Generic "stock up/down" articles (no new information)
- `analyst` - Upgrades/downgrades (opinion, not events)
- `other` - Uncategorized (likely irrelevant)

**Include these themes** (material events):
- `regulatory` - Always material (legal/gov risk)
- `earnings` - Always material (quarterly results)
- `leadership` - Usually material (CEO changes impact)
- `legal` - Usually material (lawsuits are significant)
- `acquisition` - Always material (M&A changes business)
- `product` - Sometimes material (major launches only)
- `partnership` - Sometimes material (if strategic)
- `layoffs` - Usually material (business stress signal)
- `data_breach` - Always material (reputation/liability risk)

---

### Edge Cases & Refinements

**Multi-theme headlines**:
```
"Microsoft CEO announces layoffs amid antitrust probe"
```
- Matches both `leadership` AND `regulatory` AND `layoffs`
- **Solution**: Return first match by priority (regulatory wins, priority 1)

**Ticker-specific keywords**:
```python
# Optional enhancement: Add ticker-specific keywords
TICKER_KEYWORDS = {
    "TSLA": {
        "product": ["cybertruck", "model y", "fsd", "autopilot", "robotaxi"]
    },
    "NVDA": {
        "product": ["rtx", "geforce", "data center", "ai chips", "h100"]
    }
    # ... etc
}
```

**Source quality weighting**:
```python
SOURCE_QUALITY = {
    "reuters.com": 1.0,
    "bloomberg.com": 1.0,
    "wsj.com": 1.0,
    "cnbc.com": 0.9,
    "techcrunch.com": 0.7,
    "fool.com": 0.3,  # Motley Fool - often clickbait
    "seekingalpha.com": 0.3  # Opinion pieces
}

# When clustering, weight by source quality
def calculate_theme_importance(articles):
    return sum(SOURCE_QUALITY.get(a['source'], 0.5) for a in articles)
```

---

### Testing & Validation

**Unit tests**:
```python
def test_regulatory_classification():
    assert classify_headline("DOJ sues Google") == "regulatory"
    assert classify_headline("EU opens antitrust investigation") == "regulatory"
    assert classify_headline("Microsoft fined by regulators") == "regulatory"

def test_earnings_classification():
    assert classify_headline("Apple Q4 earnings beat") == "earnings"
    assert classify_headline("Tesla revenue misses estimates") == "earnings"
    assert classify_headline("NVDA raises guidance") == "earnings"

def test_noise_filtering():
    headlines = [
        "GOOGL stock rises 2%",  # noise
        "DOJ sues Google",  # signal
        "Analyst upgrades Google"  # noise
    ]
    clusters = cluster_news([{"headline": h} for h in headlines])
    top = get_top_themes(clusters, exclude_noise=True)
    assert len(top) == 1
    assert top[0][0] == "regulatory"
```

**Manual validation**:
- Run on last 14 days of real news
- Spot-check 20 random headlines
- Verify theme assignments make sense
- Tune keywords if misclassifications found

---

### Expected Output Example

**Before clustering** (current system):
```
GOOGL news (10 articles):
- "Google stock rises 3%" (Jan 24)
- "Analyst upgrades GOOGL" (Jan 23)
- "DOJ expands investigation" (Jan 23)
- "Google launches new AI" (Jan 22)
- "GOOGL shares gain" (Jan 21)
- "EU probes Google" (Jan 20)
- "Google Cloud growth" (Jan 19)
- "Stock hits new high" (Jan 18)
- "Q4 earnings beat" (Jan 17)
- "Price target raised" (Jan 16)
```

**After clustering** (new system):
```
GOOGL themes (5 material themes):

Theme: regulatory (HIGH frequency - 4 articles)
  "DOJ expands antitrust investigation" (Jan 23, Reuters)
  
Theme: earnings (MEDIUM frequency - 2 articles)
  "Q4 earnings beat estimates" (Jan 17, WSJ)
  
Theme: product (LOW frequency - 1 article)
  "Google launches Gemini AI 2.0" (Jan 22, TechCrunch)

[stock_movement and analyst themes filtered out as noise]
```

---

### Performance Considerations

**Computational cost**:
- Simple string matching: O(keywords × articles)
- 10 themes × ~20 keywords × 25 articles = ~5000 comparisons
- Expected time: <50ms per ticker
- Total: <500ms for 10 tickers

**Memory**:
- Keyword dict: ~5KB
- No significant memory overhead

**API impact**:
- None (processing happens locally after fetch)

---

### Maintenance Plan

**Keyword updates**:
- Review quarterly based on misclassifications
- Add new keywords as language evolves
- Remove keywords that cause false positives

**New themes**:
- Can add new themes as needed (e.g., "supply_chain", "ai_advancement")
- Requires updating THEME_KEYWORDS dict only

**Tuning**:
- If too many false positives → tighten keyword lists
- If too many uncategorized → add secondary keywords
- If wrong priority → adjust priority values

---

## Approval for Addendum

- [x] Keyword mapping table defined
- [x] Implementation code provided
- [x] Edge cases addressed
- [x] Testing plan included
- [x] Reviewed and approved for inclusion in CR002

**Approved Date**: January 26, 2026
