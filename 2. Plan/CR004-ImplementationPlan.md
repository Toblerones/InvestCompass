# CR004 Implementation Plan - Enhanced Google RSS News Collection

**CR Reference**: [CR004-Enhanced Google RSS News Collection](../3.%20ChangeLog/CR004%20-%20Enhanced%20Google%20RSS%20News%20Collection.md)
**Created**: January 28, 2026
**Status**: ✅ Complete

---

## Code Review Audit

**Reviewer**: Claude Code Assistant

### Key Finding

CR004 assumes only `scan_news()` exists, but **`scan_news_enhanced()` is already implemented** and active (lines 774-886 in data_collector.py).

### Already Implemented (via CR002)

| Feature | CR004 Proposed | Already Done | Location |
|---------|----------------|--------------|----------|
| 14-day lookback | Yes | ✅ Yes | Line 774 `days=14` |
| 25 article fetch | Yes | ✅ Yes | `max_articles=25` |
| Theme clustering | Different approach | ✅ Yes | `cluster_news()` line 633 |
| Noise filtering | Pattern-based | ✅ Theme-based | `exclude_noise=True` |
| Source quality | Tier-based | ✅ Score-based | `SOURCE_QUALITY` lines 559-584 |

### Remaining Gaps (Focus of This Plan)

| Feature | Status | Description |
|---------|--------|-------------|
| Targeted query | ✅ Implemented | `build_material_events_query()` at line 602 |
| Headline deduplication | ✅ Implemented | `deduplicate_headlines()` at line 621 |

---

## Overview

This plan implements the remaining gaps in CR004:
1. **Targeted material events query** - replace generic `"{ticker} stock"` with focused keywords
2. **Headline deduplication** - fuzzy matching to consolidate duplicate stories

---

## Phase 1: Update CR004 Document ✅

**Goal**: Reflect actual codebase state

| ID | Task | Status |
|----|------|--------|
| 1.1 | Add "Code Review Audit" section to CR004 | ✅ |
| 1.2 | Mark already-implemented items as complete | ✅ |
| 1.3 | Narrow scope to targeted queries + deduplication | ✅ |
| 1.4 | Update line references to match actual code | ✅ |

---

## Phase 2: Implement Targeted Query ✅

**Goal**: Replace generic query with material events focus

**File**: `data_collector.py`

| ID | Task | Status |
|----|------|--------|
| 2.1 | Add `MATERIAL_EVENT_KEYWORDS` constant | ✅ Line 589 |
| 2.2 | Add `build_material_events_query(ticker)` function | ✅ Line 602 |
| 2.3 | Modify `scan_news_enhanced()` to use targeted query | ✅ Line 889 |
| 2.4 | Test query outputs correct format | ✅ Verified |

**Implementation**:
```python
MATERIAL_EVENT_KEYWORDS = [
    "earnings", "revenue", "profit",
    "investigation", "lawsuit", "antitrust",
    "acquisition", "merger", "partnership",
    "CEO", "CFO", "executive",
    "layoffs", "restructuring",
    "product launch", "AI", "cloud",
    "regulatory", "fine", "settlement",
    "data breach", "guidance"
]

def build_material_events_query(ticker: str) -> str:
    """Build targeted Google News query for material events."""
    keywords = " OR ".join(MATERIAL_EVENT_KEYWORDS)
    return f"{ticker} ({keywords})"
```

**Integration point**: Line ~807 in `scan_news_enhanced()` where query is built

---

## Phase 3: Implement Deduplication ✅

**Goal**: Remove duplicate stories from multiple sources

**File**: `data_collector.py`

| ID | Task | Status |
|----|------|--------|
| 3.1 | Add `deduplicate_headlines(articles)` function | ✅ Line 621 |
| 3.2 | Use SequenceMatcher for 60% similarity threshold | ✅ (adjusted from 80% for better detection) |
| 3.3 | Integrate into `scan_news_enhanced()` after fetch | ✅ Line 912-914 |
| 3.4 | Track deduplication count in stats | ✅ `duplicates_removed` in stats |

**Implementation**:
```python
from difflib import SequenceMatcher

def deduplicate_headlines(articles: list, threshold: float = 0.8) -> list:
    """Remove duplicate articles based on headline similarity."""
    if not articles:
        return []

    unique = []
    seen_normalized = []

    for article in articles:
        headline = article.get('headline', '').lower()
        headline = re.sub(r'[^\w\s]', '', headline)
        headline = ' '.join(headline.split())

        is_duplicate = False
        for seen in seen_normalized:
            if SequenceMatcher(None, headline, seen).ratio() > threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique.append(article)
            seen_normalized.append(headline)

    return unique
```

**Integration point**: Line ~835 after RSS fetch, before `cluster_news()`

---

## Phase 4: Testing & Validation ✅

**Goal**: Verify changes work correctly

| ID | Task | Status |
|----|------|--------|
| 4.1 | Test targeted query format | ✅ Verified correct OR-joined format |
| 4.2 | Test deduplication removes similar headlines | ✅ Removed 2/5 duplicates in test |
| 4.3 | Run full advisor flow | ✅ Completed successfully |
| 4.4 | Verify no regressions in news display | ✅ News themes display correctly |
| 4.5 | Check AI still receives news context | ✅ AI recommendations reference news |

---

## Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `3. ChangeLog/CR004...md` | 1 | Add audit, narrow scope |
| `App/src/data_collector.py` | 2, 3 | Add query builder, dedup function |

---

## Dependencies

- `difflib` - Standard library (no install needed)
- Existing `scan_news_enhanced()` infrastructure

---

## Verification Commands

```bash
# Test targeted query
cd App && python -c "
from src.data_collector import build_material_events_query
print(build_material_events_query('GOOGL'))
"

# Test deduplication
cd App && python -c "
from src.data_collector import deduplicate_headlines
articles = [
    {'headline': 'DOJ sues Google'},
    {'headline': 'DOJ files Google lawsuit'},
    {'headline': 'Google Cloud grows'}
]
result = deduplicate_headlines(articles)
print(f'Input: {len(articles)}, Output: {len(result)}')
for a in result:
    print(f'  - {a[\"headline\"]}')
"

# Full advisor run
cd App && python -m src.advisor
```

---

## Acceptance Criteria

- [x] CR004 document updated with audit section
- [x] `build_material_events_query()` returns `"TICKER (keyword1 OR keyword2 OR ...)"` format
- [x] `deduplicate_headlines()` removes 60%+ similar headlines (adjusted threshold)
- [x] `scan_news_enhanced()` uses targeted query
- [x] Deduplication integrated into news pipeline
- [x] Full advisor run succeeds with enhanced news
- [x] No regressions in existing functionality

---

## Progress Tracking

| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| 1 | ✅ Complete | 4/4 | CR004 document updated |
| 2 | ✅ Complete | 4/4 | Targeted query implemented |
| 3 | ✅ Complete | 4/4 | Deduplication implemented |
| 4 | ✅ Complete | 5/5 | All tests passed |

---

**Completed**: January 28, 2026
