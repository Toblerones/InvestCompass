# CR014: Prompt Architecture Simplification & Constraint/Judgment Separation

**Version**: 1.0
**Date**: March 27, 2026
**Author**: Tobes (Product Owner)
**Type**: Restructure (no new features)
**Scope**: `ai_agent.py`, `strategy.txt`, output format

---

## 1. Problem Statement

The current strategy prompt is doing two jobs simultaneously:

1. **Rules enforcement** — telling the LLM not to sell locked positions, not to exceed 3 positions, to calculate sequential cash flows, etc.
2. **Judgment guidance** — helping the LLM weigh competing signals and make nuanced decisions.

This causes two failure modes:
- The LLM pattern-matches framework structure without genuinely reasoning through it
- Math errors in sequential cash flow calculation (done by LLM, not code) can produce wrong trade sizes that the user executes

Additionally, the prompt is significantly larger than it needs to be:
- 6 investor profile dimensions are never changed and mostly no-ops for a Moderate investor
- 5 named reasoning frameworks (A/B/C/D/E) produce verbose output the user doesn't read
- Narrative update instructions are complex relative to their actual use

**Goal**: Separate what belongs in Python from what belongs in the prompt. Simplify what remains in the prompt without losing decision quality.

---

## 2. Changes Overview

| Area | Current | After CR014 |
|------|---------|-------------|
| Hard constraints | In strategy.txt, LLM enforces | In Python (`pre_compute_constraints()`), LLM receives facts |
| Cash flow calculation | LLM asked to calculate | Python calculates, LLM receives result |
| Investor profile | 6 dimensions × multi-value definitions in prompt | Single `investor_stance` paragraph injected from config |
| Reasoning frameworks | 5 named frameworks (A/B/C/D/E), narrated step-by-step | 1 compact Decision Guide, judgment only |
| Output reasoning field | Full framework walkthrough | 2–3 sentence plain English justification |
| Narrative updates | Detailed add/update/resolve instruction | Simplified: update summaries only, no structural changes |

---

## 3. Detailed Changes

---

### 3.1 New: `pre_compute_constraints()` in `ai_agent.py`

**Purpose**: Compute all hard constraint states in Python before the prompt is built. The LLM receives facts, not rules.

**Function signature**:
```python
def pre_compute_constraints(portfolio: dict, market_data: dict, config: dict) -> dict:
```

**Returns**:
```python
{
    "stop_loss_breaches": [
        {"ticker": "NVDA", "lot": 1, "purchase_price": 191.83, "current_price": 171.24, "pnl_pct": -10.73, "sellable": True}
    ],
    "earnings_blackouts": {
        "no_sell": [],        # tickers with earnings within 3 days
        "no_buy": []          # tickers with earnings within 7 days
    },
    "sellable_lots": {
        "NVDA": {"sellable_qty": 1, "total_qty": 3, "next_unlock": "2026-04-20"}
    },
    "cash_ratio": 0.79,               # cash / (cash + total position value)
    "framework_e_required": True,     # cash_ratio > 0.50
    "position_count": 1,              # current number of positions
    "max_positions": 3,
    "concentration": {
        "NVDA": 0.21                  # position value / total portfolio value
    }
}
```

**Logic**:
- Stop-loss breach: `(current_price - purchase_price) / purchase_price <= -0.10` AND lot is sellable
- Earnings blackout: compare today's date against earnings calendar from `market_data`
- Cash ratio: `cash / (cash + sum of all position values at current prices)`
- Concentration: `(qty × current_price) / total_portfolio_value`

---

### 3.2 New: `pre_compute_cash_flows()` in `ai_agent.py`

**Purpose**: Calculate available cash after hypothetical SELL actions. Passed to LLM as context — not asked of the LLM.

**Function signature**:
```python
def pre_compute_cash_flows(portfolio: dict, market_data: dict, config: dict) -> dict:
```

**Returns**:
```python
{
    "starting_cash": 666.00,
    "sellable_positions": {
        "NVDA": {
            "sellable_qty": 1,
            "current_price": 171.24,
            "max_proceeds": 170.24    # (1 × 171.24) - 1.00 fee
        }
    },
    "max_deployable": 836.24          # starting_cash + all max_proceeds
}
```

**Note**: The LLM uses this to reason about what it *could* deploy. It does not need to calculate proceeds — it selects actions, and `validate_actions()` confirms the math.

---

### 3.3 New: `build_situation_summary()` in `ai_agent.py`

**Purpose**: Translate constraint dict into plain English injected at the top of the prompt. Replaces the long constraint instruction sections.

**Function signature**:
```python
def build_situation_summary(constraints: dict, cash_flows: dict, portfolio: dict) -> str:
```

**Example output** (injected into prompt):
```
SITUATION SUMMARY (pre-computed — do not recalculate):

Portfolio: 1 position (NVDA), 2 positions available.
Cash: $666.00 (79% of portfolio) — Framework E required: justify deployment or hold.

NVDA: 3 shares held, 1 sellable (2 locked until 2026-04-20).
  ⚠ Lot 1 stop-loss breach confirmed: -10.73% from $191.83. Sellable — eligible for exit.

Cash flows if NVDA Lot 1 sold: $170.24 proceeds → $836.24 available.
No earnings blackouts active.
No earnings-related buy restrictions active.
```

This section is **authoritative**. The LLM must not recalculate or contradict it.

---

### 3.4 Change: Investor Profile → `investor_stance` paragraph

**Current**: 6 dimensions injected with full definitions from strategy.txt Layer 0. Most are no-ops for a Moderate investor.

**After CR014**: A single paragraph generated by `_format_investor_stance()` from config values. Communicates the *net effect* on judgment, not the raw settings.

**Function signature**:
```python
def _format_investor_stance(config: dict) -> str:
```

**Example output for current config** (Moderate / High AI conviction / Medium lock / Moderate buffer / Meaningful / Hold through):
```
INVESTOR STANCE:

You are advising a moderate-risk investor with high conviction in the AI infrastructure
thesis. Treat AI infrastructure positions (NVDA, MSFT, LITE) with thesis-weighted
patience — macro weakness alone does not break the case for these names.

Hold through drawdowns up to -10% (hard stop) without requiring early exit signals.
Prefer a 20-35% cash buffer; cash above 50% requires active justification.
Maximum single position: 40% of portfolio (meaningful portfolio significance).
Accept standard lock periods without reducing averaging scale unless macro is
clearly deteriorating (SPY 30-day return significantly negative).
```

**Config mapping logic** (in `_format_investor_stance()`):

| Setting | Net effect injected |
|---------|-------------------|
| risk_tolerance = Moderate | "Balance growth and preservation. Apply frameworks as designed." |
| ai_thesis_conviction = High | "Weight AI thesis strength heavily. Enter AI names despite RSI > 50 if thesis is actively strengthening." |
| lock_period_comfort = Medium | "Accept lock periods normally. No averaging scale reduction unless macro is clearly deteriorating." |
| cash_buffer_preference = Moderate | "Prefer 20-35% cash. Framework E triggers at >50% cash." |
| portfolio_significance = Meaningful | "Max single position: 40% of portfolio." |
| drawdown_behaviour = Hold through | "Hold through drawdowns to -10% hard stop. No early exit flags." |

**Layer 0 definitions removed from `strategy.txt`** — they move into `_format_investor_stance()` as code logic.

---

### 3.5 Change: Reasoning Frameworks → Compact Decision Guide

**Current**: 5 named frameworks (A/B/C/D/E) with numbered sub-questions, plus a 6-priority Signal Hierarchy block. The LLM narrates through each framework step in its output.

**After CR014**: One compact **Decision Guide** block in `strategy.txt`. Same judgment logic, expressed as a signal priority list + brief decision questions. The LLM reasons through it internally and outputs a plain-English justification — not a framework walkthrough.

**New `strategy.txt` content** (replaces current Layers 1–3):

```
=============================================================
HARD CONSTRAINTS (enforced by system — do not recalculate)
=============================================================
The SITUATION SUMMARY above is authoritative. It tells you:
- Which lots are sellable
- Which stop-losses are breached
- Which tickers have earnings blackouts
- Current cash ratio and whether Framework E applies

Your recommendations must respect these facts. Do not reason around them.

=============================================================
JUDGMENT PRINCIPLES
=============================================================

1. Price drop ≠ thesis broken. Always ask why before acting.
2. Macro weakness (SPY also down) is not a reason to exit a position.
3. Averaging down is valid when weakness is macro-driven and thesis is intact.
4. Cash above 50% is not safe — it has an opportunity cost. Justify it explicitly.
5. Only swap out of a position if your conviction has genuinely weakened — not because something else looks exciting.
6. Monthly deposit budget ($300) is external capital not in the portfolio. Never treat it as available cash.

=============================================================
SIGNAL PRIORITY (resolve conflicts in this order)
=============================================================

1. Hard constraints (from Situation Summary) — always enforced, never reasoned around
2. Material fundamental events (earnings result, guidance change, CEO departure, major contract) — override technical signals
3. Fundamental rank — must be top 3 to enter
4. Thesis integrity — weakening thesis outweighs good technicals
5. Cash buffer and concentration limits
6. Technical timing (RSI, support) — a preference, not a gate

When signals conflict: state which priority level each belongs to and which wins.

=============================================================
DECISION QUESTIONS
=============================================================

Before recommending for each ticker, answer these:

HOLD / EXIT decision:
- Why is it falling — macro or stock-specific?
- Is the thesis intact, weakening, or broken? (count negative signals)
- Is the stop-loss breached? (check Situation Summary)
- Is there a better use of this capital?

AVERAGE DOWN decision:
- Is the weakness macro-driven or stock-specific?
- Has the thesis held or strengthened since entry?
- After averaging, is the new stop-loss still an acceptable loss?
- Does cash ratio support this? (see scale guide below)

NEW ENTRY decision:
- Is it ranked top 3?
- Any material positive or negative catalyst in past 7 days?
- If no material catalyst: is RSI below 50?
- Does it fit the portfolio (positions, concentration)?

CASH DEPLOYMENT (when cash > 50%):
- Can I average down on an existing position with intact thesis? (priority)
- If not: is there a top-3 entry with no active negative catalyst?
- If neither: state explicitly why cash hold is justified and what return is foregone.

AVERAGING DOWN SCALE:
- Cash < 30% of portfolio: small addition only
- Cash 30–60%: moderate addition (up to 30% of available cash)
- Cash > 60%: larger addition warranted (up to 50% of available cash)

=============================================================
INVESTOR STANCE
=============================================================
[Injected dynamically by _format_investor_stance()]
```

---

### 3.6 Change: Output `reasoning` field

**Current**: Full framework walkthrough narrated step-by-step.

**After CR014**: 2–3 sentences covering:
1. What signal drove the recommendation (and its priority level if a conflict was resolved)
2. How the investor stance influenced sizing or timing (if it did)
3. Key risk or condition to watch

**Example — current verbose style**:
> "Framework A Step 1: NVDA is falling. SPY is also down -6.68% over 30 days suggesting macro-driven weakness not stock-specific deterioration. Framework A Step 2: Thesis signals — earnings optimism ongoing, GTC 2026 demand visible. One negative signal (crypto revenue allegations). One signal = monitor. Framework A Step 3: Lot 1 at -10.73%, approaching hard stop..."

**Example — new concise style**:
> "Lot 1 has breached the -10% stop-loss and is sellable. The weakness is partly macro (SPY -6.68%) but the crypto revenue allegation is a stock-specific negative adding to the case for exit. Selling Lot 1 only; Lot 2 remains locked and the NVDA thesis (AI infrastructure demand) is intact for the remaining position."

---

### 3.7 Change: Narrative update instructions

**Current**: Detailed add/update/resolve instruction with boundary rules repeated in the prompt.

**After CR014**: Simplified instruction — the boundary rule is enforced in `narrative_manager.py` on write, not relied on in the prompt.

**New prompt instruction**:
```
NARRATIVE UPDATES:
For each tracked ticker, update the summary of any theme with new market developments.
Keep to market intelligence only (news, analyst views, thesis signals, price levels as
external data). Return updates in the same JSON structure as before.
```

**Code change in `narrative_manager.py`**:
Add `sanitise_narrative_update()` — strips any content that matches portfolio-state patterns (cost basis numbers, share counts, confirmation language) before writing to `narratives.json`. This makes the boundary rule enforcement structural, not prompt-dependent.

```python
def sanitise_narrative_update(update: dict) -> dict:
    """
    Strip portfolio-state content from narrative updates before writing.
    Patterns to detect and remove:
    - "X shares", "X.X shares", "lot N"
    - "stop-loss at $XXX", "stop loss triggered"
    - "average cost $XXX", "cost basis $XXX"
    - "averaging down initiated", "position exited", "trade confirmed"
    - "$XXX cash", "proceeds of $XXX"
    """
    ...
```

---

### 3.8 Change: `validate_actions()` as enforcement layer

**Current**: `validate_actions()` exists but constraint logic is duplicated in the prompt.

**After CR014**: `validate_actions()` becomes the **sole enforcement layer** for hard constraints. Any action that violates a constraint is rejected with a clear error — regardless of what the LLM recommended.

**Validations to enforce in code**:

```python
def validate_actions(actions: list, constraints: dict, cash_flows: dict, config: dict) -> tuple[list, list]:
    """
    Returns (valid_actions, rejected_actions).
    Rejected actions include reason for rejection.
    """
    checks = [
        _check_sell_locked_lot,          # Cannot sell lot held < 30 days
        _check_earnings_sell_blackout,   # Cannot sell within 3 days of earnings
        _check_earnings_buy_blackout,    # Cannot buy within 7 days of earnings
        _check_max_positions,            # Cannot exceed max_positions
        _check_concentration_limit,      # Cannot exceed 40% concentration (Meaningful)
        _check_cash_sufficiency,         # Cannot buy more than available cash
        _check_stop_loss_action,         # If stop-loss breached and sellable: flag if no SELL recommended
    ]
```

If any action is rejected, display a warning in the dashboard:
```
⚠ Action rejected by system constraint: SELL NVDA 2 shares
  Reason: Only 1 share is sellable (FIFO). Lot 2 locked until 2026-04-20.
```

---

## 4. Files Changed

| File | Change type | Description |
|------|-------------|-------------|
| `ai_agent.py` | Modified | Add `pre_compute_constraints()`, `pre_compute_cash_flows()`, `build_situation_summary()`, `_format_investor_stance()`. Update `build_prompt()` to use new sections. Simplify `validate_actions()` using pre-computed constraints. |
| `strategy.txt` | Rewritten | Remove Layer 0 definitions, Layer 1 constraints, Layer 3 framework prose. Replace with compact Decision Guide (signal priority + decision questions + scale guide). |
| `narrative_manager.py` | Modified | Add `sanitise_narrative_update()`. Call it before every narrative write. |
| `display.py` | Modified | Update reasoning display — no longer expects framework narration. Show rejected actions with reason if any. |

---

## 5. Files NOT Changed

| File | Reason |
|------|--------|
| `portfolio.json` | No data model change |
| `config.json` | `investor_profile` keys remain — read by `_format_investor_stance()` |
| `data_collector.py` | No change |
| `analyzer.py` | No change |
| `event_detector.py` | No change |
| `recommendations_manager.py` | No change |
| `advisor.py` | No change to CLI or orchestration |

---

## 6. Prompt Size Reduction (Estimate)

| Section | Current (approx lines) | After CR014 |
|---------|----------------------|-------------|
| Layer 0 investor profile definitions | ~80 | 0 (moved to code) |
| Layer 1 hard constraints | ~30 | 8 (situation summary reference) |
| Layer 2 principles | ~30 | 15 (condensed) |
| Layer 3 frameworks A–E | ~120 | 40 (decision guide) |
| Signal hierarchy | ~30 | 12 (inline in decision guide) |
| Sequential cash flow instruction | ~20 | 0 (moved to code) |
| Narrative boundary rule (repeated) | ~20 | 3 (simplified) |
| **Total strategy content** | **~330 lines** | **~78 lines** |

**Estimated token reduction**: ~60% of strategy content. Faster inference, lower cost, more focused reasoning.

---

## 7. Success Criteria

- [ ] `pre_compute_constraints()` correctly identifies stop-loss breaches, earnings blackouts, sellable lots, cash ratio
- [ ] `build_situation_summary()` produces accurate plain-English summary injected into prompt
- [ ] `_format_investor_stance()` generates correct paragraph from config values — no 6-dimension prose in prompt
- [ ] `validate_actions()` rejects constraint-violating LLM actions and surfaces reason in dashboard
- [ ] `sanitise_narrative_update()` strips portfolio-state content before narrative write
- [ ] LLM reasoning output is 2–3 sentences per action (not framework narration)
- [ ] Recommendations are at least as reliable as pre-CR014 (validate against sim ledger)
- [ ] Prompt token count reduced by ≥50% vs pre-CR014

---

## 8. Out of Scope

- No changes to portfolio data model
- No new CLI commands
- No changes to ranking algorithm or data collection
- No changes to simulation or ledger
- No UI changes

---

**Product Owner**: Tobes
**Date**: March 27, 2026
**Status**: Draft — ready for Claude Code handoff