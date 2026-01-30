# Change Request: CR006 - Lot-Based Position Tracking

**Date**: January 30, 2026
**Status**: Open
**Priority**: URGENT
**Severity**: Critical (Blocking Correct Operation)
**Affects**: Portfolio data model, all downstream features

---

## Problem Description

The current portfolio structure treats each purchase as a separate position, causing **critical failures** in position tracking, validation, and display when the same stock is purchased multiple times.

**Discovered Issue**:
User purchased MSFT twice (different dates, different prices). The system now shows:
- 3 positions instead of 2 stocks
- "0 sellable, 3 locked" when 1 lot is actually sellable
- MSFT appears twice in every section (portfolio status, price context, recommendations)
- Validation incorrectly flags sellable shares as locked
- AI analyzes the same stock separately, creating confused recommendations

**Example of broken output**:
```
PORTFOLIO STATUS:
MSFT  1.5  507.60  -14.60%  73 days  SELLABLE [STOP LOSS]
NVDA  1.0  191.83  +0.35%    0 days  LOCKED
MSFT  1.0  434.00  -0.12%    0 days  LOCKED  ← DUPLICATE ENTRY

Positions: 0 sellable, 3 locked  ← WRONG COUNT

PRICE CONTEXT:
MSFT  -11.00% vs SPY  [UNDERPERFORMING]
NVDA  +2.28% vs SPY  [NEUTRAL]
MSFT  -11.00% vs SPY  [UNDERPERFORMING]  ← DUPLICATE

RECOMMENDATION:
SELL MSFT - 1.5 shares
[!] INVALID: MSFT is LOCKED  ← WRONG (Lot 1 is sellable!)
```

**Impact**:
- ❌ Portfolio count misleading (3 positions vs 2 stocks held)
- ❌ Sellability validation broken (blocks valid sell orders)
- ❌ Display cluttered (same stock appears multiple times)
- ❌ AI confused (treats lots as separate investments)
- ❌ Stop-loss ambiguous (lot-level vs position-level unclear)
- ❌ Cannot accurately track concentration risk (MSFT is 53% but appears as two entries)

**Root Cause**:
The data model treats each purchase as an independent position rather than recognizing that multiple purchases of the same stock constitute **one position with multiple tax lots**. This is fundamentally incompatible with real-world portfolio management and regulatory requirements (FIFO).

---

## Current Behavior

### Portfolio Data Structure
```json
{
  "positions": [
    {
      "ticker": "MSFT",
      "quantity": 1.5,
      "purchase_price": 507.6,
      "purchase_date": "2025-11-18",
      "notes": "Initial position"
    },
    {
      "ticker": "NVDA",
      "quantity": 1.0,
      "purchase_price": 191.83,
      "purchase_date": "2026-01-30"
    },
    {
      "ticker": "MSFT",
      "quantity": 1.0,
      "purchase_price": 434.0,
      "purchase_date": "2026-01-30"
    }
  ],
  "cash_available": 274.17,
  "last_updated": "2026-01-30"
}
```

**Problems**:
1. MSFT appears twice (confusing, error-prone)
2. No concept of "total position" (how much MSFT total?)
3. No weighted average cost (what's real cost basis?)
4. FIFO order implicit (relies on array order, fragile)
5. Sellability checking complex (must scan for all matching tickers)

---

### Display Output
```
Portfolio Status:
Ticker   Qty   Entry    Current   P&L      Days  Status
--------------------------------------------------------
MSFT     1.5   507.60   433.50   -14.60%   73   SELLABLE
NVDA     1.0   191.83   192.51   +0.35%     0   LOCKED
MSFT     1.0   434.00   433.50   -0.12%     0   LOCKED

Portfolio: 3 positions
Sellable: 0 positions
Locked: 3 positions
```

**Problems**:
- User holds 2 stocks, display shows 3 positions
- "0 sellable" is false (MSFT Lot 1 is sellable)
- Concentration risk hidden (MSFT is 53% but looks like 2 separate holdings)
- Total MSFT exposure unclear (must mentally add 1.5 + 1.0)

---

### Validation Logic
```
Action: SELL MSFT - 1.5 shares

Validation result: 
[!] INVALID: MSFT is LOCKED (held 0 days). 
    Cannot sell until 2026-03-02.
```

**Problem**:
- System sees ANY MSFT lot is locked, flags entire position as unsellable
- Ignores that Lot 1 (1.5 shares, 73 days) is SELLABLE
- Validation doesn't understand FIFO (can sell up to 1.5 shares from oldest lot)

---

### AI Context
```
You hold:
- MSFT: 1.5 shares @ $507.60, -14.6%, 73 days (sellable)
- NVDA: 1.0 shares @ $191.83, +0.4%, 0 days (locked)
- MSFT: 1.0 shares @ $434.00, -0.1%, 0 days (locked)
```

**Problems**:
- AI sees MSFT twice, analyzes separately
- No awareness of combined position (2.5 total shares)
- No weighted average cost ($478.08 blended)
- Recommendations treat lots independently instead of as unified position

---

## Expected Behavior

### Portfolio Data Structure (Lot-Based)
```json
{
  "positions": [
    {
      "ticker": "MSFT",
      "total_quantity": 2.5,
      "average_cost": 478.08,
      "current_value": 1083.75,
      "total_pnl_percent": -9.3,
      "lots": [
        {
          "lot_id": 1,
          "quantity": 1.5,
          "purchase_price": 507.6,
          "purchase_date": "2025-11-18",
          "days_held": 73,
          "status": "SELLABLE",
          "pnl_percent": -14.6,
          "notes": "Initial position"
        },
        {
          "lot_id": 2,
          "quantity": 1.0,
          "purchase_price": 434.0,
          "purchase_date": "2026-01-30",
          "days_held": 0,
          "status": "LOCKED",
          "unlock_date": "2026-03-01",
          "pnl_percent": -0.1
        }
      ]
    },
    {
      "ticker": "NVDA",
      "total_quantity": 1.0,
      "average_cost": 191.83,
      "current_value": 192.51,
      "total_pnl_percent": 0.35,
      "lots": [
        {
          "lot_id": 1,
          "quantity": 1.0,
          "purchase_price": 191.83,
          "purchase_date": "2026-01-30",
          "days_held": 0,
          "status": "LOCKED",
          "unlock_date": "2026-03-01",
          "pnl_percent": 0.35
        }
      ]
    }
  ],
  "cash_available": 274.17,
  "last_updated": "2026-01-30"
}
```

**Benefits**:
1. ✅ Each ticker appears once (clean structure)
2. ✅ Total position size clear (2.5 MSFT shares)
3. ✅ Weighted average cost calculated (blended cost basis)
4. ✅ FIFO lots explicit (array order defines sell order)
5. ✅ Lot-level and position-level P&L both available

---

### Display Output (Consolidated View)
```
Portfolio Status:
Ticker   Qty   Avg Cost  Current   P&L      Status
----------------------------------------------------
MSFT     2.5   478.08    433.50   -9.3%    PARTIAL LOCK
  ├─ Lot 1: 1.5 @ 507.60 (73d, -14.6%)    ✓ SELLABLE [STOP LOSS]
  └─ Lot 2: 1.0 @ 434.00 (0d, -0.1%)      🔒 LOCKED (29 days)

NVDA     1.0   191.83    192.51   +0.4%    LOCKED
  └─ Lot 1: 1.0 @ 191.83 (0d, +0.4%)      🔒 LOCKED (29 days)
----------------------------------------------------

Portfolio Summary:
Total Value: $1,276
Cash: $274
Total P&L: -8.0%

Positions: 2 stocks (MSFT, NVDA)
  - Fully sellable: 0
  - Partially sellable: 1 (MSFT: 1.5 of 2.5 shares sellable)
  - Fully locked: 1 (NVDA)

Sellable value: $650 (MSFT Lot 1)
Locked value: $626 (MSFT Lot 2 + NVDA)
Next unlock: 2026-03-01 (29 days)
```

**Benefits**:
- Clear position count (2 stocks)
- Total exposure visible (2.5 MSFT = 53% concentration)
- Lot details available when needed (expandable view)
- Accurate sellability status
- FIFO order explicit (Lot 1 before Lot 2)

---

### Validation Logic (FIFO-Aware)
```
Action: SELL MSFT - 1.5 shares

Validation result:
[✓] VALID: Can sell 1.5 shares from Lot 1 (FIFO compliant)
    
    FIFO breakdown:
    - Lot 1 (1.5 shares, 73 days held): SELLABLE ✓
    - Lot 2 (1.0 shares, 0 days held): LOCKED 🔒
    
    Selling 1.5 shares will:
    - Close Lot 1 completely
    - Leave Lot 2 (1.0 shares) remaining
    - Reduce total MSFT position: 2.5 → 1.0 shares
    - Proceeds: ~$650 (after $1 fee)
```

**Benefits**:
- Validation understands FIFO (checks sellable quantity correctly)
- Clear messaging (what's being sold, what remains)
- Position impact visible (before/after state)

---

### AI Context (Consolidated Position)
```
Your current holdings:

MSFT: 2.5 shares total
  Average cost: $478.08
  Current price: $433.50
  Total P&L: -9.3% (-$111)
  Portfolio weight: 53% (CONCENTRATED RISK)
  
  Lot breakdown:
  - Lot 1 (1.5 shares, 73 days old): -14.6%, SELLABLE
    → STOP-LOSS TRIGGERED (-10% threshold exceeded)
    → Eligible for immediate sale
  
  - Lot 2 (1.0 shares, 0 days old): -0.1%, LOCKED
    → Cannot sell for 29 more days
    → Essentially at breakeven
  
  FIFO constraint: Must sell Lot 1 before Lot 2
  
NVDA: 1.0 shares total
  Average cost: $191.83
  Current price: $192.51
  Total P&L: +0.4%
  Portfolio weight: 8%
  Status: LOCKED (29 days remaining)
```

**Benefits**:
- AI sees total position (2.5 shares, 53% concentration)
- Lot dynamics clear (Lot 1 losing, Lot 2 neutral)
- FIFO implications understood (must sell losing lot first)
- Recommendations can be position-aware (reduce concentration, exit losing lot)

---

## Proposed Solution

### Core Concept: Position-Lot Hierarchy

**Mental model**: 
- **Position** = All shares of a single stock (e.g., "MSFT position")
- **Lot** = A specific purchase transaction (e.g., "bought 1.5 shares on Nov 18")

**Structure**:
- User holds **positions** (MSFT, NVDA)
- Each position contains one or more **lots** (purchase transactions)
- Display shows positions (consolidated view)
- Lots tracked underneath (tax/FIFO compliance)

---

### Feature 1: Consolidated Position View

**What user sees**:
- Portfolio shows 2 positions (MSFT, NVDA) not 3 entries
- Total quantity per stock (2.5 MSFT shares)
- Weighted average cost (blended cost basis: $478.08)
- Combined P&L (position-level: -9.3%)
- Lot details available on demand (expandable/detailed view)

**Benefits**:
- Clear portfolio composition (what stocks do I own?)
- Accurate concentration risk (MSFT is 53%, not hidden across entries)
- Professional display (matches industry standard)

---

### Feature 2: FIFO Lot Tracking

**What system tracks**:
- Lots ordered by purchase date (FIFO sequence)
- Each lot has: quantity, cost, date, lock status
- Lot IDs for reference (Lot 1, Lot 2, etc.)
- Days held per lot (determines sellability)
- Unlock dates (when each lot becomes sellable)

**Benefits**:
- Regulatory compliance (FIFO enforced automatically)
- Tax lot accounting (ready for tax reporting)
- Clear sellability (know exactly which shares can be sold)

---

### Feature 3: Weighted Average Cost

**What system calculates**:
```
Average Cost = (Lot1_Qty × Lot1_Price + Lot2_Qty × Lot2_Price) / Total_Qty

Example MSFT:
= (1.5 × $507.60 + 1.0 × $434.00) / 2.5
= ($761.40 + $434.00) / 2.5
= $1,195.40 / 2.5
= $478.16
```

**Benefits**:
- Single cost basis for position (simpler P&L calculation)
- Industry standard metric (matches broker statements)
- Useful for performance tracking

---

### Feature 4: Multi-Level P&L

**What system shows**:
- **Position-level P&L**: Blended performance (MSFT: -9.3%)
- **Lot-level P&L**: Individual lot performance (Lot 1: -14.6%, Lot 2: -0.1%)

**Use cases**:
- Position P&L: Overall investment performance
- Lot P&L: Tax loss harvesting decisions, stop-loss triggers

**Benefits**:
- Flexibility (see big picture or detail)
- Stop-loss clarity (lot-specific triggers)

---

### Feature 5: Accurate Sellability

**What system determines**:
- Sellable quantity: Sum of all SELLABLE lots (FIFO order)
- Locked quantity: Sum of all LOCKED lots
- Partial sellability: Some lots sellable, others locked

**Display**:
```
MSFT Status: PARTIAL LOCK
  - Can sell: 1.5 shares (Lot 1)
  - Cannot sell: 1.0 shares (Lot 2, locked 29 days)
  
NVDA Status: FULLY LOCKED
  - Can sell: 0 shares
  - Cannot sell: 1.0 shares (locked 29 days)
```

**Benefits**:
- User knows exactly what can be sold
- AI recommendations respect FIFO constraints
- Validation accurate (no false positives/negatives)

---

### Feature 6: Position Impact Preview

**What system shows before selling**:
```
Sell action: MSFT - 1.5 shares

Current state:
  MSFT: 2.5 shares, 53% of portfolio
  
After sell:
  MSFT: 1.0 shares, 18% of portfolio
  Cash: $924 (from $274)
  
Position impact:
  - Closes Lot 1 completely (exit losing position)
  - Retains Lot 2 (keep breakeven lot)
  - Reduces concentration (53% → 18%)
```

**Benefits**:
- User understands portfolio changes before committing
- Position sizing decisions clearer
- Concentration risk management visible

---

## User Impact

### Scenario 1: Viewing Portfolio

**Before** (current broken state):
```
You see 3 positions listed
MSFT appears twice (confusing)
Must mentally add 1.5 + 1.0 to know total MSFT
Status says "0 sellable" (wrong)
```

**After** (lot-based tracking):
```
You see 2 positions (MSFT, NVDA)
MSFT shows 2.5 shares total (clear)
Lot breakdown available if you want detail
Status says "1 partially sellable" (correct)
```

**User benefit**: Clean, accurate portfolio view

---

### Scenario 2: Selling Shares

**Before**:
```
You want to sell MSFT
System flags: "MSFT is LOCKED" (wrong)
You're confused (Lot 1 should be sellable)
Can't proceed with valid sell order
```

**After**:
```
You want to sell 1.5 MSFT shares
System validates: "Can sell 1.5 shares from Lot 1 (FIFO)"
Shows: "Will close Lot 1, keep Lot 2"
Proceeds smoothly with correct validation
```

**User benefit**: Valid trades execute, no false blocks

---

### Scenario 3: AI Recommendations

**Before**:
```
AI sees MSFT twice, gets confused
Recommends selling but validation fails
Reasoning treats lots as separate investments
No awareness of total position size
```

**After**:
```
AI sees combined MSFT position (2.5 shares, -9.3%)
Understands Lot 1 triggered stop-loss, Lot 2 is fine
Recommends: "Sell 1.5 shares (Lot 1) to exit losing position"
Reasoning: "Reduces concentration, keeps profitable Lot 2"
```

**User benefit**: Smarter, clearer recommendations

---

### Scenario 4: Monthly DCA Investing

**Before**:
```
Month 1: Buy NVDA (1 entry)
Month 2: Buy NVDA again (2nd entry)
Month 3: Buy NVDA again (3rd entry)
Result: NVDA appears 3 times, display is chaos
```

**After**:
```
Month 1: Buy NVDA (creates NVDA position with Lot 1)
Month 2: Buy NVDA again (adds Lot 2 to NVDA position)
Month 3: Buy NVDA again (adds Lot 3 to NVDA position)
Result: NVDA appears once with 3 lots underneath
```

**User benefit**: Clean structure scales naturally with DCA strategy

---

## Success Metrics

### Correctness (Critical)
- [ ] Portfolio displays correct number of stocks (2, not 3)
- [ ] Sellability validation is accurate (no false positives/negatives)
- [ ] Position count correct ("1 partially sellable" not "0 sellable")
- [ ] AI receives consolidated position data (no duplicate MSFT entries)
- [ ] FIFO order enforced (oldest lot sold first automatically)

### Usability (High Priority)
- [ ] User can understand total position at a glance (2.5 MSFT shares)
- [ ] Lot details accessible when needed (expandable view)
- [ ] Weighted average cost displayed (blended cost basis)
- [ ] Concentration risk visible (MSFT 53% obvious, not hidden)
- [ ] Stop-loss triggers clear (lot-level vs position-level)

### Maintainability (Medium Priority)
- [ ] Adding new lot is simple (append to lots array)
- [ ] Selling lot updates correctly (removes or reduces lot)
- [ ] Data structure is self-documenting (clear hierarchy)
- [ ] Portfolio editable manually if needed (JSON is readable)

---

## Migration Strategy

### One-Time Conversion

**Input** (current broken format):
```json
{
  "positions": [
    {"ticker": "MSFT", "quantity": 1.5, "purchase_price": 507.6, "purchase_date": "2025-11-18"},
    {"ticker": "NVDA", "quantity": 1.0, "purchase_price": 191.83, "purchase_date": "2026-01-30"},
    {"ticker": "MSFT", "quantity": 1.0, "purchase_price": 434.0, "purchase_date": "2026-01-30"}
  ]
}
```

**Output** (lot-based format):
```json
{
  "positions": [
    {
      "ticker": "MSFT",
      "total_quantity": 2.5,
      "average_cost": 478.08,
      "lots": [
        {"lot_id": 1, "quantity": 1.5, "purchase_price": 507.6, "purchase_date": "2025-11-18"},
        {"lot_id": 2, "quantity": 1.0, "purchase_price": 434.0, "purchase_date": "2026-01-30"}
      ]
    },
    {
      "ticker": "NVDA",
      "total_quantity": 1.0,
      "average_cost": 191.83,
      "lots": [
        {"lot_id": 1, "quantity": 1.0, "purchase_price": 191.83, "purchase_date": "2026-01-30"}
      ]
    }
  ]
}
```

**Process**:
1. User runs: `python advisor.py migrate`
2. System backs up current portfolio.json
3. System groups positions by ticker
4. System calculates weighted averages
5. System creates lot-based structure
6. System validates migration
7. User confirms: "Migration successful"

**Safety**:
- Original file backed up (portfolio.json.backup)
- Validation checks data integrity
- User can rollback if needed
- One-time operation (30 seconds)

---

## Rollback Plan

**If lot-based structure causes issues**:

1. Restore backup:
   ```bash
   $ cp portfolio.json.backup portfolio.json
   ```

2. Revert code changes (use git)

3. System returns to current behavior

**Data safety**: Original portfolio.json backed up before migration, zero data loss risk

---

## Future Enhancements (Not in Scope)

### Phase 2: Advanced Lot Management
- Specific lot selection (tax loss harvesting: choose which lot to sell)
- Lot transfer between accounts
- Lot gift/donation tracking

### Phase 3: Tax Optimization
- Auto-calculate capital gains per lot
- Tax loss harvesting recommendations
- Cost basis reporting (for tax filing)

### Phase 4: Performance Attribution
- Lot-level return tracking over time
- Best/worst performing lots
- DCA effectiveness analysis

---

## Acceptance Criteria

**Data Structure** - DONE when:
- [ ] Each ticker appears once in positions array
- [ ] Lots nested under parent position
- [ ] Total quantity calculated correctly (sum of lots)
- [ ] Weighted average cost calculated correctly
- [ ] FIFO order preserved (lots sorted by purchase_date)
- [ ] Lock status determined per lot (30-day rule)

**Display** - DONE when:
- [ ] Portfolio shows 2 stocks (not 3 positions)
- [ ] Total quantity visible at position level
- [ ] Lot breakdown available (detail view)
- [ ] Sellability status accurate ("1 partially sellable")
- [ ] MSFT appears once (not duplicated everywhere)
- [ ] Concentration risk clear (53% MSFT obvious)

**Validation** - DONE when:
- [ ] SELL validation checks FIFO sellable quantity
- [ ] "Can sell 1.5 shares" not "MSFT is locked"
- [ ] Validation explains impact (what remains after sell)
- [ ] No false positives (sellable lots not flagged as locked)
- [ ] No false negatives (locked lots not flagged as sellable)

**AI Integration** - DONE when:
- [ ] AI receives consolidated position data
- [ ] MSFT context shows 2.5 total shares, not separate lots
- [ ] AI understands FIFO constraints
- [ ] Recommendations reference total position + lot details
- [ ] No duplicate analysis of same stock

**Migration** - DONE when:
- [ ] Migration script converts old → new format
- [ ] Backup created automatically
- [ ] Data validation confirms accuracy
- [ ] User's actual portfolio migrates successfully
- [ ] No data loss, all lots preserved

---

## Dependencies

**None** - This is a foundational change

**Note**: Other CRs (CR003, CR004, CR005) will benefit from this but can proceed in parallel. Lot-based tracking improves their quality but doesn't block them.

---

## Approval

- [x] Change documented
- [ ] Solution reviewed and approved
- [ ] Implementation complete
- [ ] Migration script tested
- [ ] User portfolio migrated successfully
- [ ] All acceptance criteria met
- [ ] Documentation updated

**Product Owner**: Tobes  
**Implementation Target**: This week (urgent)  
**Priority**: URGENT (Critical bugs blocking correct operation)  
**Estimated Effort**: 1-2 days  

---

**END OF CHANGE REQUEST**