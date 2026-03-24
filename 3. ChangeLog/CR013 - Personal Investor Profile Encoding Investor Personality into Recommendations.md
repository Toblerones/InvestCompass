# CR013 — Personal Investor Profile: Encoding Investor Personality into Recommendations

**Date**: March 20, 2026
**Status**: Open
**Priority**: HIGH
**Severity**: Enhancement
**Affects**: AI Advisor Strategy Prompt — New Layer and All Reasoning Frameworks

---

## Related

- **CR009**: Judgment-based reasoning redesign — established the three-layer architecture this CR extends with a fourth layer
- **CR012**: Cash efficiency — averaging down recommendations need to be weighted by investor risk tolerance, not just market signals
- **CR010**: Signal hierarchy — personal bias is a legitimate input that should influence how signals are weighted

---

## 1. Problem Description

The InvestCompass advisor synthesises three inputs to make recommendations:

1. Market data and technicals (rankings, RSI, news, price context)
2. LLM reasoning (frameworks, signal hierarchy, principles)
3. Personal investor bias — **currently missing**

The system was designed to incorporate personal bias as a first-class input alongside market data and LLM judgment. Without it, the advisor produces recommendations that are technically correct but not personalised — they reflect what a generic moderate-risk investor should do, not what *this specific investor* should do given their personality, risk tolerance, and circumstances.

### 1.1 Concrete Impact

The CR012 averaging down recommendation (buy 3 shares of NVDA) is logically sound from a market and framework perspective. But it may be wrong for a specific investor who:

- Has low comfort with 30-day lock-period exposure in a deteriorating macro environment
- Keeps this portfolio as a significant portion of total savings (high stakes = lower risk tolerance)
- Prefers to maintain a meaningful cash buffer as psychological safety
- Has moderate rather than high conviction in the AI infrastructure thesis

The same market data and the same frameworks should produce *different* recommendations for different investor personalities. Currently they produce the same recommendation for everyone.

### 1.2 What Personal Bias Is Not

Personal bias in this context is not irrational noise to be filtered out. It is legitimate investor preference that reflects:

- Actual risk capacity (financial and emotional)
- Investment horizon and life circumstances
- Conviction level in specific thesis areas
- Behavioural tendencies that are known and accepted

A good human advisor would ask these questions in the first meeting. InvestCompass has never asked them.

---

## 2. The Three-Way Synthesis Model

The advisor should operate as a synthesis of three inputs with roughly equal standing:

```
Market data + technicals
        +
   LLM reasoning
        +
  Investor profile
        =
  Personalised recommendation
```

No single input dominates. A strong market signal (Priority 2 positive catalyst) can be moderated by a conservative investor profile. A weak technical signal (RSI slightly above 50) can be overridden by a high-conviction investor profile. The hard constraints (Layer 1) remain non-negotiable regardless of profile.

---

## 3. Proposed Changes

### 3.1 Add Layer 0 — Investor Profile

Add a new layer before Layer 1, designated Layer 0 to signal that it precedes all other reasoning as the foundational context:

```
=============================================================
LAYER 0 — INVESTOR PROFILE (personalise all recommendations)
=============================================================

This profile captures who the investor is. All recommendations must
be weighted against this profile — not just market signals and frameworks.
The profile does not override Layer 1 hard constraints, but it shapes
every judgment call in Layers 2 and 3.

RISK TOLERANCE: [Conservative / Moderate / Aggressive]
  Conservative: Prefer capital preservation over returns. Tighten
    stops earlier, deploy cash more cautiously, prefer smaller
    position sizes, require higher conviction before averaging down.
  Moderate: Balance between growth and preservation. Apply frameworks
    as designed. Accept normal drawdowns within -10% stop.
  Aggressive: Prioritise returns over capital preservation. Deploy
    cash more actively, accept higher concentration, willing to hold
    through larger drawdowns if thesis is intact.

AI THESIS CONVICTION: [Low / Medium / High]
  Low: Treat AI infrastructure stocks as any other sector — apply
    frameworks without sector bias.
  Medium: Mild preference for top-ranked AI stocks, but weight
    diversification and risk management equally.
  High: Strong belief in AI infrastructure supercycle. Willing to
    concentrate in top-ranked AI names, accept higher volatility,
    and average down more aggressively on macro weakness.

LOCK-PERIOD COMFORT: [Low / Medium / High]
  Low: Treat locked positions as significantly higher risk. Require
    wider stop-loss buffer before averaging down. Prefer not to
    average down if new shares will be locked in a deteriorating
    macro environment.
  Medium: Accept lock periods as designed — the constraint prevents
    emotional exits and is a feature. Average down normally.
  High: View lock periods as beneficial discipline. Fully willing to
    average down into locked positions with high thesis conviction.

CASH BUFFER PREFERENCE: [Minimal / Moderate / Substantial]
  Minimal: Comfortable holding <15% cash when high-conviction
    opportunities are available. Prioritise deployment.
  Moderate: Prefer 20-35% cash buffer at all times. Apply Framework E
    at >50% cash as designed.
  Substantial: Prefer 35-50% cash buffer. Apply Framework E only at
    >65% cash. Higher threshold before deployment is triggered.

PORTFOLIO SIGNIFICANCE: [Discretionary / Meaningful / Primary]
  Discretionary: This portfolio is a small fraction of total wealth.
    Higher risk tolerance appropriate — losses are manageable.
  Meaningful: This portfolio represents a significant but not dominant
    portion of total wealth. Apply moderate risk weighting.
  Primary: This portfolio is a primary financial asset. Capital
    preservation weighs heavily. Be more conservative on position
    sizing, averaging down, and concentration.

DRAWDOWN BEHAVIOUR: [Hold through / Tighten gradually / Exit early]
  Hold through: Comfortable holding positions through -15% drawdowns
    if thesis is intact. Do not adjust stops on volatility.
  Tighten gradually: As losses approach -7%, begin tightening mental
    stops and require stronger thesis confirmation to hold.
  Exit early: Uncomfortable with extended drawdowns. Flag earlier
    exit opportunities even when thesis is technically intact.

HOW TO APPLY THIS PROFILE:
  1. Before finalising any recommendation, ask: "Is this right for
     THIS investor given their profile — not just for a generic
     moderate-risk investor?"
  2. Adjust position sizing, averaging down scale, and cash deployment
     thresholds proportionally to the profile settings.
  3. When profile settings conflict with a market signal, state the
     conflict explicitly and explain how the profile influenced the
     final recommendation.
  4. Never use the profile to override Layer 1 hard constraints.
  5. When profile is set to Conservative or Primary significance,
     err on the side of smaller positions, wider cash buffers, and
     fewer averaging down actions.
```

### 3.2 Profile Application Table

Add this reference table immediately after the profile definition to show how each dimension modifies framework outputs:

```
PROFILE APPLICATION REFERENCE:

Risk Tolerance impact:
  Conservative → Framework B: max averaging = 20% of cash (not 50%)
                 Framework E: trigger at >40% cash (not >50%)
                 Framework C: require RSI < 45 for entry (not < 50)
  Moderate     → Apply frameworks as designed (default)
  Aggressive   → Framework B: max averaging = 60% of cash
                 Framework E: trigger at >60% cash
                 Framework C: RSI < 55 acceptable with strong thesis

AI Thesis Conviction impact:
  Low    → No sector weighting. Treat NVDA/MSFT like any stock.
  Medium → Mild preference for top-ranked AI names, no special treatment.
  High   → In Framework B: thesis strength weighted more heavily.
            In Framework E Option B: willing to enter despite RSI > 50
            if AI thesis is actively strengthening.

Lock-Period Comfort impact:
  Low    → Before any averaging down: explicitly assess whether new
            shares will be locked during elevated macro risk. If macro
            is deteriorating (SPY negative 30-day), reduce averaging
            down scale by 50% or defer entirely.
  Medium → Apply Framework B as designed.
  High   → Lock period is not a moderating factor in averaging down
            decisions. Apply Framework B fully.

Cash Buffer Preference impact:
  Minimal    → Framework E triggers at >50% cash as designed.
  Moderate   → Framework E triggers at >50% cash as designed.
  Substantial → Framework E triggers at >65% cash. Hold cash below
                this threshold without requiring explicit justification.

Portfolio Significance impact:
  Discretionary → No modification to frameworks.
  Meaningful    → Reduce maximum single-position concentration from
                  50% to 40% of portfolio.
  Primary       → Reduce maximum single-position concentration from
                  50% to 35% of portfolio. Require two confirming
                  thesis signals before averaging down.

Drawdown Behaviour impact:
  Hold through    → Framework A: -10% hard stop only. No earlier exit signals.
  Tighten gradually → Framework A: At -7% loss, explicitly reassess thesis
                      and flag if any weakening signals are present.
  Exit early      → Framework A: At -6% loss, begin flagging exit option
                    even if thesis is technically intact. Recommend partial
                    exit if two or more minor concerns are present.
```

### 3.3 Add Profile Check to YOUR TASK Section

Add the following instruction immediately before the existing framework task instructions:

```
INVESTOR PROFILE CHECK:
Before reasoning through any framework, internalise the investor profile
in Layer 0. Every recommendation must reflect who this investor is, not
just what the market signals suggest. When profile settings moderate a
recommendation, state this explicitly:
  "Given your [Conservative risk tolerance / Low lock-period comfort /
  Primary portfolio significance], I am recommending [X] rather than
  [Y] which the market signals alone would suggest."
```

---

## 4. Concrete Example: How Profile Changes the CR012 Averaging Down

### Profile A — Aggressive / High AI conviction / High lock comfort / Discretionary
Market signal: buy 3 shares NVDA
Profile modifier: none — aggressive profile supports full deployment
**Recommendation: BUY 3 shares** (same as current)

### Profile B — Moderate / High AI conviction / Low lock comfort / Meaningful
Market signal: buy 3 shares NVDA
Profile modifier: low lock-period comfort + macro deteriorating (SPY -3.86%)
  → reduce averaging scale by 50%
  → explicitly flag lock-period risk
**Recommendation: BUY 1-2 shares** with explicit lock-period risk warning

### Profile C — Conservative / Medium AI conviction / Low lock comfort / Primary
Market signal: buy 3 shares NVDA
Profile modifier: conservative risk + primary significance + low lock comfort
  → Framework B max averaging = 20% of cash = ~$255 = 1 share
  → concentration limit reduced to 35%
  → require two confirming thesis signals (Amazon deal = 1, Planet Labs = 2 ✅)
**Recommendation: BUY 1 share** with capital preservation framing

Same market. Same frameworks. Three different right answers for three different investors.

---

## 5. Default Profile

Until the user explicitly sets their profile, the advisor assumes:

```
RISK TOLERANCE: Moderate
AI THESIS CONVICTION: High (evidenced by portfolio composition)
LOCK-PERIOD COMFORT: Medium
CASH BUFFER PREFERENCE: Moderate
PORTFOLIO SIGNIFICANCE: Meaningful
DRAWDOWN BEHAVIOUR: Hold through
```

These defaults reflect the profile implied by the existing portfolio behaviour — concentrated AI positions, willingness to hold through drawdowns, active engagement with the advisor system.

---

## 6. What Does Not Change

- Layer 1 hard constraints — never overridden by profile
- Signal hierarchy (CR010) — profile modifies thresholds, not priority order
- Narrative boundary rule (CR011) — unchanged
- Framework logic — unchanged; profile adjusts parameters within frameworks
- Response format — unchanged; profile influence stated in reasoning field
- Hard stop-loss at -10% — unchanged regardless of profile

---

## 7. Success Criteria

| Scenario | Expected Behaviour |
|---|---|
| Conservative profile, averaging down signal | Smaller position recommended; lock-period risk explicitly flagged |
| Aggressive profile, averaging down signal | Full scale deployment recommended as per Framework B |
| Primary significance, concentration approaching 50% | Advisor flags earlier at 35% limit, not 50% |
| Low lock-period comfort, deteriorating macro | Averaging down deferred or reduced; explicit reasoning citing profile |
| High AI conviction, RSI slightly above 50 | Entry considered despite RSI; profile cited as moderating factor |
| Profile conflicts with market signal | Conflict stated explicitly in reasoning; profile influence explained |
| No profile set | Default profile applied; advisor notes defaults being used |

---

## 8. Out of Scope

- This CR does not build a UI for profile configuration
- This CR does not make the profile dynamic or self-updating based on behaviour
- This CR does not add new data inputs beyond the profile block
- Profile settings are manually configured by the user in the prompt
- This is a prompt architecture change only — no application code changes required