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
    """Load portfolio from portfolio.json."""
    portfolio_path = get_portfolio_file()
    if not portfolio_path.exists():
        raise FileNotFoundError(f"Portfolio file not found: {portfolio_path}")

    portfolio = load_json(portfolio_path)
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

    # Required fields
    required = ['watchlist', 'monthly_budget', 'transaction_fee', 'max_positions']
    for field in required:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    # Validate watchlist
    if 'watchlist' in config:
        if not isinstance(config['watchlist'], list):
            errors.append("watchlist must be a list")
        elif len(config['watchlist']) == 0:
            errors.append("watchlist cannot be empty")
        else:
            for ticker in config['watchlist']:
                if not isinstance(ticker, str) or not ticker.isupper():
                    errors.append(f"Invalid ticker format: {ticker}")

    # Validate numeric fields
    if 'monthly_budget' in config and config['monthly_budget'] <= 0:
        errors.append("monthly_budget must be positive")

    if 'max_positions' in config and config['max_positions'] <= 0:
        errors.append("max_positions must be positive")

    if errors:
        raise ValueError("Config validation failed:\n  - " + "\n  - ".join(errors))


def validate_portfolio(portfolio: dict) -> None:
    """
    Validate portfolio dictionary.

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

    # Validate each position
    if 'positions' in portfolio and isinstance(portfolio['positions'], list):
        for i, pos in enumerate(portfolio['positions']):
            pos_errors = validate_position(pos)
            for err in pos_errors:
                errors.append(f"Position {i+1} ({pos.get('ticker', 'unknown')}): {err}")

    if errors:
        raise ValueError("Portfolio validation failed:\n  - " + "\n  - ".join(errors))


def validate_position(position: dict) -> list[str]:
    """
    Validate a single position.

    Args:
        position: Position dictionary

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Required fields
    required = ['ticker', 'quantity', 'purchase_price', 'purchase_date']
    for field in required:
        if field not in position:
            errors.append(f"Missing field: {field}")

    # Validate ticker
    if 'ticker' in position:
        if not isinstance(position['ticker'], str):
            errors.append("ticker must be a string")
        elif not position['ticker'].isupper():
            errors.append("ticker must be uppercase")

    # Validate quantity
    if 'quantity' in position:
        if not isinstance(position['quantity'], (int, float)):
            errors.append("quantity must be a number")
        elif position['quantity'] <= 0:
            errors.append("quantity must be positive")

    # Validate purchase_price
    if 'purchase_price' in position:
        if not isinstance(position['purchase_price'], (int, float)):
            errors.append("purchase_price must be a number")
        elif position['purchase_price'] <= 0:
            errors.append("purchase_price must be positive")

    # Validate purchase_date
    if 'purchase_date' in position:
        try:
            parse_date(position['purchase_date'])
        except ValueError:
            errors.append("purchase_date must be YYYY-MM-DD format")

    return errors


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
