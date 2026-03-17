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

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "compliance_cache.json"

# Haram business categories — auto-exclude
HARAM_INDUSTRIES = {
    # Conventional finance (riba)
    "banks—diversified", "banks—regional", "insurance—diversified",
    "insurance—life", "insurance—property & casualty", "insurance—reinsurance",
    "insurance—specialty", "credit services", "mortgage finance",
    "consumer lending", "financial conglomerates",
    # Gambling
    "gambling", "casinos & gaming",
    # Alcohol
    "alcoholic beverages", "brewers", "wineries & distilleries",
    # Tobacco
    "tobacco",
    # Adult content
    "adult entertainment",
    # Weapons (offensive — per AAOIFI SS 21)
    "weapons", "arms", "ammunition",
    # Cannabis (intoxicant — haram by consensus, Quran 5:90)
    "cannabis", "marijuana",
}

HARAM_KEYWORDS = {
    # Finance / riba
    "banking", "insurance", "mortgage", "lending", "credit",
    "interest", "consumer finance",
    # Gambling
    "casino", "gambling",
    # Alcohol
    "alcohol", "brewery", "distillery", "winery", "liquor", "nightclub",
    # Tobacco
    "tobacco",
    # Pork
    "pork",
    # Adult content
    "adult entertainment",
    # Weapons
    "weapons", "arms", "ammunition",
    # Cannabis / intoxicants
    "cannabis", "marijuana",
    # Riba instruments (T-bills, bonds, money markets)
    "treasury", "t-bill", "bond fund", "money market", "fixed income",
}

# Known non-compliant — never trade
BLACKLIST = {
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BRK.A", "BRK.B",
    "V", "MA", "AXP", "MO", "PM", "BTI", "BUD", "LVS", "MGM",
}

# Doubtful categories requiring Sheikh Agent review
DOUBTFUL_INDUSTRIES = {
    "aerospace & defense", "entertainment", "media",
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

            # Screen 3: Interest-bearing debt / market cap < 33.33% (AAOIFI)
            # One-third threshold per hadith of Sa'd ibn Abi Waqqas (Bukhari #2742)
            market_cap = info.get("marketCap", 0)
            total_debt = info.get("totalDebt", 0)

            if market_cap and market_cap > 0:
                result.debt_ratio = round(total_debt / market_cap, 4) if total_debt else 0.0

                if result.debt_ratio > 0.3333:
                    result.compliant = False
                    result.fail_reasons.append(
                        f"Debt ratio {result.debt_ratio:.1%} exceeds AAOIFI 33.33% threshold (one-third)"
                    )
                elif result.debt_ratio > 0.30:
                    result.warnings.append(
                        f"Debt ratio {result.debt_ratio:.1%} is borderline (30-33% range)"
                    )
            else:
                result.warnings.append("Market cap unavailable — cannot compute debt ratio")

            # Screen 4: Interest-bearing deposits / market cap < 33.33% (AAOIFI)
            # Per AAOIFI SS 21, denominator is market cap (not equity)
            cash = info.get("totalCash", 0) or 0
            short_investments = info.get("shortTermInvestments", 0) or 0

            if market_cap and market_cap > 0:
                cash_deposits = cash + short_investments
                result.cash_ratio = round(cash_deposits / market_cap, 4)

                if result.cash_ratio > 0.3333:
                    result.compliant = False
                    result.fail_reasons.append(
                        f"Cash/deposit ratio {result.cash_ratio:.1%} exceeds AAOIFI 33.33% of market cap"
                    )
                elif result.cash_ratio > 0.30:
                    result.warnings.append(
                        f"Cash/deposit ratio {result.cash_ratio:.1%} is borderline (30-33% range)"
                    )
            else:
                result.warnings.append("Market cap unavailable — cannot compute cash/deposit ratio")

            # Screen 5: Receivables / market cap < 33.33% (AAOIFI)
            # Unenforced before — now a hard fail per bay' al-dayn prohibition
            receivables = info.get("netReceivables", 0) or 0

            if market_cap and market_cap > 0:
                result.receivables_ratio = round(receivables / market_cap, 4)

                if result.receivables_ratio > 0.3333:
                    result.compliant = False
                    result.fail_reasons.append(
                        f"Receivables ratio {result.receivables_ratio:.1%} exceeds AAOIFI 33.33% of market cap"
                    )
                elif result.receivables_ratio > 0.30:
                    result.warnings.append(
                        f"Receivables ratio {result.receivables_ratio:.1%} is borderline (30-33% range)"
                    )
            else:
                result.receivables_ratio = None

            # Purification calculation
            # Use interest INCOME (haram earnings), not interest expense (cost of debt).
            # Stored as a fraction (0.0–1.0) for consistency with zakat_calculator.
            interest_income = abs(info.get("interestIncome", 0) or 0)
            # Fallback: if interestIncome unavailable, estimate from cash ratio
            if interest_income == 0 and result.cash_ratio and result.cash_ratio > 0:
                # Conservative proxy: assume cash earns ~4% interest
                interest_income = (info.get("totalCash", 0) or 0) * 0.04
            total_revenue = info.get("totalRevenue", 0) or 0

            if total_revenue > 0 and interest_income > 0:
                result.purification_pct = round(
                    min(interest_income / total_revenue, 1.0), 4
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
        # purification_pct is already a fraction (0.0–1.0)
        donate = round(dividend_amount * result.purification_pct, 2)
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
