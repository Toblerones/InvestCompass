# Portfolio AI Agent - Implementation Plan

**Version**: 1.0
**Date**: January 25, 2026
**Based on**: ProductRequirement.md v1.0

---

## Overview

This document outlines the sprint-based implementation plan for the Portfolio AI Agent MVP (Phase 1).

**Target Completion**: 2 weeks (4 sprints)

----

## Project Structure

```
InvestCompass/
├── 1. Requirement/
│   └── ProductRequirement.md
├── 2. Plan/
│   └── ImplementationPlan.md
├── App/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── advisor.py           # Main entry point & CLI
│   │   ├── data_collector.py    # Market data fetching
│   │   ├── analyzer.py          # Ranking & technical analysis
│   │   ├── ai_agent.py          # LLM integration (Claude API)
│   │   ├── display.py           # Terminal output formatting
│   │   └── utils.py             # Helper functions
│   ├── config/
│   │   ├── config.json          # Watchlist, budget, settings
│   │   ├── portfolio.json       # Current positions (gitignored)
│   │   └── strategy.txt         # Strategy principles for LLM
│   ├── tests/
│   │   └── __init__.py
│   ├── .env.example
│   └── requirements.txt
├── .gitignore
└── README.md
```

---

## Sprint Breakdown

### Sprint 1: Foundation & Data Layer ✅ COMPLETED
**Duration**: 2-3 days
**Goal**: Project setup and data fetching infrastructure

| ID | Task | Module | Status |
|----|------|--------|--------|
| 1.1 | Create file structure, requirements.txt, .gitignore, .env.example | Setup | ✅ |
| 1.2 | JSON loading/saving, date helpers, validation functions | `utils.py` | ✅ |
| 1.3 | yfinance integration (prices, fundamentals) | `data_collector.py` | ✅ |
| 1.4 | Google News RSS parsing | `data_collector.py` | ✅ |
| 1.5 | Create config.json, portfolio.json schemas and loaders | Config | ✅ |

**Deliverables**:
- [x] Working data fetcher for 10 tech stocks
- [x] Portfolio JSON loading/saving
- [x] Configuration management

---

### Sprint 2: Analysis & AI Layer ✅ COMPLETED
**Duration**: 3-4 days
**Goal**: Ranking algorithm and Claude API integration

| ID | Task | Module | Status |
|----|------|--------|--------|
| 2.1 | Fundamental ranking algorithm (revenue, FCF, P/E, momentum) | `analyzer.py` | ✅ |
| 2.2 | Technical indicators (RSI, SMA, support/resistance) | `analyzer.py` | ✅ |
| 2.3 | FIFO eligibility checker (30-day rule) | `analyzer.py` | ✅ |
| 2.4 | Prompt builder (context + portfolio + strategy) | `ai_agent.py` | ✅ |
| 2.5 | Claude API integration + response parser | `ai_agent.py` | ✅ |

**Deliverables**:
- [x] Stock ranking system (1-10 scale)
- [x] Technical analysis calculations
- [x] Working LLM recommendation engine

---

### Sprint 3: Output & CLI ✅ COMPLETED
**Duration**: 2-3 days
**Goal**: Terminal interface and user workflows

| ID | Task | Module | Status |
|----|------|--------|--------|
| 3.1 | ASCII table formatter, color coding | `display.py` | ✅ |
| 3.2 | Portfolio status, market snapshot, recommendations display | `display.py` | ✅ |
| 3.3 | CLI argument parsing (check, confirm, init) | `advisor.py` | ✅ |
| 3.4 | Main orchestration flow | `advisor.py` | ✅ |
| 3.5 | Trade confirmation workflow (update portfolio.json) | `advisor.py` | ✅ |

**Deliverables**:
- [x] Beautiful terminal output
- [x] Working CLI commands
- [x] Trade confirmation system
 
---

### Sprint 4: Polish & Testing ✅ COMPLETED
**Duration**: 2 days
**Goal**: Error handling, validation, documentation

| ID | Task | Module | Status |
|----|------|--------|--------|
| 4.1 | Error handling (API failures, invalid JSON, retries) | All | ✅ |
| 4.2 | Validation (portfolio schema, action constraints) | `utils.py` | ✅ |
| 4.3 | Strategy principles document | `strategy.txt` | ✅ |
| 4.4 | End-to-end testing | Manual | ✅ |
| 4.5 | README with setup instructions | `README.md` | ✅ |

**Deliverables**:
- [x] Robust error handling with retry logic
- [x] Complete documentation
- [x] Working end-to-end system

---

## Definition of Done (MVP) ✅ ALL COMPLETE

- [x] User can run `python -m src.advisor` and get a recommendation
- [x] User can run `python -m src.advisor check` for quick status
- [x] User can run `python -m src.advisor confirm` to record trades
- [x] System validates 30-day FIFO constraint
- [x] Recommendations include clear reasoning
- [x] All API failures handled gracefully with retry logic

---

## Dependencies

```
yfinance>=0.2.40
anthropic>=0.40.0
feedparser>=6.0.11
pandas>=2.2.0
python-dotenv>=1.0.0
requests>=2.31.0
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| yfinance API changes | Pin version, add retry logic |
| Claude API rate limits | Add caching, exponential backoff |
| RSS parsing failures | Graceful fallback (continue without news) |
| JSON parsing errors | Schema validation, clear error messages |

---

## Notes

- All prices in USD
- All dates in YYYY-MM-DD format
- Portfolio.json should be gitignored (contains personal data)
- .env should be gitignored (contains API keys)

---

**ALL SPRINTS COMPLETED - MVP READY**

Completed: January 26, 2026

---

## Change Requests

| CR ID | Title | Status | Priority | Date |
|-------|-------|--------|----------|------|
| CR001 | Cash Flow Logic Enhancement | Implemented | Medium | 2026-01-26 |

See `3. ChangeLog/` folder for detailed change request documents.
