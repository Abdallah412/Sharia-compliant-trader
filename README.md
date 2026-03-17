# Halal Trader

**بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ**

Automated Shariah-compliant stock trading system that connects to Charles Schwab, screens stocks for Islamic compliance using AAOIFI standards, and uses a four-agent AI pipeline to make intelligent buy/hold/sell decisions.

## Features

- **Schwab API Integration** — OAuth 2.0 auth, portfolio reading, order placement
- **AAOIFI Shariah Screener** — 5-screen compliance engine (debt ratio, interest deposits, business activity, purification)
- **Four-Agent AI Pipeline** — Sheikh Scholar + Finance Professor + Tax Accountant + Orchestrator, all powered by Claude
- **Portfolio Allocator** — Input a dollar amount, get a recommended distribution across halal stocks with risk profiles (conservative/moderate/aggressive)
- **News Intelligence** — Real-time sentiment scoring with immediate action triggers
- **Tax Optimization** — Holding period tracking, wash sale detection, loss harvesting, zakat calculation
- **Telegram Notifications** — Trade alerts with approve/reject buttons, daily summaries, compliance alerts
- **React Dashboard** — Live portfolio view, holdings table, price charts with EMA overlays, trade log

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Charles Schwab developer account (developer.schwab.com)
- Anthropic API key
- Telegram bot token (via @BotFather)
- NewsAPI key

### Setup

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys

# Backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### Run

```bash
# Start API server
cd backend
python api_server.py

# Start frontend (separate terminal)
cd frontend
npm run dev

# Run trading bot (dry run)
cd backend
python trading_bot.py --dry-run

# Start scheduler (production)
cd backend
python scheduler.py
```

### Portfolio Allocator

```bash
# CLI: Get allocation for $500 with moderate risk
python backend/portfolio_allocator.py 500 moderate

# API: POST /api/allocate?amount=500&risk_profile=moderate
# Also available in the dashboard UI
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Schwab API  │────>│  Trading Bot  │────>│  Telegram    │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              v            v            v
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │  Sheikh   │  │ Finance  │  │Accountant│
      │  Agent    │  │  Agent   │  │  Agent   │
      └────┬─────┘  └────┬─────┘  └────┬─────┘
           └──────────────┼──────────────┘
                          v
                  ┌──────────────┐
                  │ Orchestrator │
                  └──────────────┘
```

## Decision Hierarchy

1. Sheikh verdict = HARAM -> **REJECT immediately**
2. Sheikh verdict = DOUBTFUL -> **MANUAL_REVIEW** (user approval required)
3. Finance signal = SELL (confidence > 60%) -> **SELL** (after tax check)
4. Finance signal = BUY + Tax = PROCEED -> **EXECUTE**
5. Tax says WAIT (< 30 days to long-term) -> **HOLD**
6. Default -> **HOLD**

## Shariah Screening (AAOIFI Standards)

| Screen | Threshold |
|--------|-----------|
| Primary business activity | 0% haram core business |
| Secondary haram revenue | < 5% of total revenue |
| Interest-bearing debt | < 30% of market cap |
| Interest-bearing deposits | < 30% of equity |
| Purification (tazkiya) | Calculate exact charity amount |

## Risk Profiles (Portfolio Allocator)

| Profile | ETFs | Stocks | Cash | Max Single Stock |
|---------|------|--------|------|-----------------|
| Conservative | 60% | 30% | 10% | 10% |
| Moderate | 40% | 50% | 10% | 15% |
| Aggressive | 20% | 70% | 10% | 20% |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Bot status, auth, last run |
| GET | `/api/portfolio` | Portfolio value, cash, P&L |
| GET | `/api/holdings` | All positions with compliance badges |
| GET | `/api/trades` | Last 50 trades |
| GET | `/api/compliance/{ticker}` | On-demand Shariah screen |
| GET | `/api/price/{ticker}` | Price + EMA + news score |
| GET | `/api/tax` | YTD gains, estimated tax |
| GET | `/api/decisions` | Last 20 agent decisions |
| POST | `/api/allocate` | Portfolio allocation recommendation |
| POST | `/api/bot/toggle` | Toggle dry run / live trading |
| POST | `/api/approve/{trade_id}` | Approve pending trade |

## Testing

```bash
pytest tests/ -v
```

## Safety

- `DRY_RUN=True` by default -- never auto-changed
- 30 days of paper trading required before going live
- Stop-loss at -8% (auto-executes, no approval needed)
- Minimum 10% cash reserve enforced
- All decisions logged to `decisions.log` (append-only)
- Wash sale detection before any loss realization

## Legal & Religious Disclaimers

- This system is for personal use and educational purposes only
- It does not constitute licensed financial or investment advice
- Consult a qualified financial advisor before deploying real funds
- Consult a qualified Islamic scholar (sheikh) for your personal fatwa on stock investing
- Tax estimates are approximate -- consult a licensed CPA for your tax situation
- Past performance of any ETF or stock does not guarantee future results
- All investments carry risk of loss including loss of principal

## License

Private / Personal Use
