"""
Portfolio Allocator — Dollar Amount to Halal Stock Distribution
Given a dollar amount, recommends how to distribute funds across
Shariah-compliant stocks using AI analysis and quantitative scoring.
"""

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional

import anthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Halal universe — pre-screened tickers
HALAL_ETFS = ["SPUS", "HLAL", "MNZL"]
HALAL_STOCKS = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "ORCL",
    "AMD", "QCOM", "AVGO", "ADBE", "JNJ", "LLY", "ABBV", "MRK", "HD", "AMGN",
]

# Risk profiles
RISK_PROFILES = {
    "conservative": {
        "etf_pct": 0.60,
        "stock_pct": 0.30,
        "cash_pct": 0.10,
        "max_single_stock": 0.10,
        "max_single_etf": 0.30,
        "description": "60% ETFs, 30% stocks, 10% cash reserve",
    },
    "moderate": {
        "etf_pct": 0.40,
        "stock_pct": 0.50,
        "cash_pct": 0.10,
        "max_single_stock": 0.15,
        "max_single_etf": 0.25,
        "description": "40% ETFs, 50% stocks, 10% cash reserve",
    },
    "aggressive": {
        "etf_pct": 0.20,
        "stock_pct": 0.70,
        "cash_pct": 0.10,
        "max_single_stock": 0.20,
        "max_single_etf": 0.20,
        "description": "20% ETFs, 70% stocks, 10% cash reserve",
    },
}

ALLOCATOR_SYSTEM_PROMPT = """You are a senior halal portfolio strategist. Given a dollar amount,
risk profile, and market data for Shariah-compliant stocks, you recommend an optimal allocation.

Rules:
- All stocks must be Shariah-compliant (pre-screened)
- Maintain the cash reserve percentage specified by the risk profile
- Diversify across sectors — never concentrate >40% in one sector
- Consider current valuations (forward P/E), momentum (EMA signals), and sector balance
- Whole shares only — calculate exact share counts at current prices
- Any remainder after whole-share rounding goes to cash reserve
- For small portfolios (<$1000), recommend 3-5 positions max to avoid over-fragmentation
- For medium portfolios ($1000-$10000), recommend 5-10 positions
- For large portfolios (>$10000), recommend 8-15 positions

You MUST return valid JSON with this structure:
{
  "total_amount": 0.0,
  "cash_reserve": 0.0,
  "invested_amount": 0.0,
  "risk_profile": "",
  "allocations": [
    {
      "ticker": "",
      "company_name": "",
      "sector": "",
      "shares": 0,
      "price_per_share": 0.0,
      "total_cost": 0.0,
      "portfolio_pct": 0.0,
      "rationale": ""
    }
  ],
  "sector_breakdown": {"Technology": 0.0, "Healthcare": 0.0},
  "strategy_summary": "",
  "expected_dividend_yield": 0.0,
  "rebalance_frequency": "quarterly",
  "warnings": []
}"""


@dataclass
class Allocation:
    ticker: str
    company_name: str = ""
    sector: str = ""
    shares: int = 0
    price_per_share: float = 0.0
    total_cost: float = 0.0
    portfolio_pct: float = 0.0
    rationale: str = ""


@dataclass
class AllocationPlan:
    total_amount: float = 0.0
    cash_reserve: float = 0.0
    invested_amount: float = 0.0
    risk_profile: str = "moderate"
    allocations: list = field(default_factory=list)
    sector_breakdown: dict = field(default_factory=dict)
    strategy_summary: str = ""
    expected_dividend_yield: float = 0.0
    rebalance_frequency: str = "quarterly"
    warnings: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _gather_market_data(tickers: list) -> list:
    """Gather current price, fundamentals, and signals for each ticker."""
    from backend.data_fetcher import (
        get_current_price,
        get_fundamentals,
        get_price_history,
        calculate_signal,
    )
    from backend.shariah_screener import ShariahScreener

    screener = ShariahScreener()
    market_data = []

    for ticker in tickers:
        try:
            price = get_current_price(ticker)
            if price <= 0:
                continue

            fundamentals = get_fundamentals(ticker)
            compliance = screener.screen(ticker)

            # Only include compliant stocks
            if compliance.compliant is False:
                continue

            # Get EMA signal
            df = get_price_history(ticker, 90)
            signal, confidence = ("HOLD", 0.0)
            if not df.empty and len(df) >= 50:
                signal, confidence = calculate_signal(df["close"])

            market_data.append({
                "ticker": ticker,
                "company_name": fundamentals.get("longName", ticker),
                "sector": fundamentals.get("sector", "Unknown"),
                "industry": fundamentals.get("industry", "Unknown"),
                "price": round(price, 2),
                "market_cap": fundamentals.get("marketCap", 0),
                "forward_pe": fundamentals.get("forwardPE", 0),
                "dividend_yield": fundamentals.get("dividendYield", 0) or 0,
                "ema_signal": signal,
                "ema_confidence": confidence,
                "compliant": "HALAL" if compliance.compliant else "DOUBTFUL",
                "purification_pct": compliance.purification_pct,
                "debt_ratio": compliance.debt_ratio,
            })
        except Exception as e:
            logger.warning("Failed to gather data for %s: %s", ticker, e)

    return market_data


def _score_and_allocate_simple(
    amount: float, market_data: list, risk_profile: str
) -> AllocationPlan:
    """Fallback quantitative allocation without AI (if no API key)."""
    profile = RISK_PROFILES.get(risk_profile, RISK_PROFILES["moderate"])
    plan = AllocationPlan(
        total_amount=amount,
        risk_profile=risk_profile,
    )

    cash_reserve = round(amount * profile["cash_pct"], 2)
    investable = amount - cash_reserve

    # Split between ETFs and stocks
    etf_budget = investable * profile["etf_pct"] / (profile["etf_pct"] + profile["stock_pct"])
    stock_budget = investable * profile["stock_pct"] / (profile["etf_pct"] + profile["stock_pct"])

    etfs = [d for d in market_data if d["ticker"] in HALAL_ETFS]
    stocks = [d for d in market_data if d["ticker"] not in HALAL_ETFS]

    # Score stocks: favor BUY signals, lower P/E, higher confidence
    for s in stocks:
        score = 50
        if s["ema_signal"] == "BUY":
            score += 30
        elif s["ema_signal"] == "SELL":
            score -= 30
        score += min(s["ema_confidence"], 20)
        pe = s.get("forward_pe", 0)
        if 0 < pe < 20:
            score += 15
        elif 20 <= pe < 35:
            score += 5
        elif pe >= 35:
            score -= 10
        s["_score"] = score

    stocks.sort(key=lambda x: x.get("_score", 0), reverse=True)

    # Determine position count
    if amount < 1000:
        max_positions = min(3, len(stocks))
        max_etf_positions = min(1, len(etfs))
    elif amount < 10000:
        max_positions = min(7, len(stocks))
        max_etf_positions = min(2, len(etfs))
    else:
        max_positions = min(12, len(stocks))
        max_etf_positions = min(3, len(etfs))

    allocations = []
    total_invested = 0

    # Allocate ETFs equally
    if etfs and max_etf_positions > 0:
        per_etf = etf_budget / max_etf_positions
        for etf in etfs[:max_etf_positions]:
            shares = int(per_etf // etf["price"])
            if shares > 0:
                cost = round(shares * etf["price"], 2)
                total_invested += cost
                allocations.append(Allocation(
                    ticker=etf["ticker"],
                    company_name=etf["company_name"],
                    sector="Halal ETF",
                    shares=shares,
                    price_per_share=etf["price"],
                    total_cost=cost,
                    portfolio_pct=round(cost / amount * 100, 1),
                    rationale=f"Shariah-compliant ETF — diversified halal exposure",
                ))

    # Allocate stocks by score
    if stocks and max_positions > 0:
        per_stock = stock_budget / max_positions
        max_single = amount * profile["max_single_stock"]

        for stock in stocks[:max_positions]:
            allocation_amt = min(per_stock, max_single)
            shares = int(allocation_amt // stock["price"])
            if shares > 0:
                cost = round(shares * stock["price"], 2)
                total_invested += cost
                signal_note = f"{stock['ema_signal']} signal"
                if stock.get("forward_pe"):
                    signal_note += f", P/E {stock['forward_pe']:.1f}"
                allocations.append(Allocation(
                    ticker=stock["ticker"],
                    company_name=stock["company_name"],
                    sector=stock["sector"],
                    shares=shares,
                    price_per_share=stock["price"],
                    total_cost=cost,
                    portfolio_pct=round(cost / amount * 100, 1),
                    rationale=signal_note,
                ))

    plan.allocations = [asdict(a) for a in allocations]
    plan.invested_amount = round(total_invested, 2)
    plan.cash_reserve = round(amount - total_invested, 2)

    # Sector breakdown
    sectors = {}
    for a in allocations:
        sectors[a.sector] = sectors.get(a.sector, 0) + a.total_cost
    plan.sector_breakdown = {k: round(v / amount * 100, 1) for k, v in sectors.items()}

    # Dividend yield estimate
    yields = [s["dividend_yield"] for s in market_data if s["dividend_yield"] and s["dividend_yield"] > 0]
    plan.expected_dividend_yield = round(sum(yields) / len(yields) * 100, 2) if yields else 0.0

    plan.strategy_summary = (
        f"{risk_profile.title()} allocation of ${amount:,.2f} across "
        f"{len(allocations)} positions. {profile['description']}."
    )

    if amount < 500:
        plan.warnings.append(
            "Small portfolio — limited diversification. Consider ETF-only approach."
        )

    return plan


def _allocate_with_ai(
    amount: float, market_data: list, risk_profile: str
) -> Optional[AllocationPlan]:
    """Use Claude to generate an intelligent allocation plan."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        client = anthropic.Anthropic()
        profile = RISK_PROFILES.get(risk_profile, RISK_PROFILES["moderate"])

        user_message = json.dumps({
            "investment_amount": amount,
            "risk_profile": risk_profile,
            "profile_rules": profile,
            "available_stocks": market_data,
            "instructions": (
                f"Allocate ${amount:,.2f} across these Shariah-compliant stocks. "
                f"Risk profile: {risk_profile} ({profile['description']}). "
                f"Return whole share counts at current prices. "
                f"Ensure diversification across sectors."
            ),
        }, indent=2)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=ALLOCATOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text
        # Extract JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        data = json.loads(text.strip())

        plan = AllocationPlan(
            total_amount=data.get("total_amount", amount),
            cash_reserve=data.get("cash_reserve", 0),
            invested_amount=data.get("invested_amount", 0),
            risk_profile=risk_profile,
            allocations=data.get("allocations", []),
            sector_breakdown=data.get("sector_breakdown", {}),
            strategy_summary=data.get("strategy_summary", ""),
            expected_dividend_yield=data.get("expected_dividend_yield", 0),
            rebalance_frequency=data.get("rebalance_frequency", "quarterly"),
            warnings=data.get("warnings", []),
        )
        return plan

    except Exception as e:
        logger.warning("AI allocation failed, falling back to quantitative: %s", e)
        return None


def recommend_allocation(
    amount: float,
    risk_profile: str = "moderate",
    use_ai: bool = True,
    custom_tickers: list = None,
) -> dict:
    """
    Main entry point: given a dollar amount, return a recommended portfolio allocation.

    Args:
        amount: Dollar amount to invest
        risk_profile: 'conservative', 'moderate', or 'aggressive'
        use_ai: Whether to use Claude AI for allocation (falls back to quantitative)
        custom_tickers: Optional list of tickers to consider (default: full halal universe)

    Returns:
        AllocationPlan as dict with all positions, share counts, and reasoning
    """
    if amount <= 0:
        return {"error": "Investment amount must be positive"}

    if risk_profile not in RISK_PROFILES:
        risk_profile = "moderate"

    # Determine universe
    tickers = custom_tickers or (HALAL_ETFS + HALAL_STOCKS)

    logger.info(
        "Generating allocation for $%s (%s profile, %d candidate tickers)",
        f"{amount:,.2f}", risk_profile, len(tickers),
    )

    # Gather market data
    market_data = _gather_market_data(tickers)

    if not market_data:
        return {"error": "Could not fetch market data for any tickers"}

    # Try AI allocation first, fall back to quantitative
    plan = None
    if use_ai:
        plan = _allocate_with_ai(amount, market_data, risk_profile)

    if plan is None:
        plan = _score_and_allocate_simple(amount, market_data, risk_profile)

    result = plan.to_dict()
    result["market_data_summary"] = {
        d["ticker"]: {
            "price": d["price"],
            "signal": d["ema_signal"],
            "sector": d["sector"],
        }
        for d in market_data
    }

    return result


def format_allocation_report(plan: dict) -> str:
    """Format an allocation plan as a readable text report."""
    lines = []
    lines.append("=" * 60)
    lines.append("🕌 HALAL PORTFOLIO ALLOCATION RECOMMENDATION")
    lines.append("=" * 60)
    lines.append(f"\nInvestment Amount: ${plan.get('total_amount', 0):,.2f}")
    lines.append(f"Risk Profile:      {plan.get('risk_profile', 'moderate').title()}")
    lines.append(f"Cash Reserve:      ${plan.get('cash_reserve', 0):,.2f}")
    lines.append(f"Total Invested:    ${plan.get('invested_amount', 0):,.2f}")
    lines.append("")

    allocations = plan.get("allocations", [])
    if allocations:
        lines.append(f"{'Ticker':<8} {'Shares':>6} {'Price':>10} {'Total':>10} {'%':>6}  Rationale")
        lines.append("-" * 75)
        for a in allocations:
            lines.append(
                f"{a['ticker']:<8} {a['shares']:>6} "
                f"${a['price_per_share']:>8,.2f} "
                f"${a['total_cost']:>8,.2f} "
                f"{a['portfolio_pct']:>5.1f}%  {a.get('rationale', '')}"
            )

    lines.append("")
    sectors = plan.get("sector_breakdown", {})
    if sectors:
        lines.append("Sector Breakdown:")
        for sector, pct in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {sector:<25} {pct:.1f}%")

    lines.append(f"\nExpected Dividend Yield: {plan.get('expected_dividend_yield', 0):.2f}%")
    lines.append(f"Rebalance Frequency:    {plan.get('rebalance_frequency', 'quarterly')}")

    if plan.get("strategy_summary"):
        lines.append(f"\nStrategy: {plan['strategy_summary']}")

    warnings = plan.get("warnings", [])
    if warnings:
        lines.append("\nWarnings:")
        for w in warnings:
            lines.append(f"  ⚠️  {w}")

    lines.append("\n" + "=" * 60)
    lines.append("Disclaimer: This is not financial advice. Consult a qualified")
    lines.append("financial advisor and Islamic scholar before investing.")
    lines.append("=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    amount = float(sys.argv[1]) if len(sys.argv) > 1 else 500.0
    profile = sys.argv[2] if len(sys.argv) > 2 else "moderate"

    print(f"\nGenerating halal portfolio allocation for ${amount:,.2f} ({profile})...\n")

    plan = recommend_allocation(amount, risk_profile=profile, use_ai=True)

    if "error" in plan:
        print(f"Error: {plan['error']}")
    else:
        report = format_allocation_report(plan)
        print(report)
