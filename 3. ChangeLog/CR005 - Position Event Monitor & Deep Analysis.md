# Change Request: CR005 - Position Event Monitor & Deep Analysis

**Date**: January 27, 2026
**Status**: Open
**Priority**: Medium-High
**Affects**: AI recommendation engine, output display
**Dependencies**: CR002 (News Themes), CR003 (Earnings Calendar)

---

## Problem Description

The current system provides monthly recommendations focused on new investment opportunities (what to buy) but lacks deep analysis when **material events affect existing holdings** (when to exit or hold).

**Discovered Gap**:
When a stock the user holds experiences a material event (earnings, regulatory action, CEO change, etc.), the system treats it the same as any other stock in the watchlist rather than recognizing this is a **critical decision point** for the user.

**Example scenario**:
```
User holds MSFT (only position, -7.4% P&L, 70 days held)
MSFT reports earnings yesterday
System output: "MSFT rank #4, below threshold, consider exit"

Missing:
- Was earnings a beat or miss?
- Does this validate or invalidate original thesis?
- What were analyst expectations?
- What's the market reaction telling us?
- Should I exit now or give it more time?
```

**Impact on User**:
- Making exit decisions without proper context
- Don't know if thesis is intact or broken
- Can't distinguish "weak quarter" from "fundamental deterioration"
- Risk holding positions that should be exited
- Risk exiting positions that should be held

**Root Cause**:
The system is optimized for **entry decisions** (which stock to buy) but not **hold/exit decisions** (what to do with what I own). Material events are the natural trigger points for reassessing holdings, but the system doesn't recognize or analyze them specially.

---

## Current Behavior

### When Material Event Occurs

**Scenario**: MSFT (holding) reports earnings yesterday

**Current output**:
```
MARKET SNAPSHOT:
- MSFT: Rank #4, Score 5.7, RSI 45.7

RECENT NEWS:
- MSFT: "Earnings beat expectations" (Jan 24)
- MSFT: "Office 365 pricing update" (Jan 23)

RECOMMENDATION:
SELL MSFT - all shares
Reasoning: Rank dropped to #4, approaching stop-loss at -7.4%
```

**Problems**:
1. ❌ No earnings context (beat by how much? guidance?)
2. ❌ No thesis validation (is cloud growth intact?)
3. ❌ No decision framework (exit now vs wait?)
4. ❌ Generic recommendation (same as any exit)
5. ❌ No position-specific analysis (why did I buy this?)

---

## Expected Behavior

### When Material Event Detected

**Scenario**: MSFT (holding) reports earnings yesterday

**Enhanced output**:
```
═══════════════════════════════════════════════════════
⚠️  MATERIAL EVENT DETECTED
═══════════════════════════════════════════════════════

MSFT: Quarterly Earnings Release
Detected: Q4 2025 earnings reported yesterday (Jan 24)
Priority: HIGH - Requires hold/exit decision analysis

YOUR POSITION:
- Holding: 1.5 shares @ $507.60 entry
- Current: $470.28 (-7.4% loss)
- Days held: 70 (eligible to sell)
- Portfolio weight: 100% (only position)

═══════════════════════════════════════════════════════
EVENT ANALYSIS: Earnings Results
═══════════════════════════════════════════════════════

WHAT HAPPENED:
- Q4 EPS: $3.23 (vs est. $3.12) → BEAT by 3.5% ✓
- Revenue: $69.6B (vs est. $68.9B) → BEAT by 1.0% ✓
- Azure growth: 31% (vs est. 30-32%) → IN-LINE →
- Guidance: Q1 rev $70-71B (vs est. $69.5-70.5B) → RAISED ✓

MARKET REACTION:
- After-hours: +2.1%
- Today's open: +1.8%, now flat
- Your position: -7.4% → -5.6% (partial recovery)

THESIS VALIDATION:
Original investment case: [Cloud/AI growth leadership]
✓ Azure growth sustained (31% still strong)
✓ Guidance raised (management confident)
→ Competitive position maintained (not accelerating)
✗ Rank still #4 (not improving vs peers)

Status: THESIS PARTIALLY VALIDATED
- Core business healthy (earnings beat)
- Growth trajectory intact (Azure 30%+)
- But relative position not improving (still #4)

═══════════════════════════════════════════════════════
DECISION FRAMEWORK
═══════════════════════════════════════════════════════

OPTION A: EXIT Position (Recommended)
Reasoning:
- Rank #4 with three better alternatives available
- Earnings good but didn't change competitive standing
- Still -5.6% loss, no clear recovery catalyst
- Capital better deployed in NVDA (#1) or AMD (#2)

Expected outcome: Rotate to higher-quality holding

OPTION B: HOLD Position (Conservative)
Reasoning:
- Earnings validated thesis (Azure growing)
- Guidance raised (positive momentum)
- -5.6% not severe enough for forced exit
- Give one more quarter to improve ranking

Risk: Opportunity cost of holding #4 vs buying #1

═══════════════════════════════════════════════════════
RECOMMENDATION: EXIT MSFT
═══════════════════════════════════════════════════════

Rationale:
Strategy targets top-3 ranked stocks. While earnings were 
solid (thesis not broken), MSFT at #4 means capital is 
sub-optimally deployed. Exit without regret (fundamentals 
okay) and rotate to NVDA (#1) which offers better 
risk/reward profile.

Action: Sell 1.5 shares, use proceeds (~$704) for NVDA

Confidence: MEDIUM-HIGH
(Clear earnings results, ranking-based exit is judgment call)

═══════════════════════════════════════════════════════
```

**Key differences**:
1. ✅ Event-specific context (earnings details)
2. ✅ Thesis validation (original case checked)
3. ✅ Decision framework (exit vs hold options)
4. ✅ Position-specific analysis (your entry, P&L)
5. ✅ Clear recommendation with reasoning

---

## Proposed Solution

### Feature: Position Event Monitor

**Purpose**: Automatically detect when material events affect user's holdings and trigger deep analysis for hold/exit decisions.

**Scope**: Only analyze events affecting **stocks currently held** (not entire watchlist).

---

### Component 1: Event Detection (Tier 1 Material Events)

**What qualifies as "material event" requiring deep analysis**:

#### 1. Earnings Results
- **Trigger**: Earnings reported within last 2 days
- **Why material**: Validates/invalidates investment thesis quarterly
- **Analysis needed**: Beat/miss magnitude, guidance changes, key metrics

#### 2. Regulatory Actions (Escalating)
- **Trigger**: 
  - Regulatory news theme with HIGH frequency (4+ articles in 14 days)
  - OR major lawsuit/investigation announced (single high-impact article)
- **Why material**: Can permanently impair business model or profitability
- **Analysis needed**: Severity, timeline, historical precedent

#### 3. Leadership Changes
- **Trigger**: CEO, CFO, or founder departure detected in news
- **Why material**: Strategy continuity uncertainty, potential direction shift
- **Analysis needed**: Circumstances (fired vs retired), replacement quality, transition plan

#### 4. Major M&A Activity
- **Trigger**: 
  - Company being acquired (holding is target)
  - Company announces major acquisition (holding is acquirer)
- **Why material**: Business model change, capital allocation concern
- **Analysis needed**: Deal terms, strategic rationale, integration risk

#### 5. Guidance Changes (Mid-Quarter)
- **Trigger**: Pre-announcement or material warning between earnings
- **Why material**: Fundamental deterioration or acceleration
- **Analysis needed**: Magnitude of change, reason given, sector context

**Detection method**: Pattern matching on existing data sources (news themes, earnings calendar, frequency analysis).

---

### Component 2: Deep Analysis Framework

**When material event detected, system provides**:

#### Section A: Event Context
```
What happened: [Specific event details]
When: [Timing]
Initial market reaction: [Price movement, volume]
Position impact: [Effect on user's P&L]
```

#### Section B: Position Context
```
Your holdings: [Quantity, entry price, current P&L]
Days held: [Time in position]
Original thesis: [Why you bought this stock]
Current rank: [Where it stands now]
Portfolio weight: [What % of portfolio]
```

#### Section C: Fundamental Impact Assessment
```
Thesis validation check:
✓ Validated: [What confirms original thesis]
→ Neutral: [What's unchanged]
✗ Invalidated: [What contradicts thesis]

Overall: VALIDATED | PARTIALLY VALIDATED | INVALIDATED
```

#### Section D: Decision Framework
```
Option A: EXIT
- Reasoning
- Expected outcome
- Risks

Option B: HOLD
- Reasoning  
- Expected outcome
- Risks

[Additional options if relevant]
```

#### Section E: Clear Recommendation
```
Recommended action: [EXIT | HOLD]
Rationale: [Why this is best course given strategy]
Next steps: [Specific actions to take]
Confidence: [HIGH | MEDIUM | LOW]
```

---

### Component 3: Output Integration

**Display priority**:
1. **Material Events Section** (if detected) - shown FIRST
2. Standard Market Snapshot
3. Standard Recommendations

**Example output structure**:
```
╔══════════════════════════════════════════════════════╗
║              PORTFOLIO AI ADVISOR                    ║
╚══════════════════════════════════════════════════════╝

⚠️  1 MATERIAL EVENT DETECTED - Analysis Required

[Detailed event analysis as shown in Expected Behavior]

============================================================
MARKET SNAPSHOT
============================================================
[Standard rankings, technicals, news themes]

============================================================
RECOMMENDATIONS
============================================================
[Standard buy/sell/hold recommendations]
```

**When no events**: Normal output (no Material Events section shown)

**When multiple events**: Show all, sorted by priority (holdings first, then watchlist)

---

## Event-Specific Analysis Templates

### Template 1: Earnings Event

**Analysis structure**:
```
1. Results Summary
   - EPS actual vs estimate (beat/miss/inline)
   - Revenue actual vs estimate
   - Key metrics (segment performance)
   - Guidance changes

2. Historical Context
   - Beat rate (last 4 quarters)
   - Typical market reaction to beats/misses
   - Trend (improving vs deteriorating)

3. Thesis Validation
   - Original investment case: [from narratives or inferred]
   - Validated by: [results that confirm thesis]
   - Concerns: [results that contradict thesis]

4. Competitive Context
   - How peers performed (if earnings season)
   - Relative market share trends
   - Rank changes (improved or worsened)

5. Decision Factors
   - P&L status (profit vs loss)
   - Days held (how long in position)
   - Alternative opportunities (what else is ranked higher)
   - Recovery catalyst (is there reason to hold?)
```

---

### Template 2: Regulatory Event

**Analysis structure**:
```
1. Event Summary
   - What: [Lawsuit, investigation, fine]
   - Who: [DOJ, FTC, EU, SEC]
   - Allegations: [Specific claims]
   - Timeline: [Expected duration]

2. Severity Assessment
   - Financial impact: [Potential fines, revenue at risk]
   - Business model impact: [Operational changes required]
   - Historical precedent: [Similar cases, outcomes]

3. Market Pricing
   - Stock reaction: [How much has stock declined]
   - Vs historical: [Typical reaction to regulatory news]
   - Priced in? [Is risk fully reflected or more downside?]

4. Thesis Impact
   - Does this change investment case?
   - Long-term profitability impact
   - Competitive advantage affected?

5. Decision Factors
   - Exit now vs wait for resolution
   - Is regulatory risk priced in?
   - Better opportunities available?
```

---

### Template 3: Leadership Change

**Analysis structure**:
```
1. Change Details
   - Who: [Name, role]
   - When: [Effective date, transition period]
   - Why: [Retirement, fired, personal reasons]
   - Replacement: [Named or search underway]

2. Context Assessment
   - Planned vs unexpected
   - Performance prior to departure
   - Succession plan quality
   - Market/analyst reaction

3. Strategic Implications
   - Continuity of strategy
   - Potential direction changes
   - Key initiatives at risk
   - Team stability

4. Historical Pattern
   - How stock typically reacts to leadership changes
   - Successful transitions (precedent)
   - Failed transitions (warning signs)

5. Decision Factors
   - Uncertainty timeline (how long until clarity)
   - Your risk tolerance for management uncertainty
   - Alternative investments without this risk
```

---

### Template 4: M&A Event

**Analysis structure**:
```
1. Deal Summary
   - Type: [Being acquired | Acquiring company]
   - Terms: [Price, structure, timing]
   - Strategic rationale: [Why this deal]

2. Shareholder Impact
   - Premium to current price (if target)
   - Dilution concerns (if acquirer)
   - Deal certainty (regulatory approval risk)

3. Investment Case Change
   - If target: Exit on deal close or sell now?
   - If acquirer: Does this strengthen or weaken company?
   - Integration risk assessment

4. Decision Framework
   - Sell now or wait for deal close (if target)
   - Hold through or exit before uncertainty (if acquirer)
   - Arbitrage opportunity (if target, trading below offer)
```

---

## User Workflows

### Workflow 1: Monthly Run with Event Detected

**User action**: Run monthly analysis (1st of month)

**System detects**: MSFT (holding) reported earnings 2 days ago

**System output**:
1. Alert at top: "⚠️ Material Event Detected"
2. Deep event analysis (earnings template)
3. Hold/exit recommendation
4. Standard market snapshot
5. Other recommendations (if applicable)

**User action**: 
- Read event analysis
- Decide: Exit MSFT or hold
- Execute trade if exiting
- Confirm to system

**Time investment**: 10-15 minutes (vs 5 minutes without event)

---

### Workflow 2: Multiple Holdings, One Event

**User holds**: MSFT, NVDA, GOOGL (3 positions)

**System detects**: MSFT earnings (material event)

**System output**:
1. Material Event section for MSFT only
2. Standard recommendations for portfolio
3. May recommend: "Exit MSFT, hold NVDA/GOOGL"

**User focus**: MSFT decision (other holdings status quo)

---

### Workflow 3: No Events Detected

**User holds**: MSFT, NVDA (2 positions)

**System detects**: No material events in last 7 days

**System output**:
- No Material Events section (clean output)
- Standard market snapshot
- Standard recommendations

**User experience**: Same as current (no change when calm)

---

## Scope Definition

### IN SCOPE (Phase 1: Pattern Matching)

**Event detection**:
- ✅ Earnings (from earnings calendar)
- ✅ Regulatory escalation (from news themes + frequency)
- ✅ Leadership changes (from news themes)
- ✅ Major M&A (from news themes)

**Analysis depth**:
- ✅ Event-specific templates (earnings, regulatory, leadership, M&A)
- ✅ Thesis validation check
- ✅ Decision framework (hold vs exit)
- ✅ Position-specific context

**Output**:
- ✅ Material Events section (when detected)
- ✅ Integrated with standard recommendations
- ✅ Clear visual priority (shown first)

---

### NOT IN SCOPE (Explicitly Excluded)

**Event coverage**:
- ❌ Events for stocks NOT held (focus only on holdings)
- ❌ Tier 2/3 events (product launches, partnerships, minor news)
- ❌ Macroeconomic events (interest rates, unless directly impacting holding)

**Analysis features**:
- ❌ Real-time event monitoring (still monthly on-demand runs)
- ❌ Push notifications (no background service)
- ❌ Historical event database (future: learn from past patterns)

**Automation**:
- ❌ Auto-execute trades based on events (user always confirms)
- ❌ Predictive event detection (only react to occurred events)

---

### FUTURE ENHANCEMENTS (Phase 2+)

**Level 2: LLM Event Classification**
- Use Claude API to detect material events from news (smarter)
- Better event severity assessment (nuanced understanding)
- Catch events that pattern matching might miss
- More accurate thesis validation analysis

**Benefits**: 
- Higher detection accuracy (~95% vs ~70%)
- Better handling of ambiguous events
- Richer contextual understanding

**Trade-offs**:
- Additional API costs (~$0.02 per run)
- Slightly longer execution time (+5-10 seconds)

**Decision point**: Implement if Phase 1 misses critical events

---

**Phase 3: Event Learning & Patterns**
- Track historical events and outcomes
- Learn: "Last time GOOGL had regulatory news, stock recovered in 3 months"
- Pattern-based recommendations: "Historical pattern suggests holding"

**Phase 4: Real-Time Monitoring**
- Background service monitors holdings continuously
- Push notification when material event detected
- "ALERT: MSFT CEO resigns, analysis ready"

---

## Success Metrics

### Quantitative (Measurable)

**Event detection accuracy**:
- Target: Detect 90%+ of material events affecting holdings
- Measure: Manual review of holdings each month, check if major events were caught

**False positive rate**:
- Target: <20% of detected events are actually non-material
- Measure: User feedback on event relevance

**Analysis completeness**:
- Target: 100% of detected events receive full analysis template
- Measure: System logs, output review

**Response time**:
- Target: Material Events section appears within 60 seconds of run start
- Measure: Execution time logs

---

### Qualitative (User Satisfaction)

**Decision confidence**:
- User feels more confident in hold/exit decisions
- Measure: Subjective feedback, post-decision reviews

**Context value**:
- Event analysis provides information user wouldn't have found manually
- Measure: User feedback ("Did analysis add value?")

**Action clarity**:
- User knows exactly what to do after reading analysis
- Measure: Reduced follow-up questions, decisive actions

**Trust building**:
- System demonstrates understanding of user's portfolio needs
- Measure: Continued usage, confidence in recommendations

---

## Risk Analysis

### Risk 1: Missing Critical Events (Detection Failure)

**Risk**: Pattern matching misses material event affecting holding

**Impact**: User makes uninformed decision, potential loss

**Mitigation**:
- Start with conservative detection (over-trigger rather than under)
- User can manually request event analysis if something seems off
- Phase 2 adds LLM detection as backup (higher accuracy)
- Document known limitations in user guide

**Likelihood**: Medium (pattern matching ~70% effective)
**Severity**: High (could cost real money)

---

### Risk 2: False Positives (Over-Triggering)

**Risk**: System detects "material event" that isn't actually material

**Impact**: User wastes time reading unnecessary analysis

**Mitigation**:
- Strict Tier 1 criteria (only clearly material events)
- User feedback loop to tune detection
- Separate "monitoring" events (watchlist) from "action required" (holdings)

**Likelihood**: Low-Medium (20% false positive target acceptable)
**Severity**: Low (wastes 5 minutes, not costly)

---

### Risk 3: Analysis Quality Varies by Event Type

**Risk**: Some event templates less useful than others

**Impact**: User doesn't get value from analysis, questions feature

**Mitigation**:
- Prioritize earnings template (most common, most important)
- Iterate on other templates based on user feedback
- Allow user to request specific analysis focus areas

**Likelihood**: Medium (regulatory/M&A templates less mature)
**Severity**: Medium (reduces feature value)

---

### Risk 4: Execution Time Increases

**Risk**: Event detection + deep analysis adds significant time

**Impact**: User waiting 2-3 minutes instead of 60 seconds

**Mitigation**:
- Run event detection in parallel with other data fetching
- Cache event analysis if re-running same day
- Optimize API calls (batch where possible)

**Likelihood**: Low (mostly data already fetched)
**Severity**: Low (still under 2 minutes acceptable)

---

## Testing Strategy

### Functional Testing

**Test 1: Earnings Detection**
- Portfolio: Hold MSFT
- Scenario: MSFT reports earnings yesterday
- Expected: Material Event detected, earnings template shown
- Verify: Event details accurate, recommendation makes sense

**Test 2: Regulatory Detection**
- Portfolio: Hold GOOGL
- Scenario: 5 DOJ investigation articles in past week
- Expected: Material Event detected, regulatory template shown
- Verify: Severity assessment reasonable, thesis check done

**Test 3: No Events**
- Portfolio: Hold NVDA
- Scenario: No material news in past 14 days
- Expected: No Material Events section, standard output
- Verify: Clean output, no false positives

**Test 4: Multiple Holdings, One Event**
- Portfolio: Hold MSFT, NVDA, GOOGL
- Scenario: MSFT earnings only
- Expected: Event analysis for MSFT, status quo for others
- Verify: Focused analysis, not overwhelming

---

### Integration Testing

**Test 5: End-to-End with Event**
- Start: User runs monthly analysis
- System: Detects MSFT earnings, fetches data, runs analysis
- Output: Material Event section + standard recommendations
- User: Reads analysis, decides to exit, confirms
- System: Updates portfolio
- Verify: Complete workflow smooth, no errors

**Test 6: Event + Standard Recommendations**
- Scenario: MSFT event + New NVDA buy opportunity
- Expected: Both shown clearly (event first, then new buy)
- Verify: Output not confusing, priorities clear

---

### User Acceptance Testing

**Test 7: Real-World Event**
- Wait for actual earnings/event in user's holdings
- Run system with real data
- User evaluates: Did analysis help? Was recommendation reasonable?
- Iterate based on feedback

**Test 8: Missed Event Check**
- After 1 month of usage, review if any major events were missed
- If yes: Tune detection or note for Phase 2 (LLM detection)

---

## Implementation Phases

### Phase 1: Core Feature (Week 1-2)

**Deliverables**:
- [ ] Event detection for Tier 1 events (earnings, regulatory, leadership, M&A)
- [ ] Deep analysis templates for each event type
- [ ] Decision framework structure (hold vs exit options)
- [ ] Material Events output section
- [ ] Integration with standard output

**Definition of Done**:
- Earnings events detected accurately (90%+ recall)
- Event analysis templates complete and tested
- Output displays Material Events section when applicable
- User can follow analysis and make informed decision

---

### Phase 2: Refinement (Week 3)

**Deliverables**:
- [ ] Tune detection thresholds (reduce false positives)
- [ ] Enhance templates based on initial testing
- [ ] Add thesis validation logic (check against narratives)
- [ ] Improve decision framework reasoning

**Definition of Done**:
- False positive rate <20%
- Templates feel comprehensive and useful
- Thesis validation references stored narratives correctly
- Recommendations are confident and clear

---

### Phase 3: Polish (Week 4)

**Deliverables**:
- [ ] Visual improvements (formatting, icons, clarity)
- [ ] Performance optimization (if needed)
- [ ] Documentation (user guide section)
- [ ] Edge case handling (multiple simultaneous events)

**Definition of Done**:
- Output is visually clear and easy to scan
- Execution time <90 seconds including event analysis
- User guide explains Material Events feature
- Multiple events handled gracefully

---

## User Communication

### Feature Announcement

**When launching CR005**:

```
🎉 NEW FEATURE: Position Event Monitor

The system now automatically detects when material events 
affect stocks you're holding and provides deep analysis to 
help you decide whether to hold or exit.

Material Events Include:
• Earnings results (quarterly reports)
• Regulatory actions (lawsuits, investigations)
• Leadership changes (CEO/CFO departures)
• Major M&A activity
• Guidance changes

When detected, you'll see:
✓ Detailed event analysis
✓ Thesis validation check
✓ Hold vs Exit decision framework
✓ Clear recommendations

This helps you make informed decisions at critical moments,
not just when you happen to run your monthly analysis.
```

---

### User Guide Section

**Add to README.md**:

```markdown
## Material Events Analysis

When significant events affect your holdings, the system 
automatically provides deep analysis to help you decide 
whether to hold or exit the position.

### What Triggers Analysis

Material events include:
- **Earnings**: Quarterly results reported within last 2 days
- **Regulatory**: Escalating legal/regulatory actions
- **Leadership**: CEO, CFO, or founder departures
- **M&A**: Acquisition announcements (target or acquirer)
- **Guidance**: Mid-quarter warnings or pre-announcements

### What You Get

Event-specific analysis including:
1. What happened (event details, market reaction)
2. Your position context (entry, P&L, thesis)
3. Thesis validation (is your investment case still intact?)
4. Decision framework (hold vs exit options with reasoning)
5. Clear recommendation (what you should do)

### When It Appears

The Material Events section appears FIRST in your output
(above standard recommendations) when events are detected
affecting stocks you currently hold.

When your portfolio is calm (no events), output looks the
same as always - this feature only appears when needed.
```

---

## Acceptance Criteria

**Event Detection** - DONE when:
- [ ] Earnings events detected for holdings within 2-day window
- [ ] Regulatory themes with HIGH frequency trigger detection
- [ ] Leadership changes detected from news themes
- [ ] M&A announcements detected from news themes
- [ ] Detection runs automatically on every program execution
- [ ] Only holdings checked (not entire watchlist)

**Deep Analysis** - DONE when:
- [ ] Earnings template provides: results, expectations, thesis check, decision framework
- [ ] Regulatory template provides: severity, timeline, precedent, decision framework
- [ ] Leadership template provides: circumstances, implications, risk, decision framework
- [ ] M&A template provides: terms, impact, integration risk, decision framework
- [ ] All templates include clear hold vs exit options
- [ ] All templates reference user's specific position (entry, P&L, days held)

**Output Integration** - DONE when:
- [ ] Material Events section appears FIRST in output
- [ ] Section only shown when events detected (not always)
- [ ] Visual priority clear (alert symbol, formatting)
- [ ] Flows naturally into standard recommendations
- [ ] Multiple events handled (all shown, sorted by priority)

**Decision Support** - DONE when:
- [ ] User can understand what happened (event context)
- [ ] User can assess impact (thesis validation)
- [ ] User can decide action (hold vs exit framework)
- [ ] Confidence level provided (HIGH/MEDIUM/LOW)
- [ ] Recommendation is clear and actionable

**Quality Validation** - DONE when:
- [ ] Manual review: Earnings analysis matches actual results
- [ ] Manual review: Thesis validation references correct original case
- [ ] Manual review: Recommendations are reasonable
- [ ] False positive check: <20% of detected events are non-material
- [ ] Coverage check: 90%+ of real material events detected

---

## Dependencies

### Required (Must be implemented first):

**CR002: News Clustering & Sentiment**
- Provides news themes for event detection
- Frequency classification (HIGH/MEDIUM/LOW)
- Theme categorization (regulatory, leadership, etc.)

**CR003: Earnings Calendar**
- Provides earnings dates for detection
- Days until/since earnings calculation

### Optional (Enhances but not blocking):

**Narrative storage** (CR002 Phase 2)
- Enables better thesis validation (recalls why user bought)
- Without: AI infers thesis from timing and ranking

---

## Future State Vision

### Phase 2: LLM Event Classification (3-6 months)

**Enhancement**: Use Claude API to detect and assess events

**Capability**:
```
Instead of pattern matching, ask Claude:
"Review these news headlines for MSFT (holding).
 Are there any MATERIAL EVENTS requiring analysis?
 
 Material = earnings, regulatory, leadership, M&A, guidance
 
 Respond: event_type, severity, description"
```

**Benefits**:
- Catches ambiguous events pattern matching misses
- Better severity assessment (nuanced understanding)
- Richer contextual analysis

**Trade-off**: +$0.02 per run, slightly longer execution

---

### Phase 3: Event Learning (6-12 months)

**Enhancement**: Track events and outcomes over time

**Capability**:
- Store: Events that occurred, decisions made, outcomes
- Learn: "When GOOGL had regulatory news, we held and stock recovered in 3 months"
- Apply: "Current MSFT situation similar to past GOOGL case, pattern suggests holding"

**Benefits**:
- Recommendations improve with your portfolio history
- Pattern recognition from your own data
- Personalized to your strategy effectiveness

---

### Phase 4: Real-Time Monitoring (12+ months)

**Enhancement**: Continuous background monitoring

**Capability**:
- Background service watches your holdings 24/7
- Push notification when material event detected
- "ALERT: MSFT CEO resigns. Analysis ready in app."
- Instant access to event analysis

**Benefits**:
- React quickly to breaking events
- Don't wait for monthly run
- More timely decision-making

**Trade-off**: Requires architecture change (background service), push notification system

---

## Approval

- [x] Change documented
- [ ] Solution reviewed and approved
- [ ] Phase 1 implementation complete
- [ ] Phase 1 testing complete
- [ ] User acceptance testing complete
- [ ] Documentation updated
- [ ] Feature announced to user

**Product Owner**: Tobes  
**Implementation Target**: Week of Jan 27, 2026  
**Priority**: Medium-High  
**Estimated Effort**: 1-2 weeks (8-16 hours)  
**Dependencies**: CR002 (News Themes), CR003 (Earnings Calendar)

---

**END OF CHANGE REQUEST**