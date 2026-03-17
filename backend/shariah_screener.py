"""
Module 2: Shariah Compliance Screener
Screens stocks against AAOIFI Islamic finance standards using five financial screens.
"""

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional
from pathlib import Path

import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CACHE_PATH = Path("data/compliance_cache.json")

# Haram business categories — auto-exclude
HARAM_INDUSTRIES = {
    "banks—diversified", "banks—regional", "insurance—diversified",
    "insurance—life", "insurance—property & casualty", "insurance—reinsurance",
    "insurance—specialty", "gambling", "casinos & gaming",
    "tobacco", "alcoholic beverages", "brewers", "wineries & distilleries",
    "adult entertainment",
}

HARAM_KEYWORDS = {
    "banking", "insurance", "casino", "gambling", "tobacco", "alcohol",
    "brewery", "distillery", "winery", "pork", "adult entertainment",
}

# Known non-compliant — never trade
BLACKLIST = {
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BRK.A", "BRK.B",
    "V", "MA", "AXP", "MO", "PM", "BTI", "BUD", "LVS", "MGM",
}

# Doubtful categories requiring Sheikh Agent review
DOUBTFUL_INDUSTRIES = {
    "aerospace & defense", "weapons", "entertainment", "media",
    "advertising", "hotels", "resorts & cruise lines",
}

# Known scholarly disputes
SCHOLARLY_FLAGS = {
    "TSLA": "Debt ratio approaches AAOIFI limit. Deobandi scholars often exclude.",
    "AAPL": "Services segment (Apple Music, TV+) — monitor if > 5% of revenue.",
    "AMZN": "Advertising and marketplace content — needs Sheikh Agent review.",
}


@dataclass
class ScreenResult:
    ticker: str
    company_name: str = ""
    sector: str = ""
    industry: str = ""
    compliant: Optional[bool] = None  # True=HALAL, False=HARAM, None=DOUBTFUL
    fail_reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    debt_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    receivables_ratio: Optional[float] = None
    purification_pct: float = 0.0
    source: str = "yfinance"
    madhab_notes: str = ""

    def to_dict(self):
        return asdict(self)


class ShariahScreener:
    def __init__(self, zoya_api_key=None):
        self.zoya_api_key = zoya_api_key or os.getenv("ZOYA_API_KEY")
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        try:
            if CACHE_PATH.exists():
                return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
        return {}

    def _save_cache(self):
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(self._cache, indent=2))
        except Exception as e:
            logger.warning("Failed to save compliance cache: %s", e)

    def screen(self, ticker: str) -> ScreenResult:
        """Screen a single ticker against AAOIFI standards."""
        ticker = ticker.upper().strip()
        result = ScreenResult(ticker=ticker)

        # Check blacklist first
        if ticker in BLACKLIST:
            result.compliant = False
            result.fail_reasons.append("Ticker is on known non-compliant blacklist")
            return result

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            result.company_name = info.get("longName", info.get("shortName", ticker))
            result.sector = info.get("sector", "Unknown")
            result.industry = info.get("industry", "Unknown")

            # Screen 1: Primary Business Activity
            industry_lower = result.industry.lower()
            sector_lower = result.sector.lower()

            if industry_lower in HARAM_INDUSTRIES or any(
                kw in industry_lower for kw in HARAM_KEYWORDS
            ):
                result.compliant = False
                result.fail_reasons.append(
                    f"Primary business is haram: {result.industry}"
                )
                return result

            if any(kw in sector_lower for kw in HARAM_KEYWORDS):
                result.compliant = False
                result.fail_reasons.append(f"Sector is haram: {result.sector}")
                return result

            # Check doubtful industries
            if industry_lower in DOUBTFUL_INDUSTRIES or any(
                d in industry_lower for d in DOUBTFUL_INDUSTRIES
            ):
                result.warnings.append(
                    f"Industry '{result.industry}' is in doubtful category — needs Sheikh review"
                )

            # Screen 2: Secondary activity (haram revenue < 5%)
            # yfinance doesn't provide revenue breakdown, flag if in borderline sector
            if result.warnings:
                result.warnings.append(
                    "Secondary activity screen: manual review recommended for revenue breakdown"
                )

            # Screen 3: Interest-bearing debt / market cap < 30%
            market_cap = info.get("marketCap", 0)
            total_debt = info.get("totalDebt", 0)

            if market_cap and market_cap > 0:
                result.debt_ratio = round(total_debt / market_cap, 4) if total_debt else 0.0

                if result.debt_ratio > 0.33:
                    result.compliant = False
                    result.fail_reasons.append(
                        f"Debt ratio {result.debt_ratio:.1%} exceeds 33% threshold"
                    )
                elif result.debt_ratio > 0.30:
                    result.compliant = False
                    result.fail_reasons.append(
                        f"Debt ratio {result.debt_ratio:.1%} exceeds 30% AAOIFI threshold"
                    )
                elif result.debt_ratio > 0.28:
                    result.warnings.append(
                        f"Debt ratio {result.debt_ratio:.1%} is borderline (28-30% range)"
                    )
            else:
                result.warnings.append("Market cap unavailable — cannot compute debt ratio")

            # Screen 4: Interest-bearing deposits / total equity < 30%
            cash = info.get("totalCash", 0) or 0
            short_investments = info.get("shortTermInvestments", 0) or 0
            total_equity = info.get("totalStockholderEquity") or info.get("bookValue", 0)

            if total_equity and total_equity > 0:
                cash_deposits = cash + short_investments
                result.cash_ratio = round(cash_deposits / total_equity, 4)

                if result.cash_ratio > 0.33:
                    result.compliant = False
                    result.fail_reasons.append(
                        f"Cash/deposit ratio {result.cash_ratio:.1%} exceeds 33% of equity"
                    )
                elif result.cash_ratio > 0.30:
                    result.compliant = False
                    result.fail_reasons.append(
                        f"Cash/deposit ratio {result.cash_ratio:.1%} exceeds 30% AAOIFI threshold"
                    )
                elif result.cash_ratio > 0.28:
                    result.warnings.append(
                        f"Cash/deposit ratio {result.cash_ratio:.1%} is borderline"
                    )
            else:
                result.warnings.append("Equity data unavailable — cannot compute cash ratio")

            # Screen 5: Receivables ratio
            receivables = info.get("netReceivables", 0) or 0
            total_assets = info.get("totalAssets", 0) or 0

            if total_assets and total_assets > 0:
                result.receivables_ratio = round(receivables / total_assets, 4)
            else:
                result.receivables_ratio = None

            # Purification calculation
            # Estimate haram income portion from interest income / total revenue
            interest_expense = abs(info.get("interestExpense", 0) or 0)
            total_revenue = info.get("totalRevenue", 0) or 0

            if total_revenue > 0 and interest_expense > 0:
                result.purification_pct = round(
                    min(interest_expense / total_revenue * 100, 100), 2
                )
            else:
                result.purification_pct = 0.0

            # Check scholarly flags
            if ticker in SCHOLARLY_FLAGS:
                result.madhab_notes = SCHOLARLY_FLAGS[ticker]
                result.warnings.append(f"Scholarly flag: {SCHOLARLY_FLAGS[ticker]}")

            # Final verdict
            if result.compliant is False:
                pass  # Already marked HARAM
            elif result.fail_reasons:
                result.compliant = False
            elif result.warnings:
                result.compliant = None  # DOUBTFUL
            else:
                result.compliant = True  # HALAL

        except Exception as e:
            logger.error("Screening failed for %s: %s", ticker, e)
            result.compliant = None
            result.warnings.append(f"Screening error: {str(e)}")

        # Cache result
        self._cache[ticker] = result.to_dict()
        self._save_cache()

        return result

    def screen_portfolio(self, tickers: list) -> list:
        """Screen a list of tickers."""
        return [self.screen(t) for t in tickers]

    def get_compliant(self, tickers: list) -> list:
        """Return only compliant tickers from a list."""
        results = self.screen_portfolio(tickers)
        return [r.ticker for r in results if r.compliant is True]

    def calculate_purification(self, ticker: str, dividend_amount: float) -> float:
        """Calculate the amount to donate from dividends for purification."""
        result = self.screen(ticker)
        donate = round(dividend_amount * result.purification_pct / 100, 2)
        return donate


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    screener = ShariahScreener()

    test_tickers = ["SPUS", "JPM", "NVDA", "AAPL", "TSLA"]
    print("\n=== Shariah Compliance Screening ===\n")
    for ticker in test_tickers:
        result = screener.screen(ticker)
        status = {True: "HALAL ✅", False: "HARAM ❌", None: "DOUBTFUL ⚠️"}[
            result.compliant
        ]
        print(f"{ticker:6s} | {status:12s} | {result.company_name}")
        if result.fail_reasons:
            for r in result.fail_reasons:
                print(f"         FAIL: {r}")
        if result.warnings:
            for w in result.warnings:
                print(f"         WARN: {w}")
        if result.debt_ratio is not None:
            print(f"         Debt ratio: {result.debt_ratio:.1%}")
        if result.purification_pct > 0:
            print(f"         Purification: {result.purification_pct:.2f}%")
        print()
