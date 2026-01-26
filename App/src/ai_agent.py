"""
ai_agent.py - LLM Integration (Claude API)

Responsibilities:
- Build prompt from market context + portfolio state + strategy rules
- Call Claude API
- Parse JSON response
- Validate recommendations against hard constraints
- Handle API errors

Key Functions:
- build_prompt(context: dict, strategy: str) -> str
- get_recommendation(context: dict, strategy: str) -> dict
- parse_recommendation(response: str) -> dict
- validate_actions(actions: list, context: dict) -> list
"""

import os
import json
import re
import time
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# =============================================================================
# Retry Configuration
# =============================================================================

MAX_API_RETRIES = 3
RETRY_DELAY = 2.0
RETRY_BACKOFF = 2.0


# =============================================================================
# Prompt Building
# =============================================================================

def build_prompt(context: dict, strategy: str) -> str:
    """
    Build the prompt for Claude API.

    Args:
        context: Market context from analyzer.generate_market_context()
        strategy: Strategy principles text

    Returns:
        Formatted prompt string
    """
    # Format current positions
    positions_text = _format_positions(context.get('current_positions', []))

    # Format rankings
    rankings_text = _format_rankings(context.get('rankings', {}))

    # Format entry opportunities
    opportunities_text = _format_opportunities(context.get('entry_opportunities', []))

    # Format lock status
    lock_status = context.get('portfolio_lock_status', {})
    lock_text = _format_lock_status(lock_status)

    # Format news
    news_text = _format_news(context.get('news_highlights', []))

    # Get config values
    config = context.get('config', {})
    cash = context.get('cash_available', 0)
    transaction_fee = config.get('transaction_fee', 10)

    # Format holdings for cash flow calculations
    positions = context.get('current_positions', [])
    holdings_cashflow = _format_holdings_for_cashflow(positions, transaction_fee)

    prompt = f"""You are a portfolio advisor managing a tech stock portfolio.

STRATEGY PRINCIPLES:
{strategy}

REGULATORY CONSTRAINT (IMMUTABLE):
- Minimum 30-day hold from purchase (FIFO rule)
- Cannot sell positions held < 30 days under ANY circumstance
- This is a hard constraint - never recommend selling locked positions

CURRENT PORTFOLIO:
{positions_text}

Cash Available: ${cash:,.2f}

LOCK STATUS:
{lock_text}

STOCK RANKINGS (by fundamental score):
{rankings_text}

ENTRY OPPORTUNITIES (Top 3 not in portfolio):
{opportunities_text}

RECENT NEWS:
{news_text}

CONSTRAINTS:
- Maximum positions: {config.get('max_positions', 3)}
- Transaction fee: ${transaction_fee} per trade
- Monthly budget: ${config.get('monthly_budget', 400)}
- Stop loss threshold: {config.get('stop_loss_percent', -10)}%
- Profit target: +{config.get('profit_target_percent', 20)}%
- Minimum swap benefit: $50 after fees

SEQUENTIAL CASH FLOW CALCULATION (CRITICAL):
When recommending SELL followed by BUY actions, you MUST calculate cash flow sequentially:

Current Holdings (for proceeds calculation):
{holdings_cashflow}

Instructions:
1. For each SELL action, calculate expected proceeds:
   proceeds = (quantity x current_price) - ${transaction_fee} fee
2. Add proceeds to available cash: running_cash = ${cash:,.2f} + sum(all_sell_proceeds)
3. Only recommend BUY amounts up to the running_cash total
4. Include your calculation in the reasoning field

Example:
- Starting cash: $0, Holdings: MSFT 1.5 shares @ $465.95
- SELL MSFT: proceeds = (1.5 x $465.95) - $10 = $689
- Running cash: $0 + $689 = $689
- BUY NFLX: recommend "$689" (not more), reasoning: "Using $689 from MSFT sale"

Your numbers must be accurate - the user will execute these trades.

YOUR TASK:
Analyze the current situation and recommend specific actions (BUY/SELL/HOLD) with clear reasoning.
Consider:
1. FIFO constraints - can locked positions be sold?
2. Ranking quality - are current holdings still top-ranked?
3. Entry timing - are there better opportunities?
4. Transaction costs - is any swap worth the fees?

RESPONSE FORMAT (respond with valid JSON only):
{{
  "actions": [
    {{
      "type": "SELL" | "BUY" | "HOLD",
      "ticker": "SYMBOL",
      "amount": "all shares" | "$XXX" | "X shares",
      "expected_proceeds": 689.00,  // SELL only: net proceeds after fee
      "cash_source": "MSFT sale proceeds",  // BUY only: where the money comes from
      "reasoning": "Detailed explanation including cash flow calculation"
    }}
  ],
  "overall_strategy": "Brief portfolio-level explanation of the recommended approach",
  "risk_warnings": ["Warning 1", "Warning 2"],
  "confidence": "HIGH" | "MEDIUM" | "LOW"
}}

Important: Your response must be valid JSON only, no markdown or other formatting."""

    return prompt


def _format_positions(positions: list) -> str:
    """Format current positions for prompt."""
    if not positions:
        return "No current positions."

    lines = []
    for pos in positions:
        ticker = pos.get('ticker', '')
        qty = pos.get('quantity', 0)
        purchase = pos.get('purchase_price', 0)
        current = pos.get('current_price', 0)
        pnl = pos.get('pnl_percent', 0)
        days = pos.get('days_held', 0)
        rank = pos.get('rank', 'N/A')
        sellable = "SELLABLE" if pos.get('is_sellable', False) else "LOCKED"

        lines.append(
            f"- {ticker}: {qty} shares @ ${purchase:.2f} (now ${current:.2f}), "
            f"P&L: {pnl:+.1f}%, Days held: {days}, Rank: #{rank}, Status: {sellable}"
        )

        # Add exit signals/warnings
        for signal in pos.get('exit_signals', []):
            lines.append(f"  [!] {signal}")
        for warning in pos.get('exit_warnings', []):
            lines.append(f"  [!] {warning}")

    return "\n".join(lines)


def _format_rankings(rankings: dict) -> str:
    """Format stock rankings for prompt."""
    if not rankings:
        return "No rankings available."

    lines = []
    sorted_rankings = sorted(rankings.items(), key=lambda x: x[1].get('rank', 99))

    for ticker, data in sorted_rankings[:10]:  # Top 10
        rank = data.get('rank', 0)
        score = data.get('score', 0)
        fundamentals = data.get('fundamentals', {})
        technicals = data.get('technicals', {})

        pe = fundamentals.get('pe_ratio', 0)
        rev_growth = (fundamentals.get('revenue_growth_yoy', 0) or 0) * 100
        rsi = technicals.get('rsi_14', 0)

        lines.append(
            f"#{rank} {ticker}: Score={score:.1f}, P/E={pe:.1f}, "
            f"RevGrowth={rev_growth:.1f}%, RSI={rsi:.1f}"
        )

    return "\n".join(lines)


def _format_opportunities(opportunities: list) -> str:
    """Format entry opportunities for prompt."""
    if not opportunities:
        return "No entry opportunities (all top 3 already held)."

    lines = []
    for opp in opportunities:
        ticker = opp.get('ticker', '')
        rank = opp.get('rank', 0)
        price = opp.get('current_price', 0)
        rec = opp.get('entry_recommendation', '')
        rsi = opp.get('rsi', 50)

        lines.append(
            f"- {ticker} (Rank #{rank}): ${price:.2f}, RSI={rsi:.1f}, Entry: {rec}"
        )

        for signal in opp.get('entry_signals', []):
            lines.append(f"  [+] {signal}")
        for warning in opp.get('entry_warnings', []):
            lines.append(f"  [!] {warning}")

    return "\n".join(lines)


def _format_lock_status(lock_status: dict) -> str:
    """Format portfolio lock status for prompt."""
    total = lock_status.get('total_positions', 0)
    sellable = lock_status.get('sellable_count', 0)
    locked = lock_status.get('locked_count', 0)
    next_unlock = lock_status.get('next_unlock_date', '')

    if total == 0:
        return "No positions to evaluate."

    status = f"Total: {total} positions, Sellable: {sellable}, Locked: {locked}"
    if next_unlock:
        status += f"\nNext unlock date: {next_unlock}"

    return status


def _format_news(news: list) -> str:
    """Format news highlights for prompt."""
    if not news:
        return "No recent news."

    lines = []
    seen = set()  # Avoid duplicates
    for item in news[:10]:
        title = item.get('title', '')
        if title and title not in seen:
            ticker = item.get('ticker', '')
            date = item.get('date', '')
            lines.append(f"- [{ticker}] {title} ({date})")
            seen.add(title)

    return "\n".join(lines) if lines else "No recent news."


def _format_holdings_for_cashflow(positions: list, transaction_fee: float) -> str:
    """
    Format current holdings with prices for cash flow calculations.

    Args:
        positions: List of current positions with current_price
        transaction_fee: Fee per transaction

    Returns:
        Formatted string showing holdings and potential proceeds
    """
    if not positions:
        return "No holdings to sell."

    lines = []
    for pos in positions:
        ticker = pos.get('ticker', '')
        qty = pos.get('quantity', 0)
        current = pos.get('current_price', 0)
        is_sellable = pos.get('is_sellable', False)

        gross_value = qty * current
        net_proceeds = gross_value - transaction_fee
        status = "SELLABLE" if is_sellable else "LOCKED"

        lines.append(
            f"- {ticker}: {qty} shares x ${current:.2f} = ${gross_value:.2f} "
            f"(net after fee: ${net_proceeds:.2f}) [{status}]"
        )

    return "\n".join(lines)


# =============================================================================
# Claude API Integration
# =============================================================================

def get_recommendation(context: dict, strategy: str) -> dict:
    """
    Get AI recommendation from Claude API with retry logic.

    Args:
        context: Market context from analyzer
        strategy: Strategy principles text

    Returns:
        Parsed recommendation dictionary
    """
    try:
        import anthropic
    except ImportError:
        return {
            'error': 'anthropic package not installed. Run: pip install anthropic',
            'actions': [],
            'overall_strategy': '',
            'risk_warnings': ['API client not available'],
            'confidence': 'LOW'
        }

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {
            'error': 'ANTHROPIC_API_KEY not found in environment',
            'actions': [],
            'overall_strategy': '',
            'risk_warnings': ['API key not configured'],
            'confidence': 'LOW'
        }

    # Build the prompt
    prompt = build_prompt(context, strategy)
    client = anthropic.Anthropic(api_key=api_key)

    # Retry loop
    last_error = None
    current_delay = RETRY_DELAY

    for attempt in range(MAX_API_RETRIES + 1):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.3,  # Lower temp for more consistent reasoning
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract response text
            response_text = message.content[0].text

            # Parse the response
            recommendation = parse_recommendation(response_text)

            # Validate actions against constraints
            if recommendation.get('actions'):
                recommendation['actions'] = validate_actions(
                    recommendation['actions'],
                    context
                )

            return recommendation

        except anthropic.APIConnectionError as e:
            last_error = ('connection', str(e))
            if attempt < MAX_API_RETRIES:
                print(f"  [!] API connection failed (attempt {attempt + 1}/{MAX_API_RETRIES + 1})")
                print(f"      Retrying in {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay *= RETRY_BACKOFF
            continue

        except anthropic.RateLimitError as e:
            last_error = ('rate_limit', str(e))
            if attempt < MAX_API_RETRIES:
                # Rate limit needs longer delay
                wait_time = current_delay * 2
                print(f"  [!] Rate limited (attempt {attempt + 1}/{MAX_API_RETRIES + 1})")
                print(f"      Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                current_delay *= RETRY_BACKOFF
            continue

        except anthropic.APIStatusError as e:
            # Don't retry on 4xx client errors (except 429 rate limit)
            if hasattr(e, 'status_code') and 400 <= e.status_code < 500:
                return {
                    'error': f'API error ({e.status_code}): {str(e)}',
                    'actions': [],
                    'overall_strategy': '',
                    'risk_warnings': ['API returned a client error'],
                    'confidence': 'LOW'
                }
            last_error = ('api_status', str(e))
            if attempt < MAX_API_RETRIES:
                print(f"  [!] API error (attempt {attempt + 1}/{MAX_API_RETRIES + 1})")
                print(f"      Retrying in {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay *= RETRY_BACKOFF
            continue

        except Exception as e:
            last_error = ('unexpected', str(e))
            break  # Don't retry on unexpected errors

    # All retries failed
    error_type, error_msg = last_error if last_error else ('unknown', 'Unknown error')

    error_messages = {
        'connection': ('Could not connect to Claude API', 'Connection error'),
        'rate_limit': ('API rate limit reached after retries', 'Rate limit exceeded'),
        'api_status': ('API returned an error', 'API error'),
        'unexpected': ('An unexpected error occurred', 'Unexpected error'),
        'unknown': ('Unknown error occurred', 'Unknown error')
    }

    warning, prefix = error_messages.get(error_type, error_messages['unknown'])

    return {
        'error': f'{prefix}: {error_msg}',
        'actions': [],
        'overall_strategy': '',
        'risk_warnings': [warning],
        'confidence': 'LOW'
    }


# =============================================================================
# Response Parsing
# =============================================================================

def parse_recommendation(response: str) -> dict:
    """
    Parse Claude's response into structured recommendation.

    Args:
        response: Raw response text from Claude

    Returns:
        Parsed recommendation dictionary
    """
    # Default structure
    default = {
        'actions': [],
        'overall_strategy': '',
        'risk_warnings': [],
        'confidence': 'LOW',
        'raw_response': response
    }

    try:
        # Try to parse as JSON directly
        result = json.loads(response)
        return result

    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                return result
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result
            except json.JSONDecodeError:
                pass

        # Return default with error
        default['error'] = 'Could not parse JSON response'
        default['overall_strategy'] = 'Unable to parse AI response. Please review manually.'
        return default


# =============================================================================
# Action Validation
# =============================================================================

def validate_actions(actions: list, context: dict) -> list:
    """
    Validate and annotate actions against hard constraints.
    Accounts for sequential cash flow (proceeds from SELLs available for BUYs).

    Args:
        actions: List of action dictionaries
        context: Market context

    Returns:
        Validated actions with warnings
    """
    validated = []
    positions = context.get('current_positions', [])
    lock_status = context.get('portfolio_lock_status', {}).get('positions', {})
    config = context.get('config', {})
    transaction_fee = config.get('transaction_fee', 10)

    # Build position lookup for quick access
    position_lookup = {pos.get('ticker'): pos for pos in positions}

    # Track running cash (starts with available cash, increases with SELLs)
    running_cash = context.get('cash_available', 0)

    for action in actions:
        action_type = action.get('type', '').upper()
        ticker = action.get('ticker', '')

        # Check SELL actions against FIFO
        if action_type == 'SELL':
            position_lock = lock_status.get(ticker, {})
            if position_lock and not position_lock.get('is_sellable', True):
                # Mark as invalid - position is locked
                action['valid'] = False
                action['validation_error'] = (
                    f"INVALID: {ticker} is LOCKED (held {position_lock.get('days_held', 0)} days). "
                    f"Cannot sell until {position_lock.get('unlock_date', 'N/A')}."
                )
            else:
                action['valid'] = True

                # Calculate proceeds and add to running cash
                pos = position_lookup.get(ticker, {})
                qty = pos.get('quantity', 0)
                current_price = pos.get('current_price', 0)
                gross_value = qty * current_price
                net_proceeds = gross_value - transaction_fee

                # Add proceeds to running cash for subsequent BUY validation
                running_cash += net_proceeds

                # Verify AI's calculation if provided
                ai_proceeds = action.get('expected_proceeds')
                if ai_proceeds is not None:
                    diff = abs(float(ai_proceeds) - net_proceeds)
                    if diff > 50:
                        action['validation_warning'] = (
                            f"AI calculated ${ai_proceeds:.2f} proceeds, "
                            f"actual would be ${net_proceeds:.2f}"
                        )

        elif action_type == 'BUY':
            # Validate against running cash (includes proceeds from prior SELLs)
            amount_str = action.get('amount', '')
            if '$' in str(amount_str):
                try:
                    amount = float(re.sub(r'[^\d.]', '', str(amount_str)))
                    if amount > running_cash + 10:  # $10 buffer for rounding
                        action['validation_warning'] = (
                            f"Requested ${amount:.2f} but only ${running_cash:.2f} available "
                            f"(including proceeds from prior SELLs)"
                        )
                except ValueError:
                    pass
            action['valid'] = True

        else:  # HOLD
            action['valid'] = True

        validated.append(action)

    return validated


# =============================================================================
# Utility Functions
# =============================================================================

def format_recommendation_text(recommendation: dict) -> str:
    """
    Format recommendation for terminal display.

    Args:
        recommendation: Parsed recommendation dictionary

    Returns:
        Formatted text string
    """
    lines = []

    # Check for errors
    if recommendation.get('error'):
        lines.append(f"ERROR: {recommendation['error']}")
        lines.append("")

    # Overall strategy
    strategy = recommendation.get('overall_strategy', '')
    if strategy:
        lines.append("STRATEGY SUMMARY")
        lines.append("-" * 40)
        lines.append(strategy)
        lines.append("")

    # Actions
    actions = recommendation.get('actions', [])
    if actions:
        lines.append("RECOMMENDED ACTIONS")
        lines.append("-" * 40)

        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'UNKNOWN')
            ticker = action.get('ticker', '')
            amount = action.get('amount', '')
            reasoning = action.get('reasoning', '')
            valid = action.get('valid', True)

            # Action header
            status = "[+]" if valid else "[X]"
            lines.append(f"{i}. [{status}] {action_type} {ticker} - {amount}")

            # Validation error/warning
            if action.get('validation_error'):
                lines.append(f"   [!] {action['validation_error']}")
            if action.get('validation_warning'):
                lines.append(f"   [!] {action['validation_warning']}")

            # Reasoning
            if reasoning:
                lines.append(f"   Reasoning: {reasoning}")

            lines.append("")
    else:
        lines.append("No specific actions recommended.")
        lines.append("")

    # Risk warnings
    warnings = recommendation.get('risk_warnings', [])
    if warnings:
        lines.append("RISK WARNINGS")
        lines.append("-" * 40)
        for warning in warnings:
            lines.append(f"[!] {warning}")
        lines.append("")

    # Confidence
    confidence = recommendation.get('confidence', 'UNKNOWN')
    lines.append(f"Confidence Level: {confidence}")

    return "\n".join(lines)
