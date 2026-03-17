"""
Module 1: Schwab API Authentication & Account Operations
Uses schwab-py library for OAuth 2.0 connection to Charles Schwab Trader API.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

APP_KEY = os.getenv("SCHWAB_APP_KEY", "")
APP_SECRET = os.getenv("SCHWAB_APP_SECRET", "")
CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL", "https://127.0.0.1")
TOKEN_PATH = os.getenv("SCHWAB_TOKEN_PATH", "schwab_token.json")


def get_client(force_reauth=False):
    """
    Load saved token or trigger browser OAuth flow.
    Schwab tokens expire every 7 days — warns when token age > 6 days.
    """
    try:
        import schwab
        from schwab import auth
    except ImportError:
        logger.error("schwab-py not installed. Run: pip install schwab-py")
        return None

    token_path = Path(TOKEN_PATH)

    if token_path.exists() and not force_reauth:
        token_age = datetime.now() - datetime.fromtimestamp(token_path.stat().st_mtime)
        if token_age > timedelta(days=6):
            logger.warning(
                "Schwab token is %d days old. Re-authenticate soon (expires at 7 days).",
                token_age.days,
            )

        try:
            client = auth.client_from_token_file(TOKEN_PATH, APP_KEY, APP_SECRET)
            logger.info("Schwab client loaded from saved token.")
            return client
        except Exception as e:
            logger.warning("Saved token invalid: %s. Re-authenticating.", e)

    try:
        client = auth.client_from_manual_flow(
            APP_KEY, APP_SECRET, CALLBACK_URL, TOKEN_PATH
        )
        logger.info("Schwab client authenticated via manual flow.")
        return client
    except Exception as e:
        logger.error("Schwab authentication failed: %s", e)
        return None


def test_connection(client) -> dict:
    """Verify auth by calling get_account_numbers()."""
    if client is None:
        return {"status": "error", "message": "No client provided"}
    try:
        response = client.get_account_numbers()
        accounts = response.json()
        logger.info("Schwab connection verified. Accounts: %s", accounts)
        return {"status": "ok", "accounts": accounts}
    except Exception as e:
        logger.error("Schwab connection test failed: %s", e)
        return {"status": "error", "message": str(e)}


def get_account_balance(client) -> dict:
    """Returns cash_balance, total_value, buying_power."""
    if client is None:
        return {"error": "No client provided"}
    try:
        response = client.get_account_numbers()
        accounts = response.json()
        if not accounts:
            return {"error": "No accounts found"}

        account_hash = accounts[0].get("hashValue", "")
        acct_response = client.get_account(account_hash, fields=["positions"])
        acct_data = acct_response.json()

        balances = acct_data.get("securitiesAccount", {}).get("currentBalances", {})
        return {
            "cash_balance": balances.get("cashBalance", 0.0),
            "total_value": balances.get("liquidationValue", 0.0),
            "buying_power": balances.get("buyingPower", 0.0),
            "account_hash": account_hash,
        }
    except Exception as e:
        logger.error("Failed to get account balance: %s", e)
        return {"error": str(e)}


def get_positions(client) -> list:
    """Returns all current holdings with quantity, cost_basis, market_value."""
    if client is None:
        return []
    try:
        response = client.get_account_numbers()
        accounts = response.json()
        if not accounts:
            return []

        account_hash = accounts[0].get("hashValue", "")
        acct_response = client.get_account(account_hash, fields=["positions"])
        acct_data = acct_response.json()

        positions = acct_data.get("securitiesAccount", {}).get("positions", [])
        result = []
        for pos in positions:
            instrument = pos.get("instrument", {})
            result.append({
                "ticker": instrument.get("symbol", ""),
                "name": instrument.get("description", ""),
                "quantity": pos.get("longQuantity", 0),
                "cost_basis": pos.get("averagePrice", 0.0),
                "market_value": pos.get("marketValue", 0.0),
                "current_price": pos.get("currentDayProfitLoss", 0.0)
                + pos.get("averagePrice", 0.0),
                "day_pnl": pos.get("currentDayProfitLoss", 0.0),
                "total_pnl": pos.get("marketValue", 0.0)
                - (pos.get("averagePrice", 0.0) * pos.get("longQuantity", 0)),
            })
        return result
    except Exception as e:
        logger.error("Failed to get positions: %s", e)
        return []


def place_order(client, account_hash, symbol, qty, side, dry_run=True) -> dict:
    """
    Place a MARKET order. dry_run=True by default — NEVER change default.
    Logs every call regardless of dry_run status.
    """
    order_info = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "quantity": qty,
        "side": side,
        "dry_run": dry_run,
    }

    logger.info("Order request: %s", json.dumps(order_info))

    if dry_run:
        logger.info("[DRY RUN] Would place %s order: %s x %d", side, symbol, qty)
        return {"status": "dry_run", "order": order_info}

    if client is None:
        return {"status": "error", "message": "No client provided"}

    try:
        from schwab.orders.equities import equity_market_order

        if side.upper() == "BUY":
            from schwab.orders.common import Duration, Session

            order = equity_market_order(symbol, qty, "BUY")
        elif side.upper() == "SELL":
            order = equity_market_order(symbol, qty, "SELL")
        else:
            return {"status": "error", "message": f"Invalid side: {side}"}

        response = client.place_order(account_hash, order)
        logger.info("Order placed: %s %s x %d — Response: %s", side, symbol, qty, response.status_code)
        return {"status": "executed", "order": order_info, "response_code": response.status_code}
    except Exception as e:
        logger.error("Order failed: %s", e)
        return {"status": "error", "message": str(e), "order": order_info}


def get_token_age_days() -> int:
    """Returns the age of the token file in days, or -1 if not found."""
    token_path = Path(TOKEN_PATH)
    if not token_path.exists():
        return -1
    age = datetime.now() - datetime.fromtimestamp(token_path.stat().st_mtime)
    return age.days


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Schwab Auth Module")
    print(f"Token path: {TOKEN_PATH}")
    print(f"Token age: {get_token_age_days()} days")
    print("To authenticate, set SCHWAB_APP_KEY and SCHWAB_APP_SECRET in .env")
    client = get_client()
    if client:
        result = test_connection(client)
        print(f"Connection: {result}")
        balance = get_account_balance(client)
        print(f"Balance: {balance}")
    else:
        print("No client available. Configure Schwab credentials in .env")
