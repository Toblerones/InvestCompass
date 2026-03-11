# CR008 Implementation Plan: Monthly Budget Misinterpretation Fix

**Created**: March 11, 2026
**Status**: Open
**CR Reference**: `3. ChangeLog/CR008 - Monthly Budget Misinterpretation Fix`

---

## Summary

A prompt-only bug fix. The LLM advisor is misreading `monthly_budget` as investable cash from
the existing portfolio. The fix clarifies the meaning and intent in two places: the LLM prompt
template and the strategy principles file. No new files, no schema changes, no new commands.

---

## Root Cause

Two prompt inputs combine to produce the misinterpretation:

### 1. Vague constraint label — [App/src/ai_agent.py](../App/src/ai_agent.py) line 199

```
- Monthly budget: ${config.get('monthly_budget', 400)}
```

This sits in the `CONSTRAINTS` block alongside operational limits (fees, stop-loss %, max
positions). With no explanation, the LLM treats it as a spending target or deployment cap —
money to allocate from existing cash each month.

### 2. Misleading strategy instruction — [App/config/strategy.txt](../App/config/strategy.txt) line 32

```
- Capital efficiency: Use new monthly capital first, swap only if compelling
```

The LLM reads "use new monthly capital first" as an active directive. It finds the monthly
budget value ($300), interprets it as capital ready to deploy, and uses it as the BUY amount.

Together they create a reasoning chain: *"I have a monthly budget of $300. Strategy says use
it first. → BUY $300 worth."* — without checking whether that $300 is actually in the account.

---

## Files to Modify

### [App/src/ai_agent.py](../App/src/ai_agent.py) — line 199

**Change**: Rename the label and add a usage rule directly in the prompt.

```python
# BEFORE:
- Monthly budget: ${config.get('monthly_budget', 400)}

# AFTER:
- Monthly deposit budget: ${config.get('monthly_budget', 400)} (external capital the user MAY
  deposit from outside — it is NOT currently in the portfolio and must NOT be added to or
  subtracted from available cash. Only reference this in risk_warnings if: (1) confidence=HIGH
  AND (2) existing cash is insufficient for the recommended BUY. In that case include a note
  such as: "Consider depositing your $X monthly budget to fund this position if you wish to
  proceed." Do not recommend a BUY using undeposited budget funds.)
```

Location: inside the `CONSTRAINTS` f-string block in `build_prompt()` (lines 197–202).

---

### [App/config/strategy.txt](../App/config/strategy.txt) — line 32

**Change**: Replace the ambiguous "use monthly capital first" with a conditional, user-prompted
pattern.

```
# BEFORE (line 32):
- Capital efficiency: Use new monthly capital first, swap only if compelling

# AFTER (line 32):
- Capital efficiency: Default to existing cash and swap proceeds. Only when a HIGH confidence
  opportunity exists and existing cash is insufficient, suggest the user consider making their
  monthly deposit to fund the position. Never assume a deposit has been made.
```

---

## What Does NOT Change

| Item | Why unchanged |
|------|---------------|
| `config.json` — `monthly_budget` key | Config key is correct; only the LLM's interpretation of it is wrong |
| `recommendations_manager.py` | Ledger records whatever the LLM produces; fix is upstream |
| `advisor.py` | No command or flow changes needed |
| `display.py` | No display changes needed |
| `recommendations_ledger.json` | Existing entries are unaffected; future entries will have correct reasoning |

---

## Key Design Decisions

### Why fix the prompt, not validate in code?

The bug is in the LLM's understanding of what `monthly_budget` means. Code-side validation
(e.g., checking if a BUY amount exceeds cash) already exists in `validate_actions()` in
`ai_agent.py` (lines 873–885). However, the LLM was using an amount ($300) that happened to
be less than existing cash ($887.78), so no validation warning fired. The root problem is
conceptual, not arithmetic — the fix must be at the prompt level.

### Why not remove `monthly_budget` from the prompt entirely?

It has a legitimate role: when cash is genuinely short and there's a good opportunity, the
advisor should be able to surface it as a prompt to the user. Removing it would eliminate that
capability. The fix retains the value but redefines how and when to use it.

### Conditional mention in `risk_warnings`

Routing deposit suggestions through `risk_warnings` is the cleanest approach:
- It's already displayed prominently to the user
- It does not alter the `actions` array (no phantom BUY action)
- The LLM already knows how to populate this field

---

## Verification

### Manual test — normal run

1. Run `python -m src.advisor` from `App/`
2. Check the printed recommendation output
3. Confirm no BUY action cites "monthly budget" as its cash source
4. Confirm the cash balance in any BUY reasoning starts from the actual `Cash Available` shown

### Manual test — ledger entry

1. After the run, open `App/config/recommendations_ledger.json`
2. Find the latest entry
3. In the `recommendation.actions` array, check each BUY `reasoning` field
4. Must not contain "monthly budget" as a cash source; must reference existing cash or SELL proceeds

### Manual test — deposit suggestion (optional simulation)

1. Temporarily reduce `cash_available` in the portfolio to a low value (e.g., $50) by moving
   cash to a position in `portfolio.json`, then run the advisor
2. With a high-confidence top-ranked opportunity available, the advisor should:
   - NOT recommend a BUY using budget funds
   - Include a note in `risk_warnings` suggesting the user consider a monthly deposit
3. Restore `portfolio.json` after testing

---

## Estimated Effort

| Task | Scope |
|------|-------|
| Edit `ai_agent.py` line 199 | 1 line change + inline clarification text |
| Edit `strategy.txt` line 32 | 1 line rewrite |
| Verification | 5–10 minutes |
| **Total** | **< 30 minutes** |
