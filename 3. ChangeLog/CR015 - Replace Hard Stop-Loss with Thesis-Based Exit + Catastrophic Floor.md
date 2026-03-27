# CR015: Replace Hard Stop-Loss with Thesis-Based Exit + Catastrophic Floor

**Version**: 1.0
**Date**: March 27, 2026
**Author**: Tobes (Product Owner)
**Type**: Strategy change
**Scope**: `strategy.txt`, `ai_agent.py` (`pre_compute_constraints()`), `validate_actions()`

---

## 1. Problem Statement

The current -10% hard stop-loss is a price-based rule that cannot distinguish between:
- A stock down due to market-wide macro weakness (thesis intact — hold or average down)
- A stock down due to genuine fundamental deterioration (thesis broken — exit)

This creates a circular failure pattern in macro downturns:
1. Hard stop triggers → forced sell
2. Cash ratio rises above 50% → Framework E triggers
3. LLM recommends re-entry into the same stock (intact thesis, excess cash)
4. Net result: loss crystallised, two transaction fees paid, same position re-established

The -10% rule was intended to prevent emotional bagholding on broken theses. That is a
judgment problem, not a price problem. It should be solved by LLM reasoning, not a
price threshold.

---

## 2. Design Principles

**If you can enumerate it, put it in code. If it requires open-ended judgment, use the LLM.**

The thesis assessment at -10% cannot be reduced to a decision tree — market conditions,
news context, competitive signals, and macro correlation are open-ended. This is exactly
the problem the LLM is for.

The catastrophic floor at -20% is unconditional and belongs in code — no judgment required.

---

## 3. Changes

---

### 3.1 Remove: -10% hard stop-loss from Layer 1 constraints

The -10% hard stop-loss is removed from `strategy.txt` Layer 1 and from
`pre_compute_constraints()` stop-loss breach detection.

It is replaced by a thesis assessment trigger (Layer 3 judgment) and a -20%
catastrophic floor (Layer 1 hard constraint).

---

### 3.2 Add: -20% catastrophic floor (Layer 1 hard constraint)

**Rule**: If any sellable lot is at or below -20% from its purchase price, the system
must recommend SELL regardless of thesis, macro context, or any other signal.

**Implementation — `pre_compute_constraints()`**:

```python
"catastrophic_breaches": [
    {
        "ticker": "NVDA",
        "lot": 1,
        "purchase_price": 191.83,
        "current_price": 153.46,   # example at -20%
        "pnl_pct": -20.0,
        "sellable": True
    }
]
```

**Implementation — `validate_actions()`**:
Add `_check_catastrophic_floor()`. If a catastrophic breach exists for a sellable lot
and no SELL action is recommended for that ticker, inject a SELL action and log:

```
⚠ Catastrophic floor breached: NVDA Lot 1 at -20.0%. Sell action enforced.
```

**Implementation — `build_situation_summary()`**:
If catastrophic breach exists, surface it prominently:

```
🔴 CATASTROPHIC FLOOR: NVDA Lot 1 at -20.0% from $191.83. Unconditional exit required.
```

**`strategy.txt` Layer 1 addition**:
```
- Catastrophic loss floor: exit at -20% from purchase price when lot is sellable.
  This is unconditional — no thesis reasoning overrides it.
```

---

### 3.3 Add: Thesis Assessment trigger at -10% (Layer 3 judgment)

**Rule**: When any held lot reaches -10% or worse, the LLM must perform a thesis
assessment for that position before making any other recommendation. This assessment
drives the hold/average/exit decision for that ticker.

**Implementation — `pre_compute_constraints()`**:

Rename `stop_loss_breaches` to `thesis_assessment_required`:

```python
"thesis_assessment_required": [
    {
        "ticker": "NVDA",
        "lot": 1,
        "purchase_price": 191.83,
        "current_price": 171.24,
        "pnl_pct": -10.73,
        "sellable": True
    }
]
```

**Implementation — `build_situation_summary()`**:

```
⚠ THESIS ASSESSMENT REQUIRED: NVDA Lot 1 at -10.73%.
  Before recommending any action for NVDA, assess whether this weakness is
  macro-driven or reflects genuine deterioration in the investment thesis.
  Use all available news, rankings, price context, and narratives to form
  this judgment. Your recommendation must state your conclusion explicitly.
```

**`strategy.txt` Decision Guide addition** (under DECISION QUESTIONS):

```
THESIS ASSESSMENT (required when any lot is at -10% or worse):

Before any other reasoning for this ticker, answer:
Is this weakness primarily macro-driven (market-wide selloff, SPY also down,
no stock-specific negative news) — or does it reflect genuine deterioration
in this stock's fundamental thesis?

Use all available context: recent news, ranking movement, price vs SPY,
earnings results, analyst sentiment, ongoing narratives.

If macro-driven, thesis intact → hold or average down
If thesis deteriorating → exit (specify what signals support this)
If uncertain → hold, flag explicitly, reassess next run

Your reasoning for this assessment must appear in the action's reasoning field.
```

---

### 3.4 Update: `strategy.txt` Layer 1

**Remove**:
```
- Hard stop-loss: exit at -10% from entry price when eligible
```

**Add**:
```
- Catastrophic loss floor: exit at -20% from purchase price when lot is sellable.
  Unconditional — no reasoning overrides this.
- At -10% loss: thesis assessment required (see Decision Guide). Exit only if
  LLM judges thesis to be deteriorating. This is a judgment trigger, not a hard exit.
```

---

### 3.5 Update: Circular trap prevention

The combination of these two changes eliminates the circular trap by design:

- In a macro downturn with intact thesis: LLM assesses → holds or averages down →
  no forced sell → no excess cash → Framework E does not trigger spuriously
- With a broken thesis: LLM assesses → recommends exit → cash rises →
  Framework E correctly evaluates whether re-entry into the same name is warranted
  (it will not be, because thesis is broken → rank will reflect this)

No additional code change needed — the logic follows naturally from the thesis assessment.

---

## 4. Files Changed

| File | Change | Description |
|------|--------|-------------|
| `strategy.txt` | Modified | Remove -10% hard stop from Layer 1. Add -20% catastrophic floor to Layer 1. Add thesis assessment block to Decision Guide. |
| `ai_agent.py` | Modified | `pre_compute_constraints()`: rename `stop_loss_breaches` → `thesis_assessment_required`, add `catastrophic_breaches`. `build_situation_summary()`: surface thesis assessment prompt and catastrophic floor warning. |
| `ai_agent.py` | Modified | `validate_actions()`: add `_check_catastrophic_floor()`. Remove old stop-loss enforcement. |

---

## 5. Files NOT Changed

| File | Reason |
|------|--------|
| `portfolio.json` | No data model change |
| `config.json` | `stop_loss_percent` key remains — now used only for -20% floor. Update value from -10 to -20. |
| `data_collector.py` | No change |
| `analyzer.py` | No change |
| `display.py` | Minor: catastrophic floor warning display (reuses existing warning style) |
| `narrative_manager.py` | No change |
| `recommendations_manager.py` | No change |

---

## 6. Config Change

In `config.json`, update:
```json
"stop_loss_percent": -20
```

This value now represents the catastrophic floor, not the old hard stop.

---

## 7. Success Criteria

- [ ] A lot at -10% triggers thesis assessment prompt in situation summary
- [ ] A lot at -20% triggers unconditional SELL in validate_actions(), regardless of LLM output
- [ ] In a macro downturn scenario (SPY down, thesis intact), LLM recommends hold or average — not sell
- [ ] In a broken thesis scenario (rank drop + negative catalyst), LLM recommends exit
- [ ] Circular trap (sell → excess cash → rebuy same stock) does not occur in macro downturn simulation
- [ ] LLM reasoning field explicitly states thesis assessment conclusion for any -10%+ position

---

## 8. Relationship to CR014

CR015 is independent of CR014 but complementary. Both can be implemented in either order.

CR014 moves constraint enforcement into Python. CR015 changes which constraints exist
and replaces one hard constraint with a judgment trigger. Together they produce a system
where:

- **Code enforces**: 30-day hold, earnings blackouts, -20% catastrophic floor,
  position limits, concentration limits, cash flow math
- **LLM judges**: thesis integrity, macro vs stock-specific weakness, signal
  weighting, averaging scale, entry timing

---

**Product Owner**: Tobes
**Date**: March 27, 2026
**Status**: Draft — ready for Claude Code handoff