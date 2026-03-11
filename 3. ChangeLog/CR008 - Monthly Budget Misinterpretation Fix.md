# Change Request: CR008 - Fix Monthly Budget Misinterpretation by AI Advisor

**Date**: March 11, 2026
**Status**: Open
**Priority**: HIGH
**Severity**: Bug Fix
**Affects**: AI Advisor Recommendations

---

## Problem Description

The AI advisor is incorrectly treating the user's configured **monthly budget** as money that
already exists in the portfolio and is ready to invest. This leads to the advisor suggesting
trades that the user **cannot actually execute** with their current account balance.

**Current Behaviour**:
- User has $887.78 cash in their portfolio
- User has a monthly budget of $300 configured (representing money they *may* deposit each month)
- Advisor recommends a BUY using "$300 from the monthly budget" — subtracting it from the $887.78 as if it were already in the account

**Evidence** (from recommendation recorded on March 11, 2026):
```
"Monthly budget is $300. Using $300 of available cash for position addition.
 Remaining cash after purchase: $887.78 - $300 - $1 fee = $586.78."
```

**What is wrong with this**:
- The $300 monthly budget is **not** part of the $887.78 already in the account
- It represents money the user *might* deposit from their bank — it is a future, potential action
- The advisor is spending money that does not exist yet
- The "remaining cash" calculation is therefore wrong and misleading

**User Impact**:
- The advisor proposes a trade the user cannot execute without first making a deposit
- The cash balance displayed after the recommendation is incorrect — it overstates available funds
- Trust in the advisor's arithmetic is undermined
- User must manually recalculate to understand whether they have enough money to act

---

## What Monthly Budget Actually Means

The `monthly_budget` setting represents the **maximum amount of new external capital** the user
plans to deposit into their brokerage account each month. It is:

- Money that comes from **outside** the portfolio (e.g., from a salary or savings)
- **Not yet in the account** when the advisor runs
- An *intention*, not a fact — the user decides whether to actually make the deposit

Think of it like this: "I set aside up to $300/month for investing. Whether I deposit it this
month depends on whether there is a good reason to."

---

## Expected Behaviour After Fix

### Default (most runs)

The advisor works entirely within the existing portfolio cash and any proceeds from recommended
sales. The monthly budget is not mentioned and does not affect any calculations.

```
Cash Available: $887.78
...
BUY NVDA: $600 — Using existing cash.
Remaining cash: $887.78 - $600 - $1 fee = $286.78
```

### Exception: High-Confidence Opportunity with Insufficient Cash

When the advisor identifies a **high-confidence** investment opportunity but the existing cash
is not enough to take full advantage of it, the advisor **suggests** the user consider making
their monthly deposit — without assuming it will happen.

```
Cash Available: $200.00
...
HOLD — cash is insufficient for a meaningful new position.

[!] Opportunity Note: NVDA is ranked #1 with strong momentum. If you deposit your monthly
    budget of $300, you would have $500 to establish a position. Consider whether this month
    warrants a deposit.
```

The user then decides. The advisor never assumes the deposit has been made.

---

## Success Criteria

| Scenario | Expected Advisor Behaviour |
|----------|---------------------------|
| Normal run, sufficient cash | Monthly budget not mentioned in any calculations |
| Normal run, cash tight but no strong opportunity | Monthly budget not mentioned |
| High confidence opportunity, cash insufficient | Risk warning *suggests* monthly deposit; no BUY recommended using undeposited funds |
| User has already deposited (cash reflects it) | Advisor works with the updated cash balance normally |

---

## Out of Scope

- This CR does **not** add a way for the user to "confirm a deposit" through the CLI
- This CR does **not** change how the portfolio cash balance is tracked or updated
- This CR is a **prompt fix** — the AI's instructions are clarified; no new data or commands are added

---

## Related

- **CR006**: Lot-based position tracking (introduced the detailed cash flow calculations the advisor uses)
- **CR007**: Recommendation ledger (stores recommendation reasoning — the erroneous reasoning is visible there)
