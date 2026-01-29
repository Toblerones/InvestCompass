"""
advisor.py - Main Entry Point & CLI

Main orchestrator for the Portfolio AI Agent.
Handles command-line interface and coordinates all components.

Commands:
    python advisor.py           # Full analysis and recommendations
    python advisor.py check     # Quick portfolio status
    python advisor.py confirm   # Confirm executed trades
    python advisor.py init      # Initialize portfolio (first-time)
"""

import sys
import argparse
from datetime import date

from .utils import (
    load_config, load_portfolio, save_portfolio, load_strategy,
    parse_date, validate_portfolio
)
from .data_collector import fetch_all_market_data
from .analyzer import generate_market_context
from .ai_agent import get_recommendation
from .display import (
    display_full_dashboard, display_quick_check,
    print_header, print_subheader, colorize, Colors
)
from .narrative_manager import (
    load_narratives, save_narratives, update_narratives,
    prune_old_narratives, get_narrative_summary
)


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_run(args):
    """
    Run full analysis and get AI recommendations.
    This is the main command (default when no command specified).
    """
    print(colorize("\nLoading configuration...", Colors.DIM))

    try:
        config = load_config()
        portfolio = load_portfolio()
        strategy = load_strategy()
    except FileNotFoundError as e:
        print(colorize(f"\nError: {e}", Colors.RED))
        print("Run 'python -m src.advisor init' to initialize.")
        return 1
    except ValueError as e:
        print(colorize(f"\nValidation Error: {e}", Colors.RED))
        return 1

    # Load narratives for context memory
    narratives = load_narratives()
    narrative_summary = get_narrative_summary(narratives)
    if narrative_summary['total_active'] > 0:
        print(colorize(
            f"  Loaded {narrative_summary['total_active']} active narratives "
            f"across {narrative_summary['stocks_tracked']} stocks",
            Colors.DIM
        ))

    # Fetch market data
    print(colorize("Fetching market data (this may take a moment)...", Colors.DIM))
    tickers = config.get('watchlist', [])

    try:
        market_data = fetch_all_market_data(tickers, include_news=True)
    except Exception as e:
        print(colorize(f"\nError fetching market data: {e}", Colors.RED))
        return 1

    # Generate market context
    print(colorize("Analyzing market conditions...", Colors.DIM))
    context = generate_market_context(market_data, portfolio, config)

    # Log material events if detected
    material_events = context.get('material_events', [])
    if material_events:
        event_count = len(material_events)
        tickers = ', '.join(e['ticker'] for e in material_events)
        print(colorize(
            f"  Detected {event_count} material event(s) for: {tickers}",
            Colors.YELLOW
        ))

    # Get AI recommendation (with narrative context + market data for event analysis)
    print(colorize("Getting AI recommendation...", Colors.DIM))
    recommendation = get_recommendation(context, strategy, narratives, market_data)

    # Process narrative updates from AI response
    narrative_updates = recommendation.get('narrative_updates', {})
    if narrative_updates:
        narratives = update_narratives(narratives, narrative_updates)
        narratives = prune_old_narratives(narratives)
        if save_narratives(narratives):
            print(colorize("  Narrative context updated", Colors.DIM))

    # Display full dashboard
    display_full_dashboard(portfolio, context, recommendation)

    return 0


def cmd_check(args):
    """
    Quick portfolio status check.
    Shows current positions, P&L, and any critical signals.
    """
    try:
        config = load_config()
        portfolio = load_portfolio()
    except FileNotFoundError as e:
        print(colorize(f"\nError: {e}", Colors.RED))
        return 1
    except ValueError as e:
        print(colorize(f"\nValidation Error: {e}", Colors.RED))
        return 1

    # Fetch market data (faster, no news)
    print(colorize("\nFetching current prices...", Colors.DIM))
    tickers = config.get('watchlist', [])

    # Only fetch for held positions + top stocks
    held_tickers = [p.get('ticker') for p in portfolio.get('positions', [])]
    fetch_tickers = list(set(held_tickers + tickers[:5]))

    try:
        market_data = fetch_all_market_data(fetch_tickers, include_news=False)
    except Exception as e:
        print(colorize(f"\nError fetching market data: {e}", Colors.RED))
        return 1

    # Generate context
    context = generate_market_context(market_data, portfolio, config)

    # Display quick check
    display_quick_check(portfolio, context)

    return 0


def cmd_confirm(args):
    """
    Confirm executed trades and update portfolio.
    Interactive workflow to record buy/sell transactions.
    """
    try:
        portfolio = load_portfolio()
    except FileNotFoundError as e:
        print(colorize(f"\nError: {e}", Colors.RED))
        return 1

    print_header("CONFIRM TRADES")
    print("\nEnter your executed trades. Type 'done' when finished.\n")
    print("Format examples:")
    print("  sold GOOGL 28 shares at 175.50")
    print("  bought NVDA 10 shares at 450.00")
    print("  add cash 500")
    print()

    changes_made = False

    while True:
        try:
            user_input = input(colorize("> ", Colors.CYAN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input in ('done', 'exit', 'quit', ''):
            break

        result = process_trade_input(user_input, portfolio)
        if result:
            changes_made = True
            print(colorize(f"[+] {result}", Colors.GREEN))
        else:
            print(colorize("Could not parse input. Try again.", Colors.YELLOW))

    if changes_made:
        try:
            save_portfolio(portfolio)
            print(colorize("\n[+] Portfolio updated successfully.", Colors.GREEN))
        except Exception as e:
            print(colorize(f"\nError saving portfolio: {e}", Colors.RED))
            return 1
    else:
        print(colorize("\nNo changes made.", Colors.DIM))

    return 0


def process_trade_input(user_input: str, portfolio: dict) -> str:
    """
    Process a single trade input and update portfolio.

    Args:
        user_input: User's trade description
        portfolio: Portfolio dictionary (modified in place)

    Returns:
        Success message or empty string if failed
    """
    words = user_input.split()
    if len(words) < 2:
        return ""

    action = words[0]

    # Handle "add cash" command
    if action == 'add' and words[1] == 'cash':
        try:
            amount = float(words[2].replace('$', '').replace(',', ''))
            portfolio['cash_available'] = portfolio.get('cash_available', 0) + amount
            return f"Added ${amount:,.2f} to cash"
        except (IndexError, ValueError):
            return ""

    # Handle sold command
    if action == 'sold':
        # Format: sold TICKER QTY shares at PRICE [on DATE]
        try:
            ticker = words[1].upper()
            qty = int(words[2])
            # Find "at" to get price
            at_idx = words.index('at')
            price = float(words[at_idx + 1].replace('$', '').replace(',', ''))

            # Remove position
            positions = portfolio.get('positions', [])
            for i, pos in enumerate(positions):
                if pos.get('ticker') == ticker:
                    positions.pop(i)
                    break

            # Add proceeds to cash
            proceeds = qty * price
            portfolio['cash_available'] = portfolio.get('cash_available', 0) + proceeds

            return f"Recorded: SOLD {ticker} {qty} shares @ ${price:.2f} (proceeds: ${proceeds:,.2f})"
        except (ValueError, IndexError):
            return ""

    # Handle bought command
    if action == 'bought':
        # Format: bought TICKER QTY shares at PRICE [on DATE]
        try:
            ticker = words[1].upper()
            qty = int(words[2])
            at_idx = words.index('at')
            price = float(words[at_idx + 1].replace('$', '').replace(',', ''))

            # Check for date
            purchase_date = date.today().isoformat()
            if 'on' in words:
                on_idx = words.index('on')
                if on_idx + 1 < len(words):
                    purchase_date = words[on_idx + 1]

            # Add position
            new_position = {
                'ticker': ticker,
                'quantity': qty,
                'purchase_price': price,
                'purchase_date': purchase_date,
            }

            if 'positions' not in portfolio:
                portfolio['positions'] = []
            portfolio['positions'].append(new_position)

            # Deduct cost from cash
            cost = qty * price
            portfolio['cash_available'] = portfolio.get('cash_available', 0) - cost

            # Calculate unlock date
            from .utils import unlock_date
            unlock = unlock_date(purchase_date)

            return f"Recorded: BOUGHT {ticker} {qty} shares @ ${price:.2f} (locked until {unlock})"
        except (ValueError, IndexError):
            return ""

    return ""


def cmd_init(args):
    """
    Initialize portfolio for first-time setup.
    Creates or resets portfolio.json with empty positions.
    """
    from .utils import get_portfolio_file, save_json

    print_header("INITIALIZE PORTFOLIO")

    portfolio_path = get_portfolio_file()

    # Check if portfolio exists
    if portfolio_path.exists():
        print(f"\nPortfolio file already exists at: {portfolio_path}")
        try:
            confirm = input("Reset to empty portfolio? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if confirm != 'y':
            print("Initialization cancelled.")
            return 0

    # Create empty portfolio
    portfolio = {
        'positions': [],
        'cash_available': 0.0,
        'last_updated': date.today().isoformat()
    }

    # Ask for initial cash
    try:
        cash_input = input("\nEnter starting cash amount (or press Enter for $0): ").strip()
        if cash_input:
            portfolio['cash_available'] = float(cash_input.replace('$', '').replace(',', ''))
    except (ValueError, EOFError, KeyboardInterrupt):
        pass

    # Save portfolio
    try:
        save_json(portfolio_path, portfolio)
        print(colorize(f"\n[+] Portfolio initialized at: {portfolio_path}", Colors.GREEN))
        print(f"  Cash: ${portfolio['cash_available']:,.2f}")
        print("\nNext steps:")
        print("  1. Add positions using 'python -m src.advisor confirm'")
        print("  2. Or run 'python -m src.advisor' for recommendations")
    except Exception as e:
        print(colorize(f"\nError saving portfolio: {e}", Colors.RED))
        return 1

    return 0


def cmd_help(args):
    """Display help information."""
    print("""
Portfolio AI Agent - Help
==========================

COMMANDS:

  python -m src.advisor              Run full analysis and get AI recommendations
  python -m src.advisor check        Quick portfolio status check
  python -m src.advisor confirm      Record executed trades
  python -m src.advisor init         Initialize portfolio (first-time setup)
  python -m src.advisor --help       Show this help message

QUICK START:

  1. Set up your Anthropic API key:
     cp .env.example .env
     # Edit .env and add your ANTHROPIC_API_KEY

  2. Initialize your portfolio:
     python -m src.advisor init

  3. Add your existing positions:
     python -m src.advisor confirm
     > bought GOOGL 28 shares at 155.00 on 2025-12-01
     > done

  4. Run the advisor:
     python -m src.advisor

CONFIGURATION:

  config/config.json    - Watchlist, budget, and settings
  config/portfolio.json - Your current positions
  config/strategy.txt   - Investment strategy for AI

For more information, see README.md
""")
    return 0


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the advisor CLI."""
    parser = argparse.ArgumentParser(
        description='Portfolio AI Agent - AI-powered stock portfolio advisor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  (none)    Run full analysis and get AI recommendations
  check     Quick portfolio status check
  confirm   Record executed trades
  init      Initialize portfolio (first-time setup)

Examples:
  python -m src.advisor           # Full analysis
  python -m src.advisor check     # Quick status
  python -m src.advisor confirm   # Record trades
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='run',
        choices=['run', 'check', 'confirm', 'init', 'help'],
        help='Command to execute (default: run)'
    )

    args = parser.parse_args()

    # Route to appropriate command
    commands = {
        'run': cmd_run,
        'check': cmd_check,
        'confirm': cmd_confirm,
        'init': cmd_init,
        'help': cmd_help,
    }

    cmd_func = commands.get(args.command, cmd_run)

    try:
        exit_code = cmd_func(args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(colorize("\n\nOperation cancelled.", Colors.YELLOW))
        sys.exit(130)
    except Exception as e:
        print(colorize(f"\nUnexpected error: {e}", Colors.RED))
        sys.exit(1)


if __name__ == "__main__":
    main()
