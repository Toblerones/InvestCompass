# CR002 Implementation Plan - Enhanced News Analysis with Price Context

**CR Reference**: [CR002-Enhanced News Analysis with Price Context](../3.%20ChangeLog/CR002-Enhanced%20News%20Analysis%20with%20Price%20Context.md)
**Addendum**: [CR002-ADDENDUM-News Clustering Keyword Specification](../3.%20ChangeLog/CR002-ADDENDUM-News%20Clustering%20Keyword%20Specification.md)
**Created**: January 26, 2026
**Status**: Phases 1A, 1B, 2 Complete (Phase 3 Future)

---

## Overview

This plan breaks down CR002 into trackable implementation tasks across 3 phases.

---

## Phase 1A: Enhanced News (Priority) ✅ COMPLETED

**Goal**: Cluster news by theme, filter noise, show frequency

| ID | Task | File | Status |
|----|------|------|--------|
| 1A.1 | Add `THEME_KEYWORDS` dictionary | `data_collector.py` | ✅ |
| 1A.2 | Add `SOURCE_QUALITY` dictionary | `data_collector.py` | ✅ |
| 1A.3 | Implement `classify_headline()` function | `data_collector.py` | ✅ |
| 1A.4 | Implement `cluster_news()` function | `data_collector.py` | ✅ |
| 1A.5 | Implement `get_top_themes()` function | `data_collector.py` | ✅ |
| 1A.6 | Implement `classify_frequency()` function | `data_collector.py` | ✅ |
| 1A.7 | Update `scan_news()` → `scan_news_enhanced()` | `data_collector.py` | ✅ |
| 1A.8 | Expand lookback to 14 days, fetch 25 articles | `data_collector.py` | ✅ |
| 1A.9 | Update `_format_news()` for themed output | `ai_agent.py` | ✅ |
| 1A.10 | Update `generate_market_context()` for enhanced news | `analyzer.py` | ✅ |
| 1A.11 | Fix `analyze_entry_signals()` for new news structure | `analyzer.py` | ✅ |
| 1A.12 | Update `display.py` for themed news display | `display.py` | ✅ |
| 1A.13 | Manual testing - verify clustering works | Manual | ✅ |

**Deliverables**:
- [x] News clustered into themes (max 5 per stock)
- [x] Frequency detection (HIGH/MEDIUM/LOW)
- [x] Source quality filtering active
- [x] AI prompt shows enhanced news format

**Completed**: January 26, 2026

---

## Phase 1B: Price Context ✅ COMPLETED

**Goal**: Add 30-day performance vs market benchmark

| ID | Task | File | Status |
|----|------|------|--------|
| 1B.1 | Add SPY to data fetching (`fetch_benchmark_data()`) | `data_collector.py` | ✅ |
| 1B.2 | Implement `calculate_price_context()` function | `data_collector.py` | ✅ |
| 1B.3 | Add trend classification (outperforming/neutral/underperforming) | `data_collector.py` | ✅ |
| 1B.4 | Update `generate_market_context()` to include price context | `analyzer.py` | ✅ |
| 1B.5 | Add `_format_price_context()` helper | `ai_agent.py` | ✅ |
| 1B.6 | Update `build_prompt()` with price context section | `ai_agent.py` | ✅ |
| 1B.7 | Update `display.py` to show price trends in output | `display.py` | ✅ |
| 1B.8 | Manual testing - verify calculations vs broker data | Manual | ✅ |

**Deliverables**:
- [x] 30-day returns calculated for portfolio + top 3 stocks
- [x] Relative performance vs SPY shown
- [x] Trend classification working (±3% threshold)
- [x] AI prompt includes price context

**Completed**: January 26, 2026

---

## Phase 2: Narrative Storage ✅ COMPLETED

**Goal**: Persist narratives across runs for context memory

| ID | Task | File | Status |
|----|------|------|--------|
| 2.1 | Create `narrative_manager.py` module | `src/narrative_manager.py` | ✅ |
| 2.2 | Define `narratives.json` schema | `config/narratives.json` | ✅ |
| 2.3 | Implement `load_narratives()` function | `narrative_manager.py` | ✅ |
| 2.4 | Implement `save_narratives()` function | `narrative_manager.py` | ✅ |
| 2.5 | Implement `update_narratives()` function (with dedup) | `narrative_manager.py` | ✅ |
| 2.6 | Implement `prune_old_narratives()` function | `narrative_manager.py` | ✅ |
| 2.7 | Implement `format_narratives_for_prompt()` function | `narrative_manager.py` | ✅ |
| 2.8 | Update AI JSON response schema with `narrative_updates` | `ai_agent.py` | ✅ |
| 2.9 | Add narrative context section to `build_prompt()` | `ai_agent.py` | ✅ |
| 2.10 | Parse `narrative_updates` from AI response | `ai_agent.py` | ✅ |
| 2.11 | Integrate narrative loading/saving into `advisor.py` | `advisor.py` | ✅ |
| 2.12 | Add `narratives.json` to `.gitignore` | `.gitignore` | ✅ |
| 2.13 | Test narrative persistence across runs | Manual | ✅ |
| 2.14 | Test narrative update/resolve lifecycle | Manual | ✅ |

**Deliverables**:
- [x] `narratives.json` file created and loaded
- [x] AI can add/update/resolve narratives
- [x] Narratives persist across program runs
- [x] Pruning removes old resolved narratives (30+ days)
- [x] Narrative context shown in AI prompt
- [x] Deduplication prevents duplicate themes

**Completed**: January 26, 2026

---

## Phase 3: Refinement (Future)

| ID | Task | Status |
|----|------|--------|
| 3.1 | Improve clustering algorithm based on real-world testing | ⬜ |
| 3.2 | Add ticker-specific keywords (TSLA, NVDA, etc.) | ⬜ |
| 3.3 | Fine-tune materiality classification | ⬜ |
| 3.4 | Add narrative timeline visualization | ⬜ |

---

## Integration Points

### Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `data_collector.py` | 1A, 1B | News clustering, SPY fetch |
| `analyzer.py` | 1A, 1B | Price context calculation |
| `ai_agent.py` | 1A, 1B, 2 | Prompt updates, narrative parsing |
| `advisor.py` | 2 | Narrative load/save integration |
| `display.py` | 1B | Price trend display |
| `.gitignore` | 2 | Add narratives.json |

### New Files

| File | Phase | Purpose |
|------|-------|---------|
| `src/narrative_manager.py` | 2 | Narrative storage management |
| `config/narratives.json` | 2 | Persistent narrative data |
| `tests/test_news_clustering.py` | 1A | Unit tests for clustering |

---

## Dependencies

### Phase Dependencies
```
Phase 1A (News) ─┬─> Phase 2 (Narratives)
                 │
Phase 1B (Price) ┘
```
- Phase 1A and 1B can run in parallel
- Phase 2 depends on Phase 1A (narrative themes come from news clusters)

### External Dependencies
- None new (yfinance, feedparser already in use)

---

## Testing Checklist

### Phase 1A
- [ ] `classify_headline("DOJ sues Google")` returns "regulatory"
- [ ] `classify_headline("Apple Q4 earnings beat")` returns "earnings"
- [ ] `get_top_themes()` excludes stock_movement and analyst themes
- [ ] Enhanced news shows max 5 themes per stock
- [ ] Frequency detection (HIGH/MEDIUM/LOW) is accurate

### Phase 1B
- [ ] SPY benchmark data fetched successfully
- [ ] 30-day returns match broker/Yahoo Finance (±0.5%)
- [ ] Trend classification boundaries (±3%) work correctly
- [ ] AI reasoning references price trends

### Phase 2
- [x] New narrative created on first detection
- [x] Existing narrative updated on new developments (dedup working)
- [x] Narrative moved to resolved when completed
- [x] Pruning removes 30+ day resolved narratives
- [x] File size stays reasonable (<100KB)

---

## Rollback Plan

### Phase 1A Rollback
```bash
# Revert scan_news_enhanced to scan_news
# Remove clustering functions
# Restore original _format_news()
```

### Phase 1B Rollback
```bash
# Remove price context from prompt
# Skip price calculations in analyzer.py
```

### Phase 2 Rollback
```bash
# Delete narratives.json
# Remove narrative sections from prompt
# Skip narrative parsing/saving
```

---

## Acceptance Criteria

### CR002 Complete When:
- [x] Phase 1A: News clustering active, noise filtered
- [x] Phase 1B: Price context shows stock vs market performance
- [x] Phase 2: Narratives persist across runs
- [ ] All unit tests pass
- [x] Manual testing confirms improved AI reasoning
- [x] No regressions in existing functionality
- [ ] README updated with narratives.json mention

---

## Progress Tracking

| Phase | Status | Progress | Notes |
|-------|--------|----------|-------|
| 1A | ✅ Completed | 13/13 | Enhanced news clustering active |
| 1B | ✅ Completed | 8/8 | Price context vs SPY benchmark active |
| 2 | ✅ Completed | 14/14 | Narrative storage with deduplication |
| 3 | ⬜ Future | 0/4 | Post-MVP refinement |

---

**Last Updated**: January 26, 2026
