"""
recommendations_manager.py - Recommendation Ledger Management

Responsibilities:
- Load/save recommendation records from/to recommendations_ledger.json
- Record new recommendations with portfolio/market snapshots
- Match executed trades to pending recommendations
- Simulate past recommendations against current prices
- Calculate P&L and verdict (GOOD/BAD/NEUTRAL)
- Prune old entries to prevent unbounded growth

Key Functions:
- load_ledger() -> dict
- save_ledger(ledger: dict) -> bool
- record_recommendation(portfolio, context, recommendation, market_data) -> str
- match_trade_to_recommendations(trade_type, ticker, quantity, price, date) -> str
- simulate_recommendation(rec_id, current_prices) -> dict
- list_recommendations(limit, filters) -> list
- prune_ledger(ledger, max_entries) -> int
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# =============================================================================
# Configuration
# =============================================================================

LEDGER_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'config',
    'recommendations_ledger.json'
)

# Limits
MAX_LEDGER_ENTRIES = 100
PRUNE_AFTER_DAYS = 180
TRADE_MATCH_WINDOW_DAYS = 7
VERDICT_THRESHOLD = 50.0  # Dollar threshold for GOOD/BAD verdict


# =============================================================================
# Schema
# =============================================================================

def get_empty_ledger() -> dict:
    """
    Return an empty ledger structure.

    Schema:
    {
        "version": "1.0",
        "last_updated": "2026-03-03T16:08:29Z",
        "statistics": {
            "total_recommendations": 0,
            "total_accepted": 0,
            "total_partial": 0,
            "total_skipped": 0,
            "last_pruned": null
        },
        "recommendations": []
    }
    """
    return {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "statistics": {
            "total_recommendations": 0,
            "total_accepted": 0,
            "total_partial": 0,
            "total_skipped": 0,
            "last_pruned": None
        },
        "recommendations": []
    }


def generate_recommendation_id() -> str:
    """Generate unique recommendation ID: rec_YYYYMMDD_HHMMSS"""
    return datetime.now().strftime("rec_%Y%m%d_%H%M%S")


# =============================================================================
# Load / Save
# =============================================================================

def load_ledger() -> dict:
    """
    Load ledger from JSON file, or create empty structure if not exists.

    Also finalizes stale pending recommendations (older than 7 days).

    Returns:
        Ledger dictionary
    """
    if not os.path.exists(LEDGER_FILE):
        return get_empty_ledger()

    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        if 'recommendations' not in data:
            data['recommendations'] = []
        if 'statistics' not in data:
            data['statistics'] = get_empty_ledger()['statistics']
        if 'version' not in data:
            data['version'] = '1.0'

        # Finalize stale pending recommendations
        finalized = finalize_stale_recommendations(data)
        if finalized > 0:
            save_ledger(data)

        return data

    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load recommendations_ledger.json: {e}")
        print("Starting with empty ledger.")
        return get_empty_ledger()


def save_ledger(ledger: dict) -> bool:
    """
    Save ledger to JSON file.

    Args:
        ledger: Ledger dictionary to save

    Returns:
        True if successful, False otherwise
    """
    try:
        # Update timestamp
        ledger['last_updated'] = datetime.now().isoformat()

        # Update statistics
        _update_statistics(ledger)

        # Ensure config directory exists
        os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)

        with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
            json.dump(ledger, f, indent=2, default=str)

        return True

    except (IOError, TypeError) as e:
        print(f"Warning: Failed to save recommendations_ledger.json: {e}")
        return False


def _update_statistics(ledger: dict) -> None:
    """Update statistics based on current recommendations."""
    recs = ledger.get('recommendations', [])
    stats = ledger.get('statistics', {})

    stats['total_recommendations'] = len(recs)
    stats['total_accepted'] = sum(1 for r in recs if r.get('outcome') == 'accepted')
    stats['total_partial'] = sum(1 for r in recs if r.get('outcome') == 'partial')
    stats['total_skipped'] = sum(1 for r in recs if r.get('outcome') == 'skipped')

    ledger['statistics'] = stats


# =============================================================================
# Recording Recommendations
# =============================================================================

def record_recommendation(
    portfolio: dict,
    context: dict,
    recommendation: dict,
    market_data: dict
) -> str:
    """
    Record a new recommendation to the ledger.

    Called at end of cmd_run() after successful AI response.

    Args:
        portfolio: Current portfolio state
        context: Market context from analyzer
        recommendation: AI recommendation response
        market_data: Raw market data for price extraction

    Returns:
        Generated recommendation ID
    """
    ledger = load_ledger()

    rec_id = generate_recommendation_id()

    # Build record
    record = {
        "id": rec_id,
        "timestamp": datetime.now().isoformat(),
        "outcome": "pending",
        "outcome_timestamp": None,

        "portfolio_snapshot": build_portfolio_snapshot(portfolio, context),
        "market_snapshot": build_market_snapshot(context, market_data),
        "recommendation": extract_recommendation_summary(recommendation),

        "execution": {
            "matched_at": None,
            "trades_matched": []
        },
        "simulation": None
    }

    ledger['recommendations'].append(record)

    # Prune if needed
    if len(ledger['recommendations']) > MAX_LEDGER_ENTRIES:
        prune_ledger(ledger)

    save_ledger(ledger)

    return rec_id


def build_portfolio_snapshot(portfolio: dict, context: dict) -> dict:
    """Extract minimal portfolio snapshot for ledger."""
    positions = context.get('current_positions', [])

    snapshot_positions = []
    for pos in positions:
        snapshot_positions.append({
            "ticker": pos.get('ticker'),
            "total_quantity": pos.get('total_quantity'),
            "average_cost": pos.get('average_cost'),
            "current_price": pos.get('current_price'),
            "pnl_percent": pos.get('pnl_percent'),
            "lock_status": pos.get('lock_status'),
            "sellable_quantity": pos.get('sellable_quantity')
        })

    # Calculate total value
    total_value = sum(
        (pos.get('total_quantity', 0) * pos.get('current_price', 0))
        for pos in positions
    )
    cash = portfolio.get('cash_available', 0)

    return {
        "positions": snapshot_positions,
        "cash_available": cash,
        "total_value": round(total_value + cash, 2)
    }


def build_market_snapshot(context: dict, market_data: dict) -> dict:
    """Extract minimal market snapshot for ledger."""
    rankings = context.get('rankings', {})

    # Get top 3
    sorted_rankings = sorted(
        rankings.items(),
        key=lambda x: x[1].get('rank', 99)
    )
    top_3 = [ticker for ticker, _ in sorted_rankings[:3]]

    # Extract prices for all relevant tickers
    rankings_snapshot = {}
    for ticker, data in rankings.items():
        ticker_data = market_data.get('tickers', {}).get(ticker, {})
        price_data = ticker_data.get('price', {})

        rankings_snapshot[ticker] = {
            "rank": data.get('rank'),
            "score": data.get('score'),
            "price": price_data.get('current_price', 0)
        }

    # Get benchmark
    benchmark = market_data.get('benchmark', {})
    benchmark_30d = benchmark.get('return_30d', 0)

    return {
        "top_3": top_3,
        "rankings": rankings_snapshot,
        "benchmark_spy_30d": benchmark_30d
    }


def extract_recommendation_summary(recommendation: dict) -> dict:
    """Extract action details with normalized quantities."""
    actions = recommendation.get('actions', [])

    summarized_actions = []
    for action in actions:
        summarized = {
            "type": action.get('type'),
            "ticker": action.get('ticker'),
            "amount": action.get('amount'),
            "reasoning": action.get('reasoning', '')[:500],  # Truncate long reasoning
            "valid": action.get('valid', True)
        }

        # Extract numeric quantity if possible
        amount_str = action.get('amount', '')
        quantity = _parse_quantity(amount_str)
        if quantity:
            summarized['quantity'] = quantity

        # Add expected values
        if action.get('type') == 'SELL':
            summarized['expected_proceeds'] = action.get('expected_proceeds')
        elif action.get('type') == 'BUY':
            summarized['expected_quantity'] = action.get('expected_quantity')

        summarized_actions.append(summarized)

    return {
        "actions": summarized_actions,
        "overall_strategy": recommendation.get('overall_strategy', '')[:500],
        "confidence": recommendation.get('confidence', 'LOW'),
        "risk_warnings": recommendation.get('risk_warnings', [])
    }


def _parse_quantity(amount_str: str) -> Optional[float]:
    """Parse quantity from amount string like '1.5 shares' or 'all shares'."""
    if not amount_str:
        return None

    amount_str = amount_str.lower().strip()

    # Handle "all shares" - can't determine numeric value
    if 'all' in amount_str:
        return None

    # Handle "$XXX" format
    if amount_str.startswith('$'):
        return None

    # Try to extract number
    import re
    match = re.search(r'([\d.]+)\s*shares?', amount_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    # Try direct float
    try:
        return float(amount_str)
    except ValueError:
        return None


# =============================================================================
# Trade Matching
# =============================================================================

def match_trade_to_recommendations(
    trade_type: str,
    ticker: str,
    quantity: float,
    price: float,
    trade_date: str
) -> Optional[str]:
    """
    Match executed trade to pending recommendation.

    Algorithm:
    1. Load ledger, filter to pending recommendations from last 7 days
    2. For each, check if any action matches (type + ticker)
    3. Update match, calculate variance
    4. If all actions matched, set outcome to 'accepted'

    Args:
        trade_type: 'sold' or 'bought'
        ticker: Stock ticker
        quantity: Number of shares
        price: Execution price
        trade_date: Date of trade (YYYY-MM-DD)

    Returns:
        recommendation_id if matched, None otherwise
    """
    ledger = load_ledger()

    # Filter candidates - pending recommendations from last 7 days
    cutoff = (datetime.now() - timedelta(days=TRADE_MATCH_WINDOW_DAYS)).isoformat()
    candidates = [
        r for r in ledger.get('recommendations', [])
        if r.get('outcome') == 'pending' and r['timestamp'] > cutoff
    ]

    if not candidates:
        return None

    # Match most recent first
    for rec in reversed(candidates):
        actions = rec.get('recommendation', {}).get('actions', [])

        for i, action in enumerate(actions):
            # Map action type to trade type
            action_type = action.get('type', '').upper()
            expected_trade_type = 'sold' if action_type == 'SELL' else 'bought' if action_type == 'BUY' else None

            if expected_trade_type != trade_type:
                continue
            if action.get('ticker', '').upper() != ticker.upper():
                continue

            # Match found - check if already matched
            execution = rec.setdefault('execution', {'trades_matched': []})
            already_matched = any(
                m.get('action_index') == i
                for m in execution.get('trades_matched', [])
            )
            if already_matched:
                continue

            # Calculate variance from expected price
            expected_price = _get_expected_price(action, rec)
            variance = calculate_execution_variance(expected_price, price) if expected_price else 0

            # Record match
            match_record = {
                'action_index': i,
                'executed': True,
                'actual_price': price,
                'actual_quantity': quantity,
                'variance_percent': variance,
                'matched_at': datetime.now().isoformat()
            }
            execution['trades_matched'].append(match_record)
            execution['matched_at'] = datetime.now().isoformat()

            # Check if all actions now matched
            total_actions = len([a for a in actions if a.get('type') != 'HOLD'])
            matched_count = len(execution['trades_matched'])

            if matched_count >= total_actions and total_actions > 0:
                rec['outcome'] = 'accepted'
                rec['outcome_timestamp'] = datetime.now().isoformat()

            save_ledger(ledger)
            return rec['id']

    return None


def _get_expected_price(action: dict, rec: dict) -> Optional[float]:
    """Get expected price for an action from market snapshot."""
    ticker = action.get('ticker')
    market_snapshot = rec.get('market_snapshot', {})
    rankings = market_snapshot.get('rankings', {})
    ticker_data = rankings.get(ticker, {})
    return ticker_data.get('price')


def calculate_execution_variance(expected_price: float, actual_price: float) -> float:
    """Calculate % variance between expected and actual execution price."""
    if not expected_price or expected_price == 0:
        return 0
    return round(((actual_price - expected_price) / expected_price) * 100, 2)


def finalize_stale_recommendations(ledger: dict) -> int:
    """
    Finalize pending recommendations older than 7 days.

    Returns:
        Number of recommendations finalized
    """
    cutoff = (datetime.now() - timedelta(days=TRADE_MATCH_WINDOW_DAYS)).isoformat()
    finalized = 0

    for rec in ledger.get('recommendations', []):
        if rec.get('outcome') != 'pending':
            continue
        if rec['timestamp'] > cutoff:
            continue

        # Check if any trades matched
        execution = rec.get('execution', {})
        matched = execution.get('trades_matched', [])

        if matched:
            rec['outcome'] = 'partial'
            rec['execution']['partial_reason'] = 'Timeout: only some actions executed'
        else:
            rec['outcome'] = 'skipped'

        rec['outcome_timestamp'] = datetime.now().isoformat()
        finalized += 1

    return finalized


# =============================================================================
# Simulation
# =============================================================================

def simulate_recommendation(rec_id: str, current_prices: dict) -> dict:
    """
    Calculate P&L if recommendation was followed vs ignored.

    Args:
        rec_id: Recommendation ID to simulate
        current_prices: Dict of {ticker: current_price}

    Returns:
        Simulation results with verdict
    """
    ledger = load_ledger()
    rec = get_recommendation_by_id(rec_id)

    if not rec:
        return {"error": f"Recommendation {rec_id} not found"}

    # Get prices at time of recommendation
    market_snapshot = rec.get('market_snapshot', {})
    rankings = market_snapshot.get('rankings', {})
    prices_then = {ticker: data.get('price', 0) for ticker, data in rankings.items()}

    # Calculate days elapsed
    rec_timestamp = rec.get('timestamp', '')
    try:
        rec_date = datetime.fromisoformat(rec_timestamp.replace('Z', '+00:00'))
        days_elapsed = (datetime.now() - rec_date.replace(tzinfo=None)).days
    except (ValueError, TypeError):
        days_elapsed = 0

    # Calculate hypothetical P&L
    recommendation = rec.get('recommendation', {})
    transaction_fee = 1.0  # Default fee

    hypothetical = calculate_hypothetical_pnl(
        recommendation,
        prices_then,
        current_prices,
        transaction_fee
    )

    # Determine verdict
    verdict = determine_verdict(
        hypothetical.get('if_followed', 0),
        hypothetical.get('if_ignored', 0)
    )

    simulation = {
        "calculated_at": datetime.now().isoformat(),
        "days_elapsed": days_elapsed,
        "prices_then": prices_then,
        "prices_now": current_prices,
        "hypothetical_pnl": hypothetical,
        "verdict": verdict
    }

    # Store simulation results in ledger
    rec['simulation'] = simulation
    save_ledger(ledger)

    return simulation


def calculate_hypothetical_pnl(
    recommendation: dict,
    prices_then: dict,
    prices_now: dict,
    transaction_fee: float = 1.0
) -> dict:
    """
    Calculate hypothetical P&L for followed vs ignored scenarios.

    Scenarios:
    1. SELL only: Compare holding vs selling then
    2. BUY only: Compare not buying vs buying then
    3. SELL + BUY (rotation): Compare original position vs new position
    4. HOLD: No P&L to calculate
    """
    actions = recommendation.get('actions', [])

    sells = [a for a in actions if a.get('type') == 'SELL']
    buys = [a for a in actions if a.get('type') == 'BUY']

    if_followed = 0.0
    if_ignored = 0.0
    sell_proceeds = 0.0

    # Process SELL actions
    for sell in sells:
        ticker = sell.get('ticker')
        qty = sell.get('quantity') or _parse_quantity(sell.get('amount', '')) or 0
        price_then = prices_then.get(ticker, 0)
        price_now = prices_now.get(ticker, price_then)

        if qty <= 0 or price_then <= 0:
            continue

        # If followed: Got cash from sale
        proceeds = qty * price_then - transaction_fee
        sell_proceeds += proceeds

        # If ignored: Still holding, track P&L
        holding_pnl = qty * (price_now - price_then)
        if_ignored += holding_pnl

    # Process BUY actions
    for buy in buys:
        ticker = buy.get('ticker')
        price_then = prices_then.get(ticker, 0)
        price_now = prices_now.get(ticker, price_then)

        if price_then <= 0:
            continue

        # Determine buy amount
        if sells:
            # Rotation: Use sell proceeds
            buy_amount = sell_proceeds
        else:
            # Fresh buy: Use expected quantity
            expected_qty = buy.get('expected_quantity') or buy.get('quantity') or 0
            buy_amount = expected_qty * price_then

        if buy_amount <= 0:
            continue

        qty_bought = (buy_amount - transaction_fee) / price_then
        buy_pnl = qty_bought * (price_now - price_then)
        if_followed += buy_pnl

    # If only SELL (no rotation), the "if_followed" is just avoiding loss/gain
    if sells and not buys:
        # Already captured in if_ignored (holding P&L)
        # if_followed = 0 (cash position, no change)
        pass

    return {
        'if_followed': round(if_followed, 2),
        'if_ignored': round(if_ignored, 2)
    }


def determine_verdict(
    pnl_if_followed: float,
    pnl_if_ignored: float,
    threshold: float = VERDICT_THRESHOLD
) -> str:
    """
    Determine advice quality verdict.

    GOOD: Following beat ignoring by > threshold
    BAD: Ignoring beat following by > threshold
    NEUTRAL: Within threshold either way
    """
    difference = pnl_if_followed - pnl_if_ignored

    if difference > threshold:
        return 'GOOD'
    elif difference < -threshold:
        return 'BAD'
    else:
        return 'NEUTRAL'


# =============================================================================
# Ledger Management
# =============================================================================

def prune_ledger(ledger: dict, max_entries: int = MAX_LEDGER_ENTRIES) -> int:
    """
    Prune ledger to prevent unbounded growth.

    Strategy:
    1. Never prune 'pending' recommendations
    2. Keep at least 20 recent recommendations regardless of age
    3. Preserve entries with 'GOOD' verdict for learning
    4. Prune entries older than 180 days beyond the limit

    Returns:
        Number of entries pruned
    """
    recs = ledger.get('recommendations', [])

    # Separate pending from completed
    pending = [r for r in recs if r.get('outcome') == 'pending']
    completed = [r for r in recs if r.get('outcome') != 'pending']

    # Sort completed by timestamp (oldest first)
    completed.sort(key=lambda r: r.get('timestamp', ''))

    # Calculate cutoffs
    cutoff_date = (datetime.now() - timedelta(days=PRUNE_AFTER_DAYS)).isoformat()
    max_completed = max_entries - len(pending)
    min_to_keep = 20

    # Keep recent + high-value entries
    keep = []
    for rec in reversed(completed):  # Newest first
        if len(keep) < min_to_keep:
            keep.append(rec)
        elif rec.get('timestamp', '') > cutoff_date:
            keep.append(rec)
        elif rec.get('simulation', {}).get('verdict') == 'GOOD':
            keep.append(rec)  # Keep for learning
        elif len(keep) < max_completed:
            keep.append(rec)

    pruned_count = len(completed) - len(keep)

    ledger['recommendations'] = pending + list(reversed(keep))
    ledger['statistics']['last_pruned'] = datetime.now().isoformat()

    return pruned_count


def get_ledger_summary() -> dict:
    """
    Get summary statistics for display.

    Returns:
        Summary dict with counts and averages
    """
    ledger = load_ledger()
    recs = ledger.get('recommendations', [])
    stats = ledger.get('statistics', {})

    # Count verdicts
    verdicts = {'GOOD': 0, 'BAD': 0, 'NEUTRAL': 0}
    for rec in recs:
        verdict = rec.get('simulation', {}).get('verdict')
        if verdict in verdicts:
            verdicts[verdict] += 1

    # Date range
    if recs:
        oldest = min(r.get('timestamp', '') for r in recs)[:10]
        newest = max(r.get('timestamp', '') for r in recs)[:10]
    else:
        oldest = newest = None

    return {
        'total_recommendations': stats.get('total_recommendations', 0),
        'total_accepted': stats.get('total_accepted', 0),
        'total_partial': stats.get('total_partial', 0),
        'total_skipped': stats.get('total_skipped', 0),
        'total_pending': sum(1 for r in recs if r.get('outcome') == 'pending'),
        'verdicts': verdicts,
        'date_range': {'oldest': oldest, 'newest': newest}
    }


def list_recommendations(
    limit: int = 20,
    outcome_filter: str = None,
    ticker_filter: str = None
) -> List[dict]:
    """
    List recommendations with optional filters.

    Args:
        limit: Maximum number to return
        outcome_filter: Filter by outcome ('pending', 'accepted', 'partial', 'skipped')
        ticker_filter: Filter by ticker mentioned in actions

    Returns:
        List of recommendation records (newest first)
    """
    ledger = load_ledger()
    recs = ledger.get('recommendations', [])

    # Apply filters
    filtered = []
    for rec in recs:
        if outcome_filter and rec.get('outcome') != outcome_filter:
            continue

        if ticker_filter:
            actions = rec.get('recommendation', {}).get('actions', [])
            tickers = [a.get('ticker', '').upper() for a in actions]
            if ticker_filter.upper() not in tickers:
                continue

        filtered.append(rec)

    # Return newest first, limited
    return list(reversed(filtered))[:limit]


def get_recommendation_by_id(rec_id: str) -> Optional[dict]:
    """Retrieve single recommendation by ID."""
    ledger = load_ledger()

    for rec in ledger.get('recommendations', []):
        if rec.get('id') == rec_id:
            return rec

    return None


# =============================================================================
# Price Fetching for Simulation
# =============================================================================

def fetch_current_prices_for_simulation(tickers: List[str]) -> dict:
    """
    Fetch current prices for tickers referenced in a recommendation.

    Uses yfinance directly for lightweight price-only fetch.

    Args:
        tickers: List of ticker symbols

    Returns:
        Dict of {ticker: current_price}
    """
    try:
        import yfinance as yf
    except ImportError:
        print("Warning: yfinance not available for price fetch")
        return {}

    prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            if price:
                prices[ticker] = price
        except Exception as e:
            print(f"Warning: Could not fetch price for {ticker}: {e}")

    return prices


def get_tickers_from_recommendation(rec: dict) -> List[str]:
    """Extract all tickers mentioned in a recommendation."""
    tickers = set()

    # From actions
    actions = rec.get('recommendation', {}).get('actions', [])
    for action in actions:
        ticker = action.get('ticker')
        if ticker:
            tickers.add(ticker.upper())

    # From portfolio snapshot
    positions = rec.get('portfolio_snapshot', {}).get('positions', [])
    for pos in positions:
        ticker = pos.get('ticker')
        if ticker:
            tickers.add(ticker.upper())

    # From market snapshot
    rankings = rec.get('market_snapshot', {}).get('rankings', {})
    tickers.update(rankings.keys())

    return list(tickers)
