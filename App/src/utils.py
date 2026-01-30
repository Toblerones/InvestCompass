"""
utils.py - Helper Functions

Responsibilities:
- JSON loading/saving with validation
- Date parsing and calculations
- Portfolio validation
- Configuration validation
- Path utilities
"""

import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any


# =============================================================================
# Path Utilities
# =============================================================================

def get_project_root() -> Path:
    """Get the App directory root path."""
    return Path(__file__).parent.parent


def get_config_path() -> Path:
    """Get the config directory path."""
    return get_project_root() / "config"


def get_config_file() -> Path:
    """Get the config.json file path."""
    return get_config_path() / "config.json"


def get_portfolio_file() -> Path:
    """Get the portfolio.json file path."""
    return get_config_path() / "portfolio.json"


def get_strategy_file() -> Path:
    """Get the strategy.txt file path."""
    return get_config_path() / "strategy.txt"


# =============================================================================
# JSON Loading/Saving
# =============================================================================

def load_json(file_path: Path) -> dict:
    """
    Load JSON file with error handling.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: Path, data: dict, indent: int = 2) -> None:
    """
    Save dictionary to JSON file.

    Args:
        file_path: Path to save JSON file
        data: Dictionary to save
        indent: JSON indentation level
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, default=str)


def load_config() -> dict:
    """Load configuration from config.json."""
    config_path = get_config_file()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config = load_json(config_path)
    validate_config(config)
    return config


def load_portfolio() -> dict:
    """
    Load portfolio from portfolio.json.

    Auto-detects legacy flat format and migrates to lot-based format.
    Creates a backup before migration.
    """
    portfolio_path = get_portfolio_file()
    if not portfolio_path.exists():
        raise FileNotFoundError(f"Portfolio file not found: {portfolio_path}")

    portfolio = load_json(portfolio_path)

    # Auto-migrate legacy format if needed
    if not is_lot_based_format(portfolio):
        import shutil
        backup_path = portfolio_path.with_suffix('.json.backup')
        shutil.copy2(portfolio_path, backup_path)
        print(f"  [!] Migrating portfolio to lot-based format (backup: {backup_path.name})")
        portfolio = migrate_portfolio_to_lots(portfolio)
        save_json(portfolio_path, portfolio)

    validate_portfolio(portfolio)
    return portfolio


def save_portfolio(portfolio: dict) -> None:
    """Save portfolio to portfolio.json."""
    validate_portfolio(portfolio)
    portfolio['last_updated'] = date.today().isoformat()
    save_json(get_portfolio_file(), portfolio)


def load_strategy() -> str:
    """Load strategy principles from strategy.txt."""
    strategy_path = get_strategy_file()
    if not strategy_path.exists():
        raise FileNotFoundError(f"Strategy file not found: {strategy_path}")

    with open(strategy_path, 'r', encoding='utf-8') as f:
        return f.read()


# =============================================================================
# Date Utilities
# =============================================================================

def parse_date(date_str: str) -> date:
    """
    Parse date string in YYYY-MM-DD format.

    Args:
        date_str: Date string (e.g., "2025-12-01")

    Returns:
        date object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def days_held(purchase_date: str | date) -> int:
    """
    Calculate number of days a position has been held.

    Args:
        purchase_date: Purchase date as string or date object

    Returns:
        Number of days held
    """
    if isinstance(purchase_date, str):
        purchase_date = parse_date(purchase_date)

    return (date.today() - purchase_date).days


def is_sellable(purchase_date: str | date, min_hold_days: int = 30) -> bool:
    """
    Check if position meets minimum hold requirement (FIFO rule).

    Args:
        purchase_date: Purchase date as string or date object
        min_hold_days: Minimum days to hold (default 30)

    Returns:
        True if position can be sold
    """
    return days_held(purchase_date) >= min_hold_days


def days_until_sellable(purchase_date: str | date, min_hold_days: int = 30) -> int:
    """
    Calculate days remaining until position is sellable.

    Args:
        purchase_date: Purchase date as string or date object
        min_hold_days: Minimum days to hold (default 30)

    Returns:
        Days until sellable (0 if already sellable)
    """
    held = days_held(purchase_date)
    remaining = min_hold_days - held
    return max(0, remaining)


def unlock_date(purchase_date: str | date, min_hold_days: int = 30) -> date:
    """
    Calculate the date when position becomes sellable.

    Args:
        purchase_date: Purchase date as string or date object
        min_hold_days: Minimum days to hold (default 30)

    Returns:
        Date when position unlocks
    """
    if isinstance(purchase_date, str):
        purchase_date = parse_date(purchase_date)

    return purchase_date + timedelta(days=min_hold_days)


# =============================================================================
# Validation
# =============================================================================

def validate_config(config: dict) -> None:
    """
    Validate configuration dictionary.

    Args:
        config: Configuration dictionary

    Raises:
        ValueError: If configuration is invalid
    """
    errors = []
    warnings = []

    # Required fields with type checks
    required_fields = {
        'watchlist': list,
        'monthly_budget': (int, float),
        'transaction_fee': (int, float),
        'max_positions': int
    }

    for field, expected_type in required_fields.items():
        if field not in config:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(config[field], expected_type):
            errors.append(f"{field} must be {expected_type.__name__ if isinstance(expected_type, type) else 'numeric'}")

    # Validate watchlist
    if 'watchlist' in config and isinstance(config['watchlist'], list):
        if len(config['watchlist']) == 0:
            errors.append("watchlist cannot be empty")
        else:
            invalid_tickers = []
            for ticker in config['watchlist']:
                if not isinstance(ticker, str):
                    invalid_tickers.append(str(ticker))
                elif not ticker.isupper() or not ticker.isalpha():
                    invalid_tickers.append(ticker)
            if invalid_tickers:
                errors.append(f"Invalid ticker format: {', '.join(invalid_tickers)} (must be uppercase letters only)")

    # Validate numeric fields with reasonable bounds
    if 'monthly_budget' in config:
        if isinstance(config['monthly_budget'], (int, float)):
            if config['monthly_budget'] <= 0:
                errors.append("monthly_budget must be positive")
            elif config['monthly_budget'] > 1000000:
                warnings.append("monthly_budget is very high (>$1M)")

    if 'max_positions' in config:
        if isinstance(config['max_positions'], int):
            if config['max_positions'] <= 0:
                errors.append("max_positions must be positive")
            elif config['max_positions'] > 20:
                warnings.append("max_positions is high (>20) - consider diversification limits")

    if 'transaction_fee' in config:
        if isinstance(config['transaction_fee'], (int, float)):
            if config['transaction_fee'] < 0:
                errors.append("transaction_fee cannot be negative")

    # Validate optional fields
    if 'stop_loss_percent' in config:
        if not isinstance(config['stop_loss_percent'], (int, float)):
            errors.append("stop_loss_percent must be numeric")
        elif config['stop_loss_percent'] > 0:
            warnings.append("stop_loss_percent should be negative (e.g., -10)")

    if 'profit_target_percent' in config:
        if not isinstance(config['profit_target_percent'], (int, float)):
            errors.append("profit_target_percent must be numeric")
        elif config['profit_target_percent'] < 0:
            warnings.append("profit_target_percent should be positive (e.g., 20)")

    # Print warnings
    for warning in warnings:
        print(f"  [!] Config warning: {warning}")

    if errors:
        raise ValueError("Config validation failed:\n  - " + "\n  - ".join(errors))


def validate_portfolio(portfolio: dict) -> None:
    """
    Validate portfolio dictionary (lot-based format).

    Expects positions to be lot-based: each position has a 'ticker' and 'lots' array.

    Args:
        portfolio: Portfolio dictionary

    Raises:
        ValueError: If portfolio is invalid
    """
    errors = []

    # Required fields
    if 'positions' not in portfolio:
        errors.append("Missing required field: positions")
    elif not isinstance(portfolio['positions'], list):
        errors.append("positions must be a list")

    if 'cash_available' not in portfolio:
        errors.append("Missing required field: cash_available")
    elif not isinstance(portfolio['cash_available'], (int, float)):
        errors.append("cash_available must be a number")
    elif portfolio['cash_available'] < 0:
        errors.append("cash_available cannot be negative")

    # Validate each position (lot-based)
    if 'positions' in portfolio and isinstance(portfolio['positions'], list):
        seen_tickers = set()
        for i, pos in enumerate(portfolio['positions']):
            ticker = pos.get('ticker', 'unknown')
            pos_errors = validate_position(pos)
            for err in pos_errors:
                errors.append(f"Position {i+1} ({ticker}): {err}")
            # Check for duplicate tickers
            if ticker in seen_tickers:
                errors.append(f"Position {i+1}: Duplicate ticker '{ticker}'. Use lots array for multiple purchases.")
            seen_tickers.add(ticker)

    if errors:
        raise ValueError("Portfolio validation failed:\n  - " + "\n  - ".join(errors))


def validate_position(position: dict) -> list[str]:
    """
    Validate a single position (lot-based format).

    A position has a 'ticker' and a 'lots' array, where each lot contains
    quantity, purchase_price, and purchase_date.

    Args:
        position: Position dictionary with ticker and lots

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Required fields
    if 'ticker' not in position:
        errors.append("Missing field: ticker")
    if 'lots' not in position:
        errors.append("Missing field: lots")

    # Validate ticker
    if 'ticker' in position:
        if not isinstance(position['ticker'], str):
            errors.append("ticker must be a string")
        elif not position['ticker'].isupper():
            errors.append("ticker must be uppercase")

    # Validate lots array
    if 'lots' in position:
        if not isinstance(position['lots'], list):
            errors.append("lots must be a list")
        elif len(position['lots']) == 0:
            errors.append("lots cannot be empty")
        else:
            for j, lot in enumerate(position['lots']):
                lot_errors = validate_lot(lot)
                for err in lot_errors:
                    errors.append(f"Lot {j+1}: {err}")

    return errors


def validate_lot(lot: dict) -> list[str]:
    """
    Validate a single lot within a position.

    Args:
        lot: Lot dictionary with quantity, purchase_price, purchase_date

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    required = ['quantity', 'purchase_price', 'purchase_date']
    for field in required:
        if field not in lot:
            errors.append(f"Missing field: {field}")

    if 'quantity' in lot:
        if not isinstance(lot['quantity'], (int, float)):
            errors.append("quantity must be a number")
        elif lot['quantity'] <= 0:
            errors.append("quantity must be positive")

    if 'purchase_price' in lot:
        if not isinstance(lot['purchase_price'], (int, float)):
            errors.append("purchase_price must be a number")
        elif lot['purchase_price'] <= 0:
            errors.append("purchase_price must be positive")

    if 'purchase_date' in lot:
        try:
            parse_date(lot['purchase_date'])
        except ValueError:
            errors.append("purchase_date must be YYYY-MM-DD format")

    return errors


# =============================================================================
# Position Consolidation (Lot-Based)
# =============================================================================

def consolidate_positions(raw_positions: list, min_hold_days: int = 30) -> list:
    """
    Convert lot-based positions into consolidated position views.

    Each position in raw_positions has 'ticker' and 'lots' array.
    Returns enriched positions with computed aggregates and per-lot details.

    Args:
        raw_positions: List of position dicts from portfolio.json (lot-based)
        min_hold_days: Minimum hold days for FIFO rule

    Returns:
        List of consolidated position dicts with computed fields
    """
    consolidated = []

    for pos in raw_positions:
        ticker = pos.get('ticker', '')
        lots = pos.get('lots', [])
        if not lots:
            continue

        # Sort lots by purchase_date (FIFO order)
        sorted_lots = sorted(lots, key=lambda l: l.get('purchase_date', ''))

        # Compute per-lot details
        enriched_lots = []
        total_quantity = 0
        total_cost = 0
        sellable_quantity = 0
        locked_quantity = 0

        for lot in sorted_lots:
            qty = lot.get('quantity', 0)
            price = lot.get('purchase_price', 0)
            pdate = lot.get('purchase_date', '')

            held = days_held(pdate) if pdate else 0
            lot_sellable = is_sellable(pdate, min_hold_days) if pdate else False
            lot_unlock = unlock_date(pdate, min_hold_days) if pdate else None
            days_remaining = days_until_sellable(pdate, min_hold_days) if pdate else min_hold_days

            enriched_lot = {
                'quantity': qty,
                'purchase_price': price,
                'purchase_date': pdate,
                'days_held': held,
                'is_sellable': lot_sellable,
                'unlock_date': lot_unlock.isoformat() if lot_unlock else '',
                'days_until_sellable': days_remaining,
            }
            # Preserve optional fields like notes
            if lot.get('notes'):
                enriched_lot['notes'] = lot['notes']

            enriched_lots.append(enriched_lot)

            total_quantity += qty
            total_cost += qty * price
            if lot_sellable:
                sellable_quantity += qty
            else:
                locked_quantity += qty

        # Position-level aggregates
        average_cost = total_cost / total_quantity if total_quantity > 0 else 0

        # Determine lock status
        if sellable_quantity >= total_quantity:
            lock_status = 'SELLABLE'
        elif sellable_quantity > 0:
            lock_status = 'PARTIAL_LOCK'
        else:
            lock_status = 'LOCKED'

        # Find next unlock date among locked lots
        next_unlock = None
        for lot in enriched_lots:
            if not lot['is_sellable'] and lot['unlock_date']:
                if next_unlock is None or lot['unlock_date'] < next_unlock:
                    next_unlock = lot['unlock_date']

        consolidated.append({
            'ticker': ticker,
            'total_quantity': total_quantity,
            'average_cost': round(average_cost, 2),
            'lots': enriched_lots,
            'sellable_quantity': sellable_quantity,
            'locked_quantity': locked_quantity,
            'lock_status': lock_status,
            'next_unlock_date': next_unlock,
        })

    return consolidated


def is_lot_based_format(portfolio: dict) -> bool:
    """
    Check if portfolio is in lot-based format.

    Returns True if positions use the lot-based structure (ticker + lots array),
    False if they use the legacy flat format (ticker + quantity + purchase_price).
    """
    positions = portfolio.get('positions', [])
    if not positions:
        return True  # Empty portfolio is valid in either format
    return 'lots' in positions[0]


def migrate_portfolio_to_lots(portfolio: dict) -> dict:
    """
    Migrate legacy flat-format portfolio to lot-based format.

    Groups positions by ticker and nests them as lots.

    Args:
        portfolio: Legacy portfolio dict with flat positions

    Returns:
        New portfolio dict in lot-based format
    """
    old_positions = portfolio.get('positions', [])

    # Group by ticker
    ticker_groups = {}
    for pos in old_positions:
        ticker = pos.get('ticker', '')
        if ticker not in ticker_groups:
            ticker_groups[ticker] = []
        lot = {
            'quantity': pos.get('quantity', 0),
            'purchase_price': pos.get('purchase_price', 0),
            'purchase_date': pos.get('purchase_date', ''),
        }
        if pos.get('notes'):
            lot['notes'] = pos['notes']
        ticker_groups[ticker].append(lot)

    # Build new positions
    new_positions = []
    for ticker, lots in ticker_groups.items():
        # Sort lots by purchase_date (FIFO)
        lots.sort(key=lambda l: l.get('purchase_date', ''))
        new_positions.append({
            'ticker': ticker,
            'lots': lots,
        })

    return {
        'positions': new_positions,
        'cash_available': portfolio.get('cash_available', 0),
        'last_updated': portfolio.get('last_updated', date.today().isoformat()),
    }


# =============================================================================
# Financial Calculations
# =============================================================================

def calculate_position_value(quantity: float, current_price: float) -> float:
    """Calculate current value of a position."""
    return quantity * current_price


def calculate_pnl(quantity: float, purchase_price: float, current_price: float) -> float:
    """Calculate profit/loss for a position."""
    cost_basis = quantity * purchase_price
    current_value = quantity * current_price
    return current_value - cost_basis


def calculate_pnl_percent(purchase_price: float, current_price: float) -> float:
    """Calculate profit/loss percentage."""
    if purchase_price == 0:
        return 0.0
    return ((current_price - purchase_price) / purchase_price) * 100


def calculate_swap_cost(
    sell_quantity: float,
    sell_price: float,
    buy_price: float,
    transaction_fee: float = 10.0
) -> dict:
    """
    Calculate costs for swapping one position to another.

    Args:
        sell_quantity: Number of shares to sell
        sell_price: Current price of stock to sell
        buy_price: Current price of stock to buy
        transaction_fee: Fee per transaction

    Returns:
        Dictionary with swap details
    """
    proceeds = sell_quantity * sell_price
    total_fees = transaction_fee * 2  # Buy and sell
    available_for_buy = proceeds - total_fees
    new_quantity = available_for_buy / buy_price if buy_price > 0 else 0

    return {
        'proceeds': proceeds,
        'fees': total_fees,
        'available_for_buy': available_for_buy,
        'new_quantity': int(new_quantity),  # Whole shares only
        'leftover_cash': available_for_buy - (int(new_quantity) * buy_price)
    }


# =============================================================================
# Formatting Helpers
# =============================================================================

def format_currency(amount: float) -> str:
    """Format number as currency string."""
    return f"${amount:,.2f}"


def format_percent(value: float) -> str:
    """Format number as percentage string."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def format_date(d: date | str) -> str:
    """Format date for display."""
    if isinstance(d, str):
        d = parse_date(d)
    return d.strftime("%Y-%m-%d")
