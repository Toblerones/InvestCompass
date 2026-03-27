# CR015 Implementation Plan: Replace Hard Stop-Loss with Thesis-Based Exit + Catastrophic Floor

**Created**: March 27, 2026
**Status**: Ready for implementation
**CR Reference**: `3. ChangeLog/CR015 - Replace Hard Stop-Loss with Thesis-Based Exit + Catastrophic Floor.md`

---

## Summary

The -10% hard stop-loss cannot distinguish macro weakness (thesis intact — hold or average down) from fundamental deterioration (thesis broken — exit). In a macro downturn it creates a circular trap: forced sell → cash rises → Framework E → LLM recommends re-entry → loss crystallised, two fees paid, same position re-established.

CR015 splits the single threshold into two:
- **-20% catastrophic floor** (hard constraint, enforced in Python): unconditional exit when any sellable lot hits -20%
- **-10% thesis assessment trigger** (LLM judgment): at -10%, the LLM must assess macro vs fundamental weakness before deciding to hold, average, or exit

---

## Files Modified

| File | Change |
|------|--------|
| [App/config/config.json](../App/config/config.json) | `stop_loss_percent`: -10 → -20 (now represents catastrophic floor) |
| [App/src/ai_agent.py](../App/src/ai_agent.py) | `pre_compute_constraints()`, `build_situation_summary()`, `validate_actions()`, `_format_investor_stance()` |
| [App/config/strategy.txt](../App/config/strategy.txt) | HARD CONSTRAINTS section + DECISION QUESTIONS (add THESIS ASSESSMENT block) |
| [App/src/display.py](../App/src/display.py) | Minor: system-enforced SELL label in `display_recommendations()` |

---

## Change 1: `config.json`

```json
"stop_loss_percent": -20
```

This value now represents the catastrophic floor only. The -10% thesis assessment threshold is hardcoded in `pre_compute_constraints()`.

---

## Change 2: `pre_compute_constraints()` in `ai_agent.py`

Replace the current `stop_loss_threshold` / `stop_loss_breaches` block with two thresholds:

```python
THESIS_ASSESSMENT_THRESHOLD = -0.10   # hardcoded — triggers LLM judgment
catastrophic_threshold = config.get('stop_loss_percent', -20) / 100  # -0.20

# Initialise two lists (before the positions loop):
thesis_assessment_required = []
catastrophic_breaches = []

# Inside the lot loop (replaces current stop-loss check):
pnl_pct = (current_price - purchase_price) / purchase_price

if pnl_pct <= catastrophic_threshold:          # -20% or worse
    catastrophic_breaches.append({
        'ticker': ticker, 'lot': i + 1,
        'purchase_price': purchase_price,
        'current_price': current_price,
        'pnl_pct': round(pnl_pct * 100, 2),
        'sellable': True,
    })
elif pnl_pct <= THESIS_ASSESSMENT_THRESHOLD:   # -10% to -19.9%
    thesis_assessment_required.append({
        'ticker': ticker, 'lot': i + 1,
        'purchase_price': purchase_price,
        'current_price': current_price,
        'pnl_pct': round(pnl_pct * 100, 2),
        'sellable': lot.get('is_sellable', False),
    })
```

**Return dict**: replace `'stop_loss_breaches'` with both new keys:
```python
'thesis_assessment_required': thesis_assessment_required,
'catastrophic_breaches': catastrophic_breaches,
```

Lots at -20% appear only in `catastrophic_breaches` (not both lists). The `elif` ensures mutual exclusivity.

---

## Change 3: `build_situation_summary()` in `ai_agent.py`

Replace the current `constraints['stop_loss_breaches']` block with two new blocks. Catastrophic items appear first (higher urgency):

```python
# Catastrophic floor (hard — system will enforce SELL)
for breach in constraints.get('catastrophic_breaches', []):
    lines.append(
        f"CATASTROPHIC FLOOR: {breach['ticker']} Lot {breach['lot']} at "
        f"{breach['pnl_pct']}% from ${breach['purchase_price']:.2f}. "
        f"Unconditional exit required — system will enforce SELL."
    )

# Thesis assessment trigger (judgment — LLM must assess)
for item in constraints.get('thesis_assessment_required', []):
    status = "Sellable" if item['sellable'] else "Locked"
    lines.append(
        f"THESIS ASSESSMENT REQUIRED: {item['ticker']} Lot {item['lot']} at "
        f"{item['pnl_pct']}% from ${item['purchase_price']:.2f} ({status}). "
        f"Before any recommendation for {item['ticker']}: assess whether this weakness "
        f"is macro-driven or reflects genuine thesis deterioration. "
        f"State conclusion explicitly in reasoning."
    )
```

---

## Change 4: `validate_actions()` in `ai_agent.py`

After the main action loop, enforce the catastrophic floor by injecting a SELL if one is missing:

```python
# Catastrophic floor enforcement — after processing all LLM actions
catastrophic_breaches = constraints.get('catastrophic_breaches', [])
if catastrophic_breaches:
    sell_tickers = {a.get('ticker') for a in valid if a.get('type', '').upper() == 'SELL'}
    for breach in catastrophic_breaches:
        ticker = breach['ticker']
        if ticker not in sell_tickers:
            sellable_qty = constraints.get('sellable_lots', {}).get(ticker, {}).get('sellable_qty', 'all')
            injected = {
                'type': 'SELL',
                'ticker': ticker,
                'amount': f"{sellable_qty} share(s)",
                'reasoning': (
                    f"System-enforced: catastrophic floor breached at "
                    f"{breach['pnl_pct']}% from ${breach['purchase_price']:.2f}. "
                    f"Unconditional exit — no thesis reasoning overrides this."
                ),
                'valid': True,
                'system_enforced': True,
            }
            valid.insert(0, injected)
            sell_tickers.add(ticker)
```

---

## Change 5: `strategy.txt` — two edits

### Edit 1: `HARD CONSTRAINTS` section

Replace:
```
- Hard stop-loss: exit at -10% from entry price when eligible
```
(Currently not present explicitly — was removed in CR014 since it was enforced pre-prompt. The section reference still exists in Layer 1 prose that the LLM reads.)

The current `strategy.txt` has:
```
HARD CONSTRAINTS (enforced by system — do not recalculate)
The SITUATION SUMMARY at the top of this prompt is authoritative. ...
```

Add these two lines to that section:
```
- Catastrophic loss floor: exit at -20% from purchase price when lot is sellable.
  Unconditional — no reasoning overrides this. System enforces automatically.
- At -10% loss: thesis assessment required (see DECISION QUESTIONS). Hold, average,
  or exit only after assessing macro vs fundamental weakness. Not an automatic exit.
```

### Edit 2: `DECISION QUESTIONS` section

Add THESIS ASSESSMENT block before HOLD / EXIT decision:

```
THESIS ASSESSMENT (required when SITUATION SUMMARY shows a lot at -10% or worse):

Before any other reasoning for that ticker, answer:
Is this weakness primarily macro-driven (market-wide selloff, SPY also down,
no stock-specific negative news) — or does it reflect genuine deterioration
in this stock's fundamental thesis?

Use: recent news, ranking movement, price vs SPY, earnings results,
analyst sentiment, active narratives.

Macro-driven, thesis intact → hold or average down (explain why)
Thesis deteriorating → recommend exit (state which signals support this)
Uncertain → hold, flag explicitly, reassess next run

Your conclusion must appear in the action reasoning field.
```

---

## Change 6: `_format_investor_stance()` in `ai_agent.py`

The `'Hold through'` drawdown wording currently references the old -10% hard stop. Update:

```python
# Before:
'Hold through': 'Hold through drawdowns to the -10% hard stop. No early exit flags.',

# After:
'Hold through': (
    'Hold through drawdowns unless thesis assessment concludes deterioration. '
    'No early exit flags — catastrophic floor at -20% is the only unconditional stop.'
),
```

---

## Change 7: `display.py` — system-enforced SELL label

In `display_recommendations()`, update the action rendering to distinguish system-enforced SELLs:

```python
# Before the print statement in the actions loop:
if action.get('system_enforced'):
    type_str = colorize("SELL", Colors.RED + Colors.BOLD)
    print(f"\n  {i}. [SYSTEM] {type_str} {colorize(ticker, Colors.BOLD)} - {amount}")
    print(colorize("     Catastrophic floor — system-enforced exit.", Colors.RED))
else:
    print(f"\n  {i}. [{status_icon}] {type_str} {colorize(ticker, Colors.BOLD)} - {amount}")
```

---

## What Does Not Change

- Portfolio data model (`portfolio.json`)
- All other config keys
- Data collection, analyzer, event detection, narrative manager
- Simulation, ledger, CLI commands

---

## Verification

1. Confirm `config.json` reads `stop_loss_percent: -20`
2. Run `cd App && python -m src.advisor run --manual`
3. With NVDA at -10.73% (current scenario):
   - SITUATION SUMMARY shows `THESIS ASSESSMENT REQUIRED: NVDA Lot 1 at -10.73%`
   - No `CATASTROPHIC FLOOR` line
   - LLM reasoning contains explicit thesis conclusion
4. To test catastrophic floor: temporarily set a lot's `purchase_price` higher in `portfolio.json` to push P&L below -20%, then run:
   - SITUATION SUMMARY shows `CATASTROPHIC FLOOR: ...`
   - Even if LLM doesn't recommend SELL, `validate_actions()` injects one
   - Terminal shows `[SYSTEM] SELL` label in red
5. Reset `portfolio.json` to real values
