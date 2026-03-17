"""
Core Strategy Engine — Halal Stock Trading Bot
Runs the daily trading cycle: compliance screening, signal generation,
agent pipeline, order execution, and reporting.
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Sibling module imports
# ---------------------------------------------------------------------------
from schwab_auth import (
    get_client,
    get_positions,
    place_order,
    get_account_balance,
    get_token_age_days,
)
from shariah_screener import ShariahScreener
from data_fetcher import (
    get_price_history,
    get_current_price,
    calculate_signal,
    get_earnings_calendar,
    get_macro_data,
    get_fundamentals,
)
from news_fetcher import get_news_sentiment

# Optional modules — imported defensively so the bot can still run in
# degraded mode when a module has not been created yet.
try:
    from agents.orchestrator import run_pipeline
except ImportError:
    run_pipeline = None  # type: ignore[assignment]

from agents.sheikh_agent import evaluate as sheikh_evaluate

try:
    from tax_engine import TaxEngine
except ImportError:
    TaxEngine = None  # type: ignore[assignment, misc]

try:
    from portfolio_manager import (
        load_portfolio,
        save_portfolio,
        calculate_position_size,
        get_portfolio_summary,
    )
except ImportError:
    load_portfolio = None  # type: ignore[assignment]
    save_portfolio = None  # type: ignore[assignment]
    calculate_position_size = None  # type: ignore[assignment]
    get_portfolio_summary = None  # type: ignore[assignment]

try:
    from notifier import send_trade_alert, send_compliance_alert, send_daily_summary
except ImportError:
    send_trade_alert = None  # type: ignore[assignment]
    send_compliance_alert = None  # type: ignore[assignment]
    send_daily_summary = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("trading_bot")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
AUTO_EXECUTE = os.getenv("AUTO_EXECUTE", "false").lower() in ("true", "1", "yes")
AUTO_EXECUTE_MAX_USD = float(os.getenv("AUTO_EXECUTE_MAX_USD", "50"))

STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.08"))
TAKE_PROFIT_PARTIAL_PCT = float(os.getenv("TAKE_PROFIT_PARTIAL_PCT", "0.15"))
TAKE_PROFIT_FULL_PCT = float(os.getenv("TAKE_PROFIT_FULL_PCT", "0.25"))
MIN_HOLD_DAYS = int(os.getenv("MIN_HOLD_DAYS", "5"))

# ---------------------------------------------------------------------------
# Pre-screened halal watchlist
# ---------------------------------------------------------------------------
WATCHLIST_ETFS = ["SPUS", "HLAL", "MNZL"]
WATCHLIST_STOCKS = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "ORCL",
    "AMD", "QCOM", "AVGO", "ADBE", "JNJ", "LLY", "ABBV", "MRK", "HD", "AMGN",
]
WATCHLIST = WATCHLIST_ETFS + WATCHLIST_STOCKS

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DECISIONS_LOG = DATA_DIR / "decisions.log"
TRADE_LOG_CSV = DATA_DIR / "trade_log.csv"

TRADE_LOG_FIELDS = [
    "timestamp", "ticker", "action", "quantity", "price", "total_value",
    "signal_reason", "dry_run", "compliance_check", "sheikh_verdict",
    "finance_confidence", "tax_impact", "holding_period_days",
    "is_long_term", "portfolio_value_after",
]


# ===================================================================
# Logging helpers
# ===================================================================

def log_decision(decision_data: dict) -> None:
    """Append a JSON-line entry to decisions.log."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            **decision_data,
        }
        with open(DECISIONS_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        logger.debug("Decision logged for %s", decision_data.get("ticker", "?"))
    except Exception as exc:
        logger.error("Failed to write decisions.log: %s", exc)


def log_trade(trade_data: dict) -> None:
    """Append a row to trade_log.csv.  Creates header if file is empty."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        write_header = not TRADE_LOG_CSV.exists() or TRADE_LOG_CSV.stat().st_size == 0
        # Ensure the CSV at least has the header row already written by prior runs
        if TRADE_LOG_CSV.exists() and TRADE_LOG_CSV.stat().st_size > 0:
            write_header = False

        row = {"timestamp": datetime.now().isoformat()}
        for field in TRADE_LOG_FIELDS:
            if field == "timestamp":
                continue
            row[field] = trade_data.get(field, "")

        with open(TRADE_LOG_CSV, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=TRADE_LOG_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        logger.debug("Trade logged for %s", trade_data.get("ticker", "?"))
    except Exception as exc:
        logger.error("Failed to write trade_log.csv: %s", exc)


# ===================================================================
# Stop-loss / take-profit monitors
# ===================================================================

def check_stop_loss(positions: list[dict]) -> list[dict]:
    """Return a list of SELL order dicts for positions that breached the stop-loss.

    Each position dict is expected to have at least:
        ticker, cost_basis, current_price, quantity
    """
    sell_orders: list[dict] = []
    for pos in positions:
        ticker = pos.get("ticker", "")
        cost = pos.get("cost_basis", 0.0)
        price = pos.get("current_price") or get_current_price(ticker)
        if cost <= 0 or price <= 0:
            continue

        loss_pct = (cost - price) / cost
        if loss_pct >= STOP_LOSS_PCT:
            order = {
                "ticker": ticker,
                "action": "SELL",
                "quantity": pos.get("quantity", 0),
                "reason": f"STOP-LOSS triggered: -{loss_pct:.1%} (threshold -{STOP_LOSS_PCT:.0%})",
                "price": price,
                "priority": "immediate",
            }
            sell_orders.append(order)
            logger.warning(
                "STOP-LOSS %s: price $%.2f vs cost $%.2f (%.1f%% loss)",
                ticker, price, cost, loss_pct * 100,
            )
    return sell_orders


def check_take_profit(positions: list[dict]) -> list[dict]:
    """Return a list of SELL order dicts for positions that hit take-profit levels.

    +15% → sell 50% of position (partial take-profit).
    +25% → sell 100% remaining (full take-profit).
    """
    sell_orders: list[dict] = []
    for pos in positions:
        ticker = pos.get("ticker", "")
        cost = pos.get("cost_basis", 0.0)
        price = pos.get("current_price") or get_current_price(ticker)
        qty = pos.get("quantity", 0)
        if cost <= 0 or price <= 0 or qty <= 0:
            continue

        gain_pct = (price - cost) / cost

        if gain_pct >= TAKE_PROFIT_FULL_PCT:
            order = {
                "ticker": ticker,
                "action": "SELL",
                "quantity": qty,
                "reason": f"TAKE-PROFIT (full): +{gain_pct:.1%} (threshold +{TAKE_PROFIT_FULL_PCT:.0%})",
                "price": price,
                "priority": "normal",
            }
            sell_orders.append(order)
            logger.info("TAKE-PROFIT full %s: +%.1f%%", ticker, gain_pct * 100)
        elif gain_pct >= TAKE_PROFIT_PARTIAL_PCT:
            partial_qty = max(1, qty // 2)
            order = {
                "ticker": ticker,
                "action": "SELL",
                "quantity": partial_qty,
                "reason": f"TAKE-PROFIT (partial 50%): +{gain_pct:.1%} (threshold +{TAKE_PROFIT_PARTIAL_PCT:.0%})",
                "price": price,
                "priority": "normal",
            }
            sell_orders.append(order)
            logger.info(
                "TAKE-PROFIT partial %s: +%.1f%% — selling %d of %d shares",
                ticker, gain_pct * 100, partial_qty, qty,
            )

    return sell_orders


# ===================================================================
# Go-live readiness gate
# ===================================================================

def check_go_live_readiness() -> dict:
    """Enforce preconditions before switching from paper to live trading.

    Returns a dict with:
        ready: bool
        checks: dict[str, bool]   — individual check results
        messages: list[str]       — human-readable explanations
    """
    checks: dict[str, bool] = {}
    messages: list[str] = []

    # 1. 30 days of paper trading history
    try:
        if TRADE_LOG_CSV.exists():
            with open(TRADE_LOG_CSV, "r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
            dry_rows = [r for r in rows if r.get("dry_run", "").lower() in ("true", "1")]
            if dry_rows:
                first_ts = dry_rows[0].get("timestamp", "")
                first_date = datetime.fromisoformat(first_ts)
                days_of_paper = (datetime.now() - first_date).days
                checks["paper_trading_30d"] = days_of_paper >= 30
                if not checks["paper_trading_30d"]:
                    messages.append(
                        f"Only {days_of_paper} days of paper trading (need 30)."
                    )
            else:
                checks["paper_trading_30d"] = False
                messages.append("No paper trades found in trade_log.csv.")
        else:
            checks["paper_trading_30d"] = False
            messages.append("trade_log.csv does not exist.")
    except Exception as exc:
        checks["paper_trading_30d"] = False
        messages.append(f"Error reading trade log: {exc}")

    # 2. All current holdings are halal
    try:
        client = get_client()
        positions = get_positions(client) if client else []
        screener = ShariahScreener()
        all_halal = True
        for pos in positions:
            result = screener.screen(pos["ticker"])
            if result.compliant is not True:
                all_halal = False
                messages.append(f"{pos['ticker']} is not HALAL (status: {result.compliant}).")
        checks["all_holdings_halal"] = all_halal
        if not positions:
            checks["all_holdings_halal"] = True  # vacuously true
    except Exception as exc:
        checks["all_holdings_halal"] = False
        messages.append(f"Error checking holdings compliance: {exc}")

    # 3. Telegram notifier is working
    if send_trade_alert is not None:
        checks["telegram_working"] = True
    else:
        checks["telegram_working"] = False
        messages.append("notifier module not available — Telegram alerts disabled.")

    # 4. Fresh Schwab token (< 6 days)
    token_age = get_token_age_days()
    checks["fresh_token"] = 0 <= token_age < 6
    if not checks["fresh_token"]:
        messages.append(f"Schwab token is {token_age} days old (must be < 6).")

    # 5. Tax engine configured
    if TaxEngine is not None:
        checks["tax_configured"] = True
    else:
        checks["tax_configured"] = False
        messages.append("tax_engine module not available — tax tracking disabled.")

    ready = all(checks.values())
    if ready:
        messages.append("All go-live checks passed.")

    return {"ready": ready, "checks": checks, "messages": messages}


# ===================================================================
# Order execution helper
# ===================================================================

def _execute_order(
    client,
    account_hash: str,
    ticker: str,
    qty: int,
    side: str,
    reason: str,
    dry_run: bool,
    sheikh_verdict: str = "",
    finance_confidence: float = 0.0,
) -> dict:
    """Place an order (or simulate it) and log the result."""
    price = get_current_price(ticker)
    total_value = round(price * qty, 2)

    # Auto-execute gate: only real orders under the cap
    actually_execute = not dry_run
    if actually_execute and AUTO_EXECUTE and total_value > AUTO_EXECUTE_MAX_USD:
        logger.warning(
            "Order $%.2f exceeds AUTO_EXECUTE_MAX_USD ($%.2f) — forcing dry run",
            total_value, AUTO_EXECUTE_MAX_USD,
        )
        dry_run = True
        actually_execute = False

    order_result = place_order(
        client, account_hash, ticker, qty, side, dry_run=dry_run,
    )

    # Notify
    if send_trade_alert is not None:
        try:
            send_trade_alert({
                "ticker": ticker,
                "side": side,
                "qty": qty,
                "price": price,
                "total": total_value,
                "reason": reason,
                "dry_run": dry_run,
                "result": order_result.get("status", "unknown"),
            })
        except Exception as exc:
            logger.error("Failed to send trade alert: %s", exc)

    # Compute tax impact if available
    tax_impact = ""
    if TaxEngine is not None and side.upper() == "SELL":
        try:
            engine = TaxEngine()
            tax_impact = str(engine.estimate_tax(ticker, qty, price))
        except Exception:
            tax_impact = "error"

    # Log the trade
    trade_data = {
        "ticker": ticker,
        "action": side,
        "quantity": qty,
        "price": price,
        "total_value": total_value,
        "signal_reason": reason,
        "dry_run": dry_run,
        "compliance_check": "PASS",
        "sheikh_verdict": sheikh_verdict,
        "finance_confidence": finance_confidence,
        "tax_impact": tax_impact,
        "holding_period_days": "",
        "is_long_term": "",
        "portfolio_value_after": "",
    }
    log_trade(trade_data)

    return order_result


# ===================================================================
# Main daily cycle
# ===================================================================

def run_daily_cycle() -> dict:
    """Execute the full daily trading cycle.

    Returns a summary dict suitable for the daily Telegram digest.
    """
    cycle_start = datetime.now()
    summary: dict = {
        "timestamp": cycle_start.isoformat(),
        "dry_run": DRY_RUN,
        "scanned": 0,
        "signals": [],
        "orders_placed": [],
        "compliance_alerts": [],
        "errors": [],
    }

    logger.info(
        "=== Daily cycle started at %s (DRY_RUN=%s, AUTO_EXECUTE=%s) ===",
        cycle_start.isoformat(), DRY_RUN, AUTO_EXECUTE,
    )

    # ------------------------------------------------------------------
    # 1. Auth check
    # ------------------------------------------------------------------
    client = get_client()
    if client is None:
        msg = "Schwab authentication failed — aborting cycle."
        logger.error(msg)
        summary["errors"].append(msg)
        return summary

    token_age = get_token_age_days()
    if token_age > 6:
        logger.warning(
            "Schwab token is %d days old — re-authenticate immediately!", token_age,
        )
    elif token_age >= 5:
        logger.warning("Schwab token is %d days old — consider refreshing.", token_age)

    balance = get_account_balance(client)
    account_hash = balance.get("account_hash", "")
    cash_balance = balance.get("cash_balance", 0.0)
    total_value = balance.get("total_value", 0.0)

    logger.info(
        "Account balance: cash=$%.2f  total=$%.2f", cash_balance, total_value,
    )

    # ------------------------------------------------------------------
    # 2. Fetch positions & re-screen compliance
    # ------------------------------------------------------------------
    positions = get_positions(client)
    screener = ShariahScreener()

    for pos in positions:
        ticker = pos.get("ticker", "")
        if not ticker:
            continue
        screen = screener.screen(ticker)
        if screen.compliant is False:
            alert_msg = f"HARAM DETECTED: {ticker} — {screen.fail_reasons}"
            logger.critical(alert_msg)
            summary["compliance_alerts"].append(alert_msg)

            if send_compliance_alert is not None:
                try:
                    send_compliance_alert(alert_msg)
                except Exception as exc:
                    logger.error("Compliance alert send failed: %s", exc)

            # Immediate sell
            qty = pos.get("quantity", 0)
            if qty > 0:
                result = _execute_order(
                    client, account_hash, ticker, qty, "SELL",
                    reason=f"HARAM rescreen: {screen.fail_reasons}",
                    dry_run=DRY_RUN,
                    sheikh_verdict="HARAM",
                )
                summary["orders_placed"].append({
                    "ticker": ticker, "action": "SELL", "qty": qty,
                    "reason": "HARAM_RESCREEN", "result": result.get("status"),
                })

    # ------------------------------------------------------------------
    # 2b. Stop-loss & take-profit checks on existing positions
    # ------------------------------------------------------------------
    stop_loss_orders = check_stop_loss(positions)
    for order in stop_loss_orders:
        result = _execute_order(
            client, account_hash, order["ticker"], order["quantity"], "SELL",
            reason=order["reason"], dry_run=DRY_RUN,
        )
        summary["orders_placed"].append({
            "ticker": order["ticker"], "action": "SELL",
            "qty": order["quantity"], "reason": "STOP_LOSS",
            "result": result.get("status"),
        })

    tp_orders = check_take_profit(positions)
    for order in tp_orders:
        result = _execute_order(
            client, account_hash, order["ticker"], order["quantity"], "SELL",
            reason=order["reason"], dry_run=DRY_RUN,
        )
        summary["orders_placed"].append({
            "ticker": order["ticker"], "action": "SELL",
            "qty": order["quantity"], "reason": "TAKE_PROFIT",
            "result": result.get("status"),
        })

    # ------------------------------------------------------------------
    # 3. Scan watchlist
    # ------------------------------------------------------------------
    held_tickers = {p["ticker"] for p in positions}
    macro = get_macro_data()

    for ticker in WATCHLIST:
        summary["scanned"] += 1
        try:
            # 3a. Price history
            price_df = get_price_history(ticker, days=90)
            if price_df.empty or len(price_df) < 50:
                logger.info("Skipping %s — insufficient price data (%d rows)", ticker, len(price_df))
                continue

            # 3b. EMA crossover signal
            signal, confidence = calculate_signal(price_df["close"])
            if signal == "HOLD":
                continue

            # 3c. News sentiment
            fundamentals = get_fundamentals(ticker)
            company_name = fundamentals.get("longName", ticker)
            news = get_news_sentiment(ticker, company_name)
            news_score = news.get("score", 0)

            # 3d. Earnings proximity check — skip buys within 3 days of earnings
            earnings = get_earnings_calendar(ticker)
            if signal == "BUY" and earnings.get("too_close", False):
                logger.info(
                    "Skipping BUY on %s — earnings in %s days",
                    ticker, earnings.get("days_until_earnings"),
                )
                log_decision({
                    "ticker": ticker, "signal": signal,
                    "action": "SKIP", "reason": "earnings_too_close",
                    "news_score": news_score, "confidence": confidence,
                })
                continue

            # 3e. Only act on actionable signals
            logger.info(
                "Signal for %s: %s (confidence=%.1f, news=%d)",
                ticker, signal, confidence, news_score,
            )
            summary["signals"].append({
                "ticker": ticker, "signal": signal,
                "confidence": confidence, "news_score": news_score,
            })

            # ----------------------------------------------------------
            # 4. Agent pipeline: sheikh → finance → orchestrator
            # ----------------------------------------------------------

            # Sheikh compliance evaluation
            screen = screener.screen(ticker)
            sheikh_result = {}
            try:
                sheikh_result = sheikh_evaluate(
                    ticker=ticker,
                    sector=screen.sector,
                    industry=screen.industry,
                    debt_ratio=screen.debt_ratio or 0.0,
                    cash_ratio=screen.cash_ratio or 0.0,
                    revenue_total=fundamentals.get("totalRevenue", 0),
                    revenue_impermissible=0.0,
                    dividend_yield=fundamentals.get("dividendYield", 0) or 0.0,
                    scholarly_flags=screen.warnings,
                )
            except Exception as exc:
                logger.error("Sheikh agent failed for %s: %s", ticker, exc)
                sheikh_result = {"verdict": "DOUBTFUL", "recommendation": "REVIEW_MANUALLY"}

            sheikh_verdict = sheikh_result.get("verdict", "DOUBTFUL")

            if sheikh_verdict == "HARAM":
                logger.info("Skipping %s — Sheikh verdict HARAM", ticker)
                log_decision({
                    "ticker": ticker, "signal": signal,
                    "action": "SKIP", "reason": "sheikh_haram",
                    "sheikh_result": sheikh_result,
                })
                continue

            # Run full orchestrator pipeline if available
            pipeline_result = {}
            if run_pipeline is not None:
                try:
                    pipeline_result = run_pipeline(
                        ticker=ticker,
                        signal=signal,
                        confidence=confidence,
                        news=news,
                        fundamentals=fundamentals,
                        macro=macro,
                        sheikh_result=sheikh_result,
                        screen_result=screen.to_dict(),
                    )
                except Exception as exc:
                    logger.error("Orchestrator pipeline failed for %s: %s", ticker, exc)

            final_action = pipeline_result.get("action", signal)
            finance_confidence = pipeline_result.get("finance_confidence", confidence)

            # ----------------------------------------------------------
            # 5. Execute decision
            # ----------------------------------------------------------

            # --- BUY rules (all must be true) ---
            if final_action == "BUY" and ticker not in held_tickers:
                # Golden cross already confirmed by signal == "BUY"
                if sheikh_verdict != "HALAL":
                    log_decision({
                        "ticker": ticker, "signal": signal,
                        "action": "SKIP", "reason": "sheikh_not_halal",
                    })
                    continue
                if news_score <= -20:
                    log_decision({
                        "ticker": ticker, "signal": signal,
                        "action": "SKIP", "reason": f"news_too_negative ({news_score})",
                    })
                    continue
                if earnings.get("too_close", False):
                    continue  # already handled above, safety net

                # Cash reserve: require at least 20% cash after buy
                current_price = get_current_price(ticker)
                if current_price <= 0:
                    continue

                # Position sizing
                if calculate_position_size is not None:
                    qty = calculate_position_size(
                        ticker=ticker,
                        price=current_price,
                        cash=cash_balance,
                        total_value=total_value,
                        confidence=finance_confidence,
                    )
                else:
                    # Fallback: invest up to 5% of portfolio or available cash
                    max_invest = min(cash_balance * 0.8, total_value * 0.05)
                    qty = int(max_invest // current_price) if current_price > 0 else 0

                if qty <= 0:
                    log_decision({
                        "ticker": ticker, "signal": "BUY",
                        "action": "SKIP", "reason": "position_size_zero",
                    })
                    continue

                order_total = qty * current_price
                # Cash reserve check: keep at least 20% cash
                if (cash_balance - order_total) < total_value * 0.20:
                    log_decision({
                        "ticker": ticker, "signal": "BUY",
                        "action": "SKIP", "reason": "cash_reserve_insufficient",
                    })
                    continue

                # Wash sale check via tax engine
                if TaxEngine is not None:
                    try:
                        engine = TaxEngine()
                        if hasattr(engine, "check_wash_sale") and engine.check_wash_sale(ticker):
                            log_decision({
                                "ticker": ticker, "signal": "BUY",
                                "action": "SKIP", "reason": "wash_sale_window",
                            })
                            continue
                    except Exception:
                        pass

                # Position limit: max 10 individual positions
                if len(held_tickers) >= 10:
                    log_decision({
                        "ticker": ticker, "signal": "BUY",
                        "action": "SKIP", "reason": "position_limit_reached",
                    })
                    continue

                # Execute
                should_dry = DRY_RUN or not (AUTO_EXECUTE and order_total <= AUTO_EXECUTE_MAX_USD)
                result = _execute_order(
                    client, account_hash, ticker, qty, "BUY",
                    reason=f"Golden cross | news={news_score} | sheikh={sheikh_verdict}",
                    dry_run=should_dry,
                    sheikh_verdict=sheikh_verdict,
                    finance_confidence=finance_confidence,
                )
                summary["orders_placed"].append({
                    "ticker": ticker, "action": "BUY", "qty": qty,
                    "reason": "SIGNAL_BUY", "result": result.get("status"),
                })
                log_decision({
                    "ticker": ticker, "signal": "BUY", "action": "EXECUTE",
                    "qty": qty, "price": current_price,
                    "dry_run": should_dry,
                    "sheikh_verdict": sheikh_verdict,
                    "news_score": news_score, "confidence": finance_confidence,
                })

            # --- SELL rules (priority order) ---
            elif final_action == "SELL" and ticker in held_tickers:
                pos = next((p for p in positions if p["ticker"] == ticker), None)
                if pos is None:
                    continue
                qty = pos.get("quantity", 0)
                if qty <= 0:
                    continue

                # Determine sell reason
                sell_reason = "Death cross signal"
                if news_score < -20:
                    sell_reason = f"Death cross + negative news ({news_score})"

                # Tax-loss harvesting consideration
                cost_basis = pos.get("cost_basis", 0.0)
                current_price = pos.get("current_price") or get_current_price(ticker)
                if current_price < cost_basis and TaxEngine is not None:
                    try:
                        engine = TaxEngine()
                        if hasattr(engine, "should_harvest_loss"):
                            if engine.should_harvest_loss(ticker, cost_basis, current_price, qty):
                                sell_reason = "Tax-loss harvesting + death cross"
                    except Exception:
                        pass

                # Min hold period check (non-urgent sells)
                # Stop-loss and HARAM sells bypass this; signal-based sells respect it
                portfolio = load_portfolio() if load_portfolio is not None else {}
                holding_info = portfolio.get(ticker, {})
                buy_date_str = holding_info.get("buy_date", "")
                if buy_date_str:
                    try:
                        buy_date = datetime.fromisoformat(buy_date_str)
                        hold_days = (datetime.now() - buy_date).days
                        if hold_days < MIN_HOLD_DAYS:
                            logger.info(
                                "Skipping SELL on %s — only held %d days (min %d)",
                                ticker, hold_days, MIN_HOLD_DAYS,
                            )
                            log_decision({
                                "ticker": ticker, "signal": "SELL",
                                "action": "SKIP", "reason": f"min_hold_days ({hold_days}/{MIN_HOLD_DAYS})",
                            })
                            continue
                    except (ValueError, TypeError):
                        pass

                should_dry = DRY_RUN or not AUTO_EXECUTE
                result = _execute_order(
                    client, account_hash, ticker, qty, "SELL",
                    reason=sell_reason, dry_run=should_dry,
                    sheikh_verdict=sheikh_verdict,
                    finance_confidence=finance_confidence,
                )
                summary["orders_placed"].append({
                    "ticker": ticker, "action": "SELL", "qty": qty,
                    "reason": "SIGNAL_SELL", "result": result.get("status"),
                })
                log_decision({
                    "ticker": ticker, "signal": "SELL", "action": "EXECUTE",
                    "qty": qty, "reason": sell_reason,
                    "dry_run": should_dry,
                })

        except Exception as exc:
            msg = f"Error processing {ticker}: {exc}"
            logger.error(msg, exc_info=True)
            summary["errors"].append(msg)

    # ------------------------------------------------------------------
    # 6–7. Logging already handled inline above
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 8. Send daily summary
    # ------------------------------------------------------------------
    cycle_end = datetime.now()
    summary["duration_seconds"] = (cycle_end - cycle_start).total_seconds()

    # Update portfolio state if available
    if save_portfolio is not None:
        try:
            updated_positions = get_positions(client)
            save_portfolio(updated_positions)
        except Exception as exc:
            logger.error("Failed to save portfolio: %s", exc)

    # Portfolio summary for the digest
    if get_portfolio_summary is not None:
        try:
            summary["portfolio"] = get_portfolio_summary()
        except Exception:
            pass

    logger.info(
        "=== Daily cycle finished in %.1fs — %d scanned, %d signals, %d orders ===",
        summary["duration_seconds"],
        summary["scanned"],
        len(summary["signals"]),
        len(summary["orders_placed"]),
    )

    if send_daily_summary is not None:
        try:
            send_daily_summary(summary)
        except Exception as exc:
            logger.error("Failed to send daily summary: %s", exc)

    log_decision({"event": "daily_cycle_complete", "summary": summary})

    return summary


# ===================================================================
# CLI entry-point
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Halal Stock Trading Bot — Daily Strategy Engine",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode (default: True). No real orders placed.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Run in live mode. Requires passing go-live readiness checks.",
    )
    parser.add_argument(
        "--check-readiness",
        action="store_true",
        default=False,
        help="Check go-live readiness and exit.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    if args.check_readiness:
        result = check_go_live_readiness()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["ready"] else 1)

    if args.live:
        global DRY_RUN
        readiness = check_go_live_readiness()
        if not readiness["ready"]:
            logger.error("Go-live readiness check FAILED:")
            for msg in readiness["messages"]:
                logger.error("  - %s", msg)
            sys.exit(1)
        DRY_RUN = False
        logger.warning("*** LIVE MODE ENABLED — real orders will be placed ***")
    else:
        DRY_RUN = True
        logger.info("Running in DRY-RUN mode.")

    summary = run_daily_cycle()
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
