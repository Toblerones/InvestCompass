# CR013 Implementation Plan: Personal Investor Profile

**Created**: March 20, 2026
**Status**: Implemented
**CR Reference**: `3. ChangeLog/CR013 - Personal Investor Profile Encoding Investor Personality into Recommendations.md`

---

## Summary

The advisor produced technically correct but generic recommendations — valid for a moderate-risk
investor, but not personalised for the actual user. CR013 adds a Layer 0 investor profile that
shapes every judgment call in Layers 2 and 3. Profile values live in `config.json` (matching the
existing pattern for all user-tunable settings) and are injected into the prompt by `ai_agent.py`
as a formatted block. The Layer 0 definitions (what each value means and how it modifies
framework thresholds) live in `strategy.txt`.

---

## Files Modified

### 1. [App/config/config.json](../App/config/config.json)

Added `investor_profile` object with 6 dimensions and default values:

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

**Valid values:**
| Dimension | Options |
|---|---|
| risk_tolerance | Conservative / Moderate / Aggressive |
| ai_thesis_conviction | Low / Medium / High |
| lock_period_comfort | Low / Medium / High |
| cash_buffer_preference | Minimal / Moderate / Substantial |
| portfolio_significance | Discretionary / Meaningful / Primary |
| drawdown_behaviour | Hold through / Tighten gradually / Exit early |

---

### 2. [App/src/ai_agent.py](../App/src/ai_agent.py)

**Change 1** — New helper `_format_investor_profile(config)` added alongside existing
`_format_positions`, `_format_rankings`, etc. Reads `investor_profile` from config with
graceful fallback to defaults for any missing key.

**Change 2** — Call added in `build_prompt()`:
```python
profile_text = _format_investor_profile(config)
```

**Change 3** — New `INVESTOR PROFILE` section injected at the top of the prompt string,
before `STRATEGY PRINCIPLES`. The LLM sees the active values immediately, then reads the
Layer 0 definitions in the strategy document for interpretation.

**Change 4** — One line added to YOUR TASK section:
```
Apply the investor profile from Layer 0 to all framework outputs — adjust thresholds and
sizing as defined. State profile influence explicitly in reasoning when it moderates a decision.
```

---

### 3. [App/config/strategy.txt](../App/config/strategy.txt)

Added Layer 0 section before Layer 1. Contains definitions for all 6 profile dimensions with
explicit framework modification rules per setting (e.g. Conservative → Framework B max 20% of
cash, Framework E triggers at >40%, Framework C requires RSI < 45). Ends with an INVESTOR
PROFILE CHECK instruction mirroring CR011's narrative boundary check pattern.

---

## How to Change Your Profile

Edit `App/config/config.json` — change any value in `investor_profile`:
```json
"risk_tolerance": "Conservative"   // was "Moderate"
```
The next run will pick up the change automatically. No code changes needed.

---

## What Does Not Change

- Layer 1 hard constraints — never overridden by profile
- Signal hierarchy (CR010) — profile modifies thresholds, not priority order
- Narrative boundary rule (CR011) — unchanged
- Framework logic — unchanged; profile adjusts parameters within frameworks
- Response JSON format — unchanged; profile influence stated in reasoning field
- All other code files — unchanged

---

## Verification

1. Set `config.json` `risk_tolerance` to `"Conservative"`
2. Run `python -m src.advisor --manual` from `App/`
3. Open `output/prompt_YYYYMMDD_HHMMSS.md` — confirm:
   - `INVESTOR PROFILE` block appears at top showing `Risk Tolerance: Conservative`
   - Layer 0 section visible in STRATEGY PRINCIPLES with all 6 dimension definitions
4. With Conservative + current NVDA position (-6.9%, macro weakness):
   - Framework B max should be 20% of cash (~$255, ~1 share) — not 50%
   - Advisor should explicitly cite Conservative risk tolerance in reasoning
5. Reset to `"Moderate"` — confirm prompt reflects the change
6. Remove `investor_profile` key entirely from config — confirm all 6 defaults applied
