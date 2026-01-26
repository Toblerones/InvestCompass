"""
narrative_manager.py - Narrative Storage Management

Responsibilities:
- Load/save narrative data from/to narratives.json
- Update narratives based on AI suggestions
- Prune old resolved narratives
- Format narratives for AI prompt context

Key Functions:
- load_narratives() -> dict
- save_narratives(narratives: dict)
- update_narratives(current: dict, ai_updates: dict) -> dict
- prune_old_narratives(narratives: dict, days: int) -> dict
- format_narratives_for_prompt(narratives: dict, tickers: list) -> str
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

# =============================================================================
# Configuration
# =============================================================================

# Path to narratives file (relative to config directory)
NARRATIVES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'config',
    'narratives.json'
)

# Limits
MAX_ACTIVE_NARRATIVES_PER_STOCK = 5
PRUNE_RESOLVED_AFTER_DAYS = 30


# =============================================================================
# Schema
# =============================================================================

def get_empty_narratives() -> dict:
    """
    Return an empty narratives structure.

    Schema:
    {
        "version": "1.0",
        "last_updated": "2026-01-26T10:30:00Z",
        "stocks": {
            "TICKER": {
                "active_narratives": [
                    {
                        "theme": "regulatory_risk",
                        "first_seen": "2025-12-15",
                        "last_updated": "2026-01-20",
                        "summary": "DOJ antitrust investigation ongoing",
                        "impact": "negative",
                        "article_count": 12
                    }
                ],
                "resolved_narratives": [
                    {
                        "theme": "earnings_concern",
                        "resolved_date": "2026-01-18",
                        "resolution": "Q4 earnings beat, concerns addressed"
                    }
                ]
            }
        }
    }
    """
    return {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "stocks": {}
    }


def get_empty_stock_narratives() -> dict:
    """Return empty narrative structure for a single stock."""
    return {
        "active_narratives": [],
        "resolved_narratives": []
    }


# =============================================================================
# Load / Save
# =============================================================================

def load_narratives() -> dict:
    """
    Load narratives from JSON file, or create empty structure if not exists.

    Returns:
        Narratives dictionary
    """
    if not os.path.exists(NARRATIVES_FILE):
        return get_empty_narratives()

    try:
        with open(NARRATIVES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate structure
        if 'stocks' not in data:
            data['stocks'] = {}
        if 'version' not in data:
            data['version'] = '1.0'

        return data

    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load narratives.json: {e}")
        print("Starting with empty narratives.")
        return get_empty_narratives()


def save_narratives(narratives: dict) -> bool:
    """
    Save narratives to JSON file.

    Args:
        narratives: Narratives dictionary to save

    Returns:
        True if successful, False otherwise
    """
    try:
        # Update timestamp
        narratives['last_updated'] = datetime.now().isoformat()

        # Ensure config directory exists
        os.makedirs(os.path.dirname(NARRATIVES_FILE), exist_ok=True)

        with open(NARRATIVES_FILE, 'w', encoding='utf-8') as f:
            json.dump(narratives, f, indent=2)

        return True

    except (IOError, TypeError) as e:
        print(f"Warning: Failed to save narratives.json: {e}")
        return False


# =============================================================================
# Update Functions
# =============================================================================

def update_narratives(current_narratives: dict, ai_updates: dict) -> dict:
    """
    Apply AI-suggested updates to narrative structure.

    Args:
        current_narratives: Current narratives dictionary
        ai_updates: AI's narrative_updates from response, format:
            {
                "TICKER": {
                    "add": [{"theme": "...", "summary": "...", "impact": "..."}],
                    "update": [{"theme": "...", "summary": "...", "impact": "..."}],
                    "resolve": ["theme_name"]
                }
            }

    Returns:
        Updated narratives dictionary
    """
    if not ai_updates:
        return current_narratives

    today = datetime.now().strftime('%Y-%m-%d')

    for ticker, updates in ai_updates.items():
        # Ensure stock exists in narratives
        if ticker not in current_narratives.get('stocks', {}):
            if 'stocks' not in current_narratives:
                current_narratives['stocks'] = {}
            current_narratives['stocks'][ticker] = get_empty_stock_narratives()

        stock_data = current_narratives['stocks'][ticker]

        # Handle additions (with deduplication)
        for new_narrative in updates.get('add', []):
            theme = new_narrative.get('theme', 'unknown')

            # Check if narrative with same theme already exists
            existing = None
            for active in stock_data['active_narratives']:
                if active['theme'] == theme:
                    existing = active
                    break

            if existing:
                # Update existing narrative instead of adding duplicate
                existing['last_updated'] = today
                if 'summary' in new_narrative:
                    existing['summary'] = new_narrative['summary']
                if 'impact' in new_narrative:
                    existing['impact'] = new_narrative['impact']
                if 'article_count' in new_narrative:
                    existing['article_count'] = new_narrative.get('article_count', 1)
            elif _can_add_narrative(stock_data):
                # Add new narrative
                narrative = {
                    'theme': theme,
                    'first_seen': today,
                    'last_updated': today,
                    'summary': new_narrative.get('summary', ''),
                    'impact': new_narrative.get('impact', 'neutral'),
                    'article_count': new_narrative.get('article_count', 1)
                }
                stock_data['active_narratives'].append(narrative)

        # Handle updates
        for update_narrative in updates.get('update', []):
            theme = update_narrative.get('theme', '')
            for active in stock_data['active_narratives']:
                if active['theme'] == theme:
                    active['last_updated'] = today
                    if 'summary' in update_narrative:
                        active['summary'] = update_narrative['summary']
                    if 'impact' in update_narrative:
                        active['impact'] = update_narrative['impact']
                    if 'article_count' in update_narrative:
                        active['article_count'] = update_narrative['article_count']
                    break

        # Handle resolutions
        for theme_to_resolve in updates.get('resolve', []):
            # Find and move from active to resolved
            for i, active in enumerate(stock_data['active_narratives']):
                if active['theme'] == theme_to_resolve:
                    resolved_narrative = {
                        'theme': active['theme'],
                        'resolved_date': today,
                        'resolution': updates.get('resolution_reason', f'Resolved on {today}')
                    }
                    stock_data['resolved_narratives'].append(resolved_narrative)
                    stock_data['active_narratives'].pop(i)
                    break

    return current_narratives


def _can_add_narrative(stock_data: dict) -> bool:
    """Check if we can add another narrative (respecting limit)."""
    return len(stock_data.get('active_narratives', [])) < MAX_ACTIVE_NARRATIVES_PER_STOCK


def prune_old_narratives(narratives: dict, days: int = PRUNE_RESOLVED_AFTER_DAYS) -> dict:
    """
    Remove resolved narratives older than N days.

    Args:
        narratives: Narratives dictionary
        days: Number of days after which to prune resolved narratives

    Returns:
        Pruned narratives dictionary
    """
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    for ticker, stock_data in narratives.get('stocks', {}).items():
        resolved = stock_data.get('resolved_narratives', [])

        # Keep only narratives resolved after cutoff
        stock_data['resolved_narratives'] = [
            r for r in resolved
            if r.get('resolved_date', '9999-99-99') > cutoff_date
        ]

    return narratives


# =============================================================================
# Formatting for Prompt
# =============================================================================

def format_narratives_for_prompt(narratives: dict, tickers: list) -> str:
    """
    Format narratives into prompt text for AI context.

    Args:
        narratives: Narratives dictionary
        tickers: List of tickers to include (held + top 3)

    Returns:
        Formatted string for prompt
    """
    if not narratives or not narratives.get('stocks'):
        return "No prior narratives tracked."

    lines = []
    has_narratives = False

    for ticker in tickers:
        stock_data = narratives.get('stocks', {}).get(ticker, {})
        active = stock_data.get('active_narratives', [])
        resolved = stock_data.get('resolved_narratives', [])

        if not active and not resolved:
            continue

        has_narratives = True
        lines.append(f"\n{ticker}:")

        # Active narratives
        if active:
            for narrative in active:
                theme = narrative.get('theme', 'unknown').replace('_', ' ').title()
                first_seen = narrative.get('first_seen', '')
                summary = narrative.get('summary', '')
                impact = narrative.get('impact', 'neutral')

                # Calculate how long ongoing
                days_active = _days_since(first_seen)
                duration = f"ongoing {days_active} days" if days_active else "new"

                impact_indicator = {
                    'positive': '+',
                    'negative': '-',
                    'neutral': '~'
                }.get(impact, '~')

                lines.append(f"  [{impact_indicator}] {theme} ({duration}): {summary}")

        # Recently resolved (last 7 days)
        recent_resolved = [r for r in resolved if _days_since(r.get('resolved_date', '')) <= 7]
        if recent_resolved:
            for resolved_narrative in recent_resolved:
                theme = resolved_narrative.get('theme', 'unknown').replace('_', ' ').title()
                resolution = resolved_narrative.get('resolution', 'Resolved')
                lines.append(f"  [RESOLVED] {theme}: {resolution}")

    if not has_narratives:
        return "No prior narratives tracked."

    return "\n".join(lines)


def _days_since(date_str: str) -> int:
    """Calculate days since a date string."""
    if not date_str:
        return 0
    try:
        past = datetime.strptime(date_str, '%Y-%m-%d')
        return (datetime.now() - past).days
    except ValueError:
        return 0


# =============================================================================
# Utility Functions
# =============================================================================

def get_narrative_summary(narratives: dict) -> dict:
    """
    Get a summary of narratives for display.

    Returns:
        Dict with counts: {'total_active': N, 'total_resolved': N, 'stocks_tracked': N}
    """
    total_active = 0
    total_resolved = 0
    stocks_tracked = 0

    for ticker, stock_data in narratives.get('stocks', {}).items():
        active = len(stock_data.get('active_narratives', []))
        resolved = len(stock_data.get('resolved_narratives', []))

        if active or resolved:
            stocks_tracked += 1
            total_active += active
            total_resolved += resolved

    return {
        'total_active': total_active,
        'total_resolved': total_resolved,
        'stocks_tracked': stocks_tracked
    }


def has_narratives(narratives: dict) -> bool:
    """Check if any narratives exist."""
    summary = get_narrative_summary(narratives)
    return summary['total_active'] > 0 or summary['total_resolved'] > 0
