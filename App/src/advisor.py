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
from .recommendations_manager import (
    record_recommendation, match_trade_to_recommendations,
    list_recommendations, get_recommendation_by_id,
    simulate_recommendation, fetch_current_prices_for_simulation,
    get_tickers_from_recommendation, get_ledger_summary
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
    manual = getattr(args, 'manual', False)
    if manual:
        print(colorize("Manual mode: building prompt for manual LLM input...", Colors.DIM))
    else:
        print(colorize("Getting AI recommendation...", Colors.DIM))
    recommendation = get_recommendation(context, strategy, narratives, market_data, manual_mode=manual)

    # Process narrative updates from AI response
    narrative_updates = recommendation.get('narrative_updates', {})
    if narrative_updates:
        narratives = update_narratives(narratives, narrative_updates)
        narratives = prune_old_narratives(narratives)
        if save_narratives(narratives):
            print(colorize("  Narrative context updated", Colors.DIM))

    # Display full dashboard
    display_full_dashboard(portfolio, context, recommendation)

    # Record recommendation to ledger (CR007)
    try:
        rec_id = record_recommendation(portfolio, context, recommendation, market_data)
        print(colorize(f"  Recommendation recorded: {rec_id}", Colors.DIM))
    except Exception as e:
        print(colorize(f"  Warning: Failed to record recommendation: {e}", Colors.YELLOW))

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

    # Only fetch for held positions + top stocks (lot-based: ticker is at position level)
    held_tickers = [p.get('ticker', '') for p in portfolio.get('positions', [])]
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
    print("  add cash 500          - Add to cash balance")
    print("  set cash 666          - Set cash to exact amount (use for currency conversion)")
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
            return f"Added ${amount:,.2f} to cash. New balance: ${portfolio['cash_available']:,.2f}"
        except (IndexError, ValueError):
            return ""

    # Handle "set cash" command — direct override (e.g. for currency conversion)
    if action == 'set' and len(words) >= 3 and words[1] == 'cash':
        try:
            amount = float(words[2].replace('$', '').replace(',', ''))
            old = portfolio.get('cash_available', 0)
            portfolio['cash_available'] = amount
            return f"Cash set to ${amount:,.2f} (was ${old:,.2f})"
        except (IndexError, ValueError):
            return ""

    # Handle sold command (lot-aware FIFO)
    if action == 'sold':
        # Format: sold TICKER QTY shares at PRICE [on DATE]
        try:
            ticker = words[1].upper()
            qty = float(words[2])
            at_idx = words.index('at')
            price = float(words[at_idx + 1].replace('$', '').replace(',', ''))

            # Find position by ticker
            positions = portfolio.get('positions', [])
            position = None
            pos_idx = None
            for i, pos in enumerate(positions):
                if pos.get('ticker') == ticker:
                    position = pos
                    pos_idx = i
                    break

            if position is None:
                return f"No position found for {ticker}"

            # FIFO: remove quantity from oldest lots first
            remaining_to_sell = qty
            lots = position.get('lots', [])
            lots_removed = 0

            for lot in lots[:]:  # iterate over copy
                if remaining_to_sell <= 0:
                    break
                lot_qty = lot.get('quantity', 0)
                if lot_qty <= remaining_to_sell:
                    # Consume entire lot
                    remaining_to_sell -= lot_qty
                    lots.remove(lot)
                    lots_removed += 1
                else:
                    # Partial lot consumption
                    lot['quantity'] = lot_qty - remaining_to_sell
                    remaining_to_sell = 0

            # If no lots left, remove the position entirely
            if not lots:
                positions.pop(pos_idx)

            # Add proceeds to cash
            proceeds = qty * price
            portfolio['cash_available'] = portfolio.get('cash_available', 0) + proceeds

            message = f"Recorded: SOLD {ticker} {qty} shares @ ${price:.2f} (proceeds: ${proceeds:,.2f}, {lots_removed} lot(s) consumed)"

            # Try to match trade to pending recommendation (CR007)
            try:
                matched_id = match_trade_to_recommendations('sold', ticker, qty, price, date.today().isoformat())
                if matched_id:
                    message += f"\n    [Matched to recommendation {matched_id}]"
            except Exception:
                pass  # Silent failure - matching is optional

            return message
        except (ValueError, IndexError):
            return ""

    # Handle bought command (lot-aware)
    if action == 'bought':
        # Format: bought TICKER QTY shares at PRICE [on DATE]
        try:
            ticker = words[1].upper()
            qty = float(words[2])
            at_idx = words.index('at')
            price = float(words[at_idx + 1].replace('$', '').replace(',', ''))

            # Check for date
            purchase_date = date.today().isoformat()
            if 'on' in words:
                on_idx = words.index('on')
                if on_idx + 1 < len(words):
                    purchase_date = words[on_idx + 1]

            # Confirm before writing
            cost = qty * price
            cash_after = portfolio.get('cash_available', 0) - cost
            print(f"\n  About to record: BUY {ticker} {qty} share(s) @ ${price:.2f}/share")
            print(f"  Total cost: ${cost:,.2f}  |  Cash after: ${cash_after:,.2f}")
            try:
                confirm_input = input("  Confirm? (y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return "Cancelled."
            if confirm_input != 'y':
                return "Cancelled."

            # New lot
            new_lot = {
                'quantity': qty,
                'purchase_price': price,
                'purchase_date': purchase_date,
            }

            # Find existing position for this ticker, or create new one
            if 'positions' not in portfolio:
                portfolio['positions'] = []

            existing_position = None
            for pos in portfolio['positions']:
                if pos.get('ticker') == ticker:
                    existing_position = pos
                    break

            if existing_position:
                # Add lot to existing position
                existing_position['lots'].append(new_lot)
            else:
                # Create new position with this lot
                portfolio['positions'].append({
                    'ticker': ticker,
                    'lots': [new_lot],
                })

            # Deduct cost from cash
            portfolio['cash_available'] = portfolio.get('cash_available', 0) - cost

            # Calculate unlock date
            from .utils import unlock_date
            unlock = unlock_date(purchase_date)

            message = f"Recorded: BOUGHT {ticker} {qty} shares @ ${price:.2f} (locked until {unlock})"

            # Try to match trade to pending recommendation (CR007)
            try:
                matched_id = match_trade_to_recommendations('bought', ticker, qty, price, purchase_date)
                if matched_id:
                    message += f"\n    [Matched to recommendation {matched_id}]"
            except Exception:
                pass  # Silent failure - matching is optional

            return message
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


def cmd_migrate(args):
    """
    Migrate portfolio from legacy flat format to lot-based format.
    """
    from .utils import (
        get_portfolio_file, load_json, save_json,
        is_lot_based_format, migrate_portfolio_to_lots, validate_portfolio
    )
    import shutil

    print_header("MIGRATE PORTFOLIO TO LOT-BASED FORMAT")

    portfolio_path = get_portfolio_file()
    if not portfolio_path.exists():
        print(colorize("\nError: Portfolio file not found.", Colors.RED))
        return 1

    portfolio = load_json(portfolio_path)

    # Check if already migrated
    if is_lot_based_format(portfolio):
        print(colorize("\n  Portfolio is already in lot-based format. No migration needed.", Colors.GREEN))
        return 0

    # Show current state
    positions = portfolio.get('positions', [])
    unique_tickers = set(p.get('ticker', '') for p in positions)
    print(f"\n  Current format: {len(positions)} entries, {len(unique_tickers)} unique stocks")
    for p in positions:
        print(f"    {p.get('ticker', '')} - {p.get('quantity', 0)} shares @ ${p.get('purchase_price', 0):.2f} ({p.get('purchase_date', '')})")

    # Migrate
    backup_path = portfolio_path.with_suffix('.json.backup')
    shutil.copy2(portfolio_path, backup_path)
    print(colorize(f"\n  Backup created: {backup_path.name}", Colors.DIM))

    migrated = migrate_portfolio_to_lots(portfolio)

    # Validate
    try:
        validate_portfolio(migrated)
    except ValueError as e:
        print(colorize(f"\n  Migration validation failed: {e}", Colors.RED))
        print(colorize("  Restoring backup...", Colors.YELLOW))
        shutil.copy2(backup_path, portfolio_path)
        return 1

    # Save
    save_json(portfolio_path, migrated)

    # Show result
    new_positions = migrated.get('positions', [])
    print(colorize(f"\n  Migration successful!", Colors.GREEN))
    print(f"  New format: {len(new_positions)} stocks")
    for pos in new_positions:
        ticker = pos.get('ticker', '')
        lots = pos.get('lots', [])
        total_qty = sum(l.get('quantity', 0) for l in lots)
        print(f"    {ticker} - {total_qty} shares ({len(lots)} lot{'s' if len(lots) > 1 else ''})")
        for i, lot in enumerate(lots):
            print(f"      Lot {i+1}: {lot.get('quantity', 0)} @ ${lot.get('purchase_price', 0):.2f} ({lot.get('purchase_date', '')})")

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
  python -m src.advisor migrate      Migrate portfolio to lot-based format
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
# Simulation Commands (CR007)
# =============================================================================

def cmd_sim(args):
    """
    Simulation command - analyze past recommendation performance.

    Usage:
        python -m src.advisor sim              # Simulate most recent
        python -m src.advisor sim <ID>         # Simulate specific recommendation
        python -m src.advisor sim --list       # List all recommendations
        python -m src.advisor sim --summary    # Show outcome statistics
    """
    # Handle --list flag
    if hasattr(args, 'sim_list') and args.sim_list:
        return _display_recommendation_list()

    # Handle --summary flag
    if hasattr(args, 'sim_summary') and args.sim_summary:
        return _display_ledger_summary()

    # Get specific ID or most recent
    rec_id = getattr(args, 'sim_id', None)

    recs = list_recommendations(limit=1)
    if not recs and not rec_id:
        print(colorize("\nNo recommendations recorded yet.", Colors.YELLOW))
        print("Run a full analysis first: python -m src.advisor")
        return 0

    if rec_id:
        rec = get_recommendation_by_id(rec_id)
        if not rec:
            print(colorize(f"\nRecommendation {rec_id} not found.", Colors.RED))
            print("\nUse 'python -m src.advisor sim --list' to see available IDs.")
            return 1
    else:
        # Get most recent
        rec = recs[0]
        rec_id = rec['id']

    # Fetch current prices
    tickers = get_tickers_from_recommendation(rec)
    print(colorize(f"\nFetching current prices for: {', '.join(tickers)}...", Colors.DIM))
    current_prices = fetch_current_prices_for_simulation(tickers)

    if not current_prices:
        print(colorize("Warning: Could not fetch current prices.", Colors.YELLOW))
        return 1

    # Run simulation
    print(colorize("Running simulation...", Colors.DIM))
    simulation = simulate_recommendation(rec_id, current_prices)

    # Display results
    _display_simulation_results(rec, simulation)

    return 0


def _display_recommendation_list():
    """Display list of all recorded recommendations."""
    print_header("RECOMMENDATION HISTORY")

    recs = list_recommendations(limit=50)

    if not recs:
        print("\n  No recommendations recorded yet.")
        print("  Run a full analysis first: python -m src.advisor")
        return 0

    print()
    header = f"{'ID':<26}{'Date':<12}{'Actions':<28}{'Outcome':<12}{'Verdict':<10}"
    print(colorize(header, Colors.BOLD))
    print("-" * 88)

    for rec in recs:
        rec_id = rec.get('id', 'unknown')
        rec_date = rec.get('timestamp', '')[:10]
        actions = _summarize_actions(rec.get('recommendation', {}).get('actions', []))
        outcome = rec.get('outcome', 'pending')
        verdict = rec.get('simulation', {}).get('verdict', '-') if rec.get('simulation') else '-'

        # Color by outcome
        if outcome == 'accepted':
            outcome_str = colorize(outcome, Colors.GREEN)
        elif outcome == 'partial':
            outcome_str = colorize(outcome, Colors.YELLOW)
        elif outcome == 'skipped':
            outcome_str = colorize(outcome, Colors.RED)
        else:
            outcome_str = colorize(outcome, Colors.DIM)

        # Color by verdict
        if verdict == 'GOOD':
            verdict_str = colorize(verdict, Colors.GREEN)
        elif verdict == 'BAD':
            verdict_str = colorize(verdict, Colors.RED)
        else:
            verdict_str = verdict

        print(f"{rec_id:<26}{rec_date:<12}{actions:<28}{outcome_str:<20}{verdict_str:<10}")

    print()
    summary = get_ledger_summary()
    print(f"Total: {summary['total_recommendations']} | "
          f"Accepted: {summary['total_accepted']} | "
          f"Partial: {summary['total_partial']} | "
          f"Skipped: {summary['total_skipped']} | "
          f"Pending: {summary['total_pending']}")

    return 0


def _summarize_actions(actions):
    """Create brief summary of actions for list display."""
    if not actions:
        return "HOLD ALL"

    parts = []
    for action in actions[:2]:  # Max 2 actions in summary
        action_type = action.get('type', '?')
        ticker = action.get('ticker', '?')
        parts.append(f"{action_type} {ticker}")

    summary = ", ".join(parts)
    if len(actions) > 2:
        summary += f" +{len(actions) - 2}"

    return summary[:26]  # Truncate if needed


def _display_ledger_summary():
    """Display aggregate statistics from the ledger."""
    print_header("RECOMMENDATION LEDGER SUMMARY")

    summary = get_ledger_summary()

    print()
    print(f"  Total Recommendations:  {summary['total_recommendations']}")
    print()
    print(colorize("  Outcomes:", Colors.BOLD))
    print(f"    Accepted (followed):  {colorize(str(summary['total_accepted']), Colors.GREEN)}")
    print(f"    Partial (some):       {colorize(str(summary['total_partial']), Colors.YELLOW)}")
    print(f"    Skipped (ignored):    {colorize(str(summary['total_skipped']), Colors.RED)}")
    print(f"    Pending (awaiting):   {colorize(str(summary['total_pending']), Colors.DIM)}")

    print()
    print(colorize("  Verdicts (simulated):", Colors.BOLD))
    verdicts = summary.get('verdicts', {})
    print(f"    GOOD (advice helped): {colorize(str(verdicts.get('GOOD', 0)), Colors.GREEN)}")
    print(f"    BAD (should ignore):  {colorize(str(verdicts.get('BAD', 0)), Colors.RED)}")
    print(f"    NEUTRAL (no diff):    {verdicts.get('NEUTRAL', 0)}")

    date_range = summary.get('date_range', {})
    if date_range.get('oldest'):
        print()
        print(f"  Date Range: {date_range['oldest']} to {date_range['newest']}")

    return 0


def _display_simulation_results(rec: dict, simulation: dict):
    """Display detailed simulation results for a recommendation."""
    print_header(f"SIMULATION: {rec.get('id', 'unknown')}")

    # Check for errors
    if simulation.get('error'):
        print(colorize(f"\n  Error: {simulation['error']}", Colors.RED))
        return

    # Recommendation summary
    print()
    print(colorize("Original Recommendation", Colors.BOLD))
    print(f"  Date: {rec.get('timestamp', '')[:19]}")
    print(f"  Confidence: {rec.get('recommendation', {}).get('confidence', 'N/A')}")
    print()

    actions = rec.get('recommendation', {}).get('actions', [])
    for i, action in enumerate(actions):
        action_type = action.get('type', '?')
        ticker = action.get('ticker', '?')
        amount = action.get('amount', '')

        # Get price at time of recommendation
        market_snapshot = rec.get('market_snapshot', {})
        rankings = market_snapshot.get('rankings', {})
        expected_price = rankings.get(ticker, {}).get('price', 0)

        if action_type == 'BUY':
            type_color = Colors.GREEN
        elif action_type == 'SELL':
            type_color = Colors.RED
        else:
            type_color = Colors.YELLOW

        print(f"  {i+1}. {colorize(action_type, type_color + Colors.BOLD)} {ticker} {amount}", end='')
        if expected_price:
            print(f" @ ${expected_price:.2f}")
        else:
            print()

    # Price movement
    print()
    print(colorize("Price Movement", Colors.BOLD))
    prices_then = simulation.get('prices_then', {})
    prices_now = simulation.get('prices_now', {})

    for ticker in sorted(prices_then.keys()):
        then = prices_then.get(ticker, 0)
        now = prices_now.get(ticker, then)
        if then > 0:
            change = ((now - then) / then) * 100
            change_str = f"{change:+.1f}%"
            if change > 0:
                change_color = Colors.GREEN
            elif change < 0:
                change_color = Colors.RED
            else:
                change_color = Colors.DIM
            print(f"  {ticker}: ${then:.2f} -> ${now:.2f} ({colorize(change_str, change_color)})")

    # Hypothetical P&L
    print()
    print(colorize("Hypothetical P&L Analysis", Colors.BOLD))
    hypo = simulation.get('hypothetical_pnl', {})

    if_followed = hypo.get('if_followed', 0)
    if_ignored = hypo.get('if_ignored', 0)

    followed_color = Colors.GREEN if if_followed > 0 else Colors.RED if if_followed < 0 else Colors.DIM
    ignored_color = Colors.GREEN if if_ignored > 0 else Colors.RED if if_ignored < 0 else Colors.DIM

    print(f"  If you followed advice:  {colorize(f'${if_followed:+,.2f}', followed_color)}")
    print(f"  If you ignored advice:   {colorize(f'${if_ignored:+,.2f}', ignored_color)}")

    # Verdict
    print()
    print(colorize("Verdict", Colors.BOLD))
    verdict = simulation.get('verdict', 'NEUTRAL')
    days = simulation.get('days_elapsed', 0)
    diff = if_followed - if_ignored

    if verdict == 'GOOD':
        print(colorize(f"  {verdict}: The advice would have helped! (+${diff:.2f} vs ignoring)", Colors.GREEN + Colors.BOLD))
    elif verdict == 'BAD':
        print(colorize(f"  {verdict}: Better to have ignored this one. (${diff:.2f} vs ignoring)", Colors.RED + Colors.BOLD))
    else:
        print(colorize(f"  {verdict}: Advice made little difference either way.", Colors.YELLOW))

    print(f"\n  Analysis period: {days} days since recommendation")
    print()


def cmd_review(args):
    """
    Review command - AI-assisted pattern analysis (Phase 3 - Future).

    Requires: Minimum 20 completed recommendations with verdicts.
    """
    summary = get_ledger_summary()
    total_completed = summary['total_accepted'] + summary['total_partial'] + summary['total_skipped']

    if total_completed < 20:
        print(colorize("\nNot enough data for pattern analysis.", Colors.YELLOW))
        print(f"  Completed recommendations: {total_completed}")
        print(f"  Required minimum: 20")
        print("\nContinue using the advisor and running simulations to build history.")
        return 0

    print(colorize("\n[Phase 3] Learning loop not yet implemented.", Colors.DIM))
    print("\nFuture capabilities:")
    print("  - Pattern detection in GOOD vs BAD verdicts")
    print("  - Strategy refinement suggestions")
    print("  - Scorecard by decision type")
    print("\nThis feature will be available once the recommendation ledger has")
    print("accumulated enough data to identify meaningful patterns.")

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
  sim       Simulate past recommendations (--list, --summary, or <ID>)
  review    AI-assisted strategy review (requires 20+ recommendations)
  init      Initialize portfolio (first-time setup)

Examples:
  python -m src.advisor              # Full analysis
  python -m src.advisor --manual     # Save prompt to file, read response from stdin
  python -m src.advisor check        # Quick status
  python -m src.advisor confirm      # Record trades
  python -m src.advisor sim --list   # List past recommendations
  python -m src.advisor sim          # Simulate most recent
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='run',
        choices=['run', 'check', 'confirm', 'migrate', 'init', 'sim', 'review', 'help'],
        help='Command to execute (default: run)'
    )

    # Simulation command arguments
    parser.add_argument(
        'sim_id',
        nargs='?',
        default=None,
        help='Recommendation ID to simulate (for sim command)'
    )
    parser.add_argument(
        '--list',
        dest='sim_list',
        action='store_true',
        help='List all recorded recommendations'
    )
    parser.add_argument(
        '--summary',
        dest='sim_summary',
        action='store_true',
        help='Show ledger summary statistics'
    )
    parser.add_argument(
        '--manual',
        action='store_true',
        help='Skip API call: save prompt to file and read LLM response from stdin'
    )

    args = parser.parse_args()

    # Route to appropriate command
    commands = {
        'run': cmd_run,
        'check': cmd_check,
        'confirm': cmd_confirm,
        'migrate': cmd_migrate,
        'init': cmd_init,
        'sim': cmd_sim,
        'review': cmd_review,
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
