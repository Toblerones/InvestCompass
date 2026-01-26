# Change Request: CR001 - Cash Flow Logic Enhancement

**Date**: January 26, 2026
**Status**: Implemented (Pending Testing)
**Priority**: Medium
**Affects**: `ai_agent.py` (prompt template, validation)

---

## Problem Description

The AI recommendation engine currently validates BUY actions against the static portfolio state (current cash available) without accounting for proceeds from SELL actions that are recommended in the same execution sequence. 

**Example scenario:**
- Portfolio: 1.5 MSFT shares (worth ~$699), $0 cash
- AI recommends: (1) SELL MSFT, (2) BUY NFLX $700
- System shows error: "Requested $700.00 but only $0.00 available"

The AI doesn't calculate that selling MSFT would generate ~$689 in proceeds, which would then be available for the NFLX purchase. This creates a confusing user experience where valid sequential actions appear to fail validation.

---

## Current Behavior

1. AI receives portfolio context with static cash amount ($0)
2. AI recommends SELL action (MSFT)
3. AI recommends BUY action (NFLX $700) without calculating proceeds from step 2
4. Program validates BUY against original cash ($0)
5. System displays warning: "Only $0.00 available" despite the SELL generating sufficient proceeds

**Root cause**: The AI prompt does not instruct the model to:
- Calculate expected proceeds from recommended SELL actions
- Use those proceeds as available capital for subsequent BUY actions
- Perform sequential cash flow calculations

---

## Expected Behavior

1. AI receives portfolio context including current prices and transaction fees
2. AI recommends SELL action and calculates expected proceeds
   - Example: "SELL MSFT 1.5 shares @ $465.95 = $699 - $10 fee = $689 proceeds"
3. AI tracks available cash sequentially: $0 + $689 = $689
4. AI recommends BUY action using calculated available cash
   - Example: "BUY NFLX $689 (using proceeds from MSFT sale)"
5. System displays coherent action sequence with accurate cash flow

**Expected output:**
```
1. SELL MSFT - all shares
   Expected proceeds: $689 (after $10 fee)

2. BUY NFLX - $689
   [✓] Using proceeds from MSFT sale
```

---

## Proposed Solution

**Files to modify:**
- [x] `App/src/ai_agent.py` - Update prompt template

**Changes:**

1. **Add current price context to prompt**
   - Include current market prices for all portfolio holdings
   - AI needs this to calculate sell proceeds accurately

2. **Add sequential cash flow instructions**
   - Explicit instruction to calculate proceeds from each SELL
   - Formula: `proceeds = (quantity × current_price) - transaction_fee`
   - Instruction to add proceeds to available cash before calculating BUY amounts

3. **Add worked example in prompt**
   - Show concrete example of SELL → BUY cash flow calculation
   - Demonstrate expected reasoning format

4. **Update JSON response schema** (optional)
   - Add `expected_proceeds` field to SELL actions
   - Add `cash_source` field to BUY actions (e.g., "MSFT sale proceeds")

**Detailed implementation:**
```python
# In ai_agent.py, update build_prompt() function:

SEQUENTIAL_CASH_FLOW_INSTRUCTION = """
CRITICAL - SEQUENTIAL CASH FLOW CALCULATION:

Current cash available: ${portfolio['cash_available']}
Transaction fee: ${config['transaction_fee']} per trade

When recommending multiple actions (SELL followed by BUY):

1. Calculate expected proceeds from each SELL action:
   Formula: proceeds = (quantity × current_price) - transaction_fee
   
2. Add proceeds to running cash total:
   available_cash = current_cash + sum(all_sell_proceeds)
   
3. Use accumulated cash for BUY recommendations:
   Never recommend buying more than available_cash

4. Show your calculation in reasoning:
   Example: "Using $689 from MSFT sale ($699 gross - $10 fee)"

CURRENT PRICES (for your proceeds calculations):
{format_current_prices(market_data)}

WORKED EXAMPLE:
Starting cash: $0
Holdings: MSFT 1.5 shares (current price $465.95)

Step 1: Recommend SELL MSFT
  Proceeds = 1.5 × $465.95 = $699 - $10 fee = $689
  
Step 2: Update available cash
  Available = $0 + $689 = $689
  
Step 3: Recommend BUY with accurate amount
  "BUY NFLX $689" (not $700, because we only have $689)
  Reasoning: "Using $689 proceeds from MSFT sale"

Your calculations must be accurate. The user will execute these trades based on your numbers.
"""

# Add to existing prompt template after portfolio context section
```

5. **Add validation helper** (optional safety net):
```python
def validate_ai_cash_flow(actions, portfolio, market_data):
    """
    Safety check: Verify AI's cash flow math is reasonable.
    Warns if calculations are off by >$50.
    """
    simulated_cash = portfolio['cash_available']
    
    for action in actions:
        if action['type'] == 'SELL':
            # Calculate what proceeds should actually be
            position = find_position(portfolio, action['ticker'])
            current_price = market_data[action['ticker']]['price']
            actual_proceeds = (position['quantity'] * current_price) - 10
            
            # If AI provided expected_proceeds, check accuracy
            if 'expected_proceeds' in action:
                diff = abs(action['expected_proceeds'] - actual_proceeds)
                if diff > 50:
                    print(f"⚠️  AI calculated ${action['expected_proceeds']} "
                          f"proceeds, actual would be ${actual_proceeds:.2f}")
            
            simulated_cash += actual_proceeds
            
        elif action['type'] == 'BUY':
            if action['amount'] > simulated_cash + 10:  # +10 buffer
                print(f"⚠️  AI recommended buying ${action['amount']} "
                      f"but only ${simulated_cash:.2f} available")
```

---

## Impact Analysis

- **Risk**: Low
  - Prompt change only, no code logic modifications
  - AI already has capability to do arithmetic
  - Fallback: User can still manually interpret recommendations
  
- **Testing**: Manual end-to-end test required
  - Test case 1: SELL followed by BUY (current scenario)
  - Test case 2: Multiple SELLs followed by BUY
  - Test case 3: BUY with new capital (no SELL)
  - Test case 4: SELL only (no BUY)
  
- **Backward Compatibility**: N/A (prompt improvement, not breaking change)

- **Performance**: Negligible
  - Same number of API calls
  - Slightly longer prompt (~200 tokens added)
  - Estimated cost increase: <$0.01 per run

- **User Experience**: Significant improvement
  - Eliminates confusing "insufficient funds" warnings
  - Shows accurate, executable action plans
  - Builds user trust in AI recommendations

---

## Implementation Notes

**Pre-implementation checklist:**
- [ ] Review current prompt template in `ai_agent.py`
- [ ] Identify exact insertion point for new instructions
- [ ] Verify `market_data` includes current prices for all holdings
- [ ] Confirm `format_current_prices()` helper function exists (or create it)

**Implementation steps:**
1. Create `format_current_prices()` helper function
```python
   def format_current_prices(market_data):
       """Format current prices for prompt"""
       lines = []
       for ticker, data in market_data.items():
           lines.append(f"- {ticker}: ${data['price']:.2f}")
       return "\n".join(lines)
```

2. Update `build_prompt()` to include sequential cash flow instructions
   - Insert after portfolio context section
   - Before "YOUR TASK:" section

3. Test with actual portfolio state (MSFT holding, $0 cash)

4. Verify AI response includes accurate cash flow calculations

**Post-implementation:**
- [ ] Run end-to-end test with current portfolio
- [ ] Verify SELL proceeds are calculated correctly
- [ ] Verify BUY amount matches available proceeds
- [ ] Check reasoning includes cash flow explanation
- [ ] Document any edge cases discovered

**Potential edge cases to consider:**
- What if multiple positions are sold? (AI should sum all proceeds)
- What if transaction fees reduce proceeds below minimum buy? (AI should warn)
- What if prices change between recommendation and execution? (User responsibility, document in README)

**Future enhancements** (not in this CR):
- Add real-time price refresh before execution
- Add "adjust buy amount to available cash" option
- Add cash flow waterfall display in output

---

## Approval

- [x] Change documented
- [x] Solution reviewed
- [x] Implementation complete
- [ ] Testing complete

**Reviewed by**: Product Owner
**Approved by**: Product Owner
**Implementation date**: January 26, 2026

## Implementation Summary

Changes made to `App/src/ai_agent.py`:

1. **Added `_format_holdings_for_cashflow()` helper** (lines 252-282)
   - Formats holdings with gross value and net proceeds after fee
   - Shows SELLABLE/LOCKED status

2. **Updated `build_prompt()` function** (lines 69-159)
   - Added `SEQUENTIAL CASH FLOW CALCULATION` section with instructions
   - Includes worked example for SELL → BUY flow
   - Shows holdings with calculated proceeds

3. **Updated JSON response schema** (lines 142-157)
   - Added `expected_proceeds` field for SELL actions
   - Added `cash_source` field for BUY actions

4. **Updated `validate_actions()` function** (lines 504-585)
   - Now tracks `running_cash` that accumulates proceeds from SELLs
   - BUY validation uses running_cash instead of static cash_available
   - Verifies AI's expected_proceeds calculation (warns if >$50 diff)