# Halal Trader

**بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ**

Automated Shariah-compliant stock trading system that connects to Charles Schwab, screens stocks for Islamic compliance using AAOIFI standards, and uses a four-agent AI pipeline (powered by Claude) to make intelligent buy/hold/sell decisions with real-time Telegram notifications.

## Features

- **Schwab API Integration** -- OAuth 2.0 auth, portfolio reading, market order placement
- **AAOIFI Shariah Screener** -- 5-screen compliance engine (debt ratio, interest deposits, business activity, purification)
- **Four-Agent AI Pipeline** -- Sheikh Scholar + Finance Professor + Tax Accountant + Orchestrator, all powered by Claude Sonnet
- **Portfolio Allocator** -- Input a dollar amount + risk profile, get a recommended distribution across halal stocks
- **News Intelligence** -- Real-time sentiment scoring via NewsAPI + Claude, with immediate buy/sell triggers
- **Tax Optimization** -- Holding period tracking, wash sale detection, tax-loss harvesting, short/long-term capital gains
- **Zakat Calculator** -- Nisab threshold, 2.5% zakat rate, dividend purification amounts
- **Telegram Notifications** -- Trade alerts with inline approve/reject buttons, daily summaries, compliance alerts
- **Premium React Dashboard** -- Dark theme ("Refined Islamic Fintech"), 8 pages, Framer Motion animations, Recharts

## Dashboard Preview

The dashboard features a premium dark theme with Bloomberg-inspired data density and Islamic design accents:

- **Dashboard** -- KPI cards, portfolio performance chart, agent activity feed
- **Portfolio** -- Holdings table with compliance badges, allocation pie chart, stock detail drawer
- **Screener** -- Run on-demand Shariah screens with animated results and ratio progress bars
- **News Feed** -- Sentiment-scored headlines with bullish/bearish indicators
- **Charts** -- EMA20/EMA50 overlays, crossover signals, volume bars
- **Tax Center** -- YTD gains, loss harvesting opportunities, zakat calculator
- **Compliance** -- Portfolio-wide compliance donut chart, scholarly notes
- **Settings** -- Trading config, tax brackets, Telegram, madhab preferences

## Project Structure

```
halal-trader/
├── backend/
│   ├── schwab_auth.py          # Schwab OAuth 2.0 + account operations
│   ├── shariah_screener.py     # AAOIFI 5-screen compliance engine
│   ├── data_fetcher.py         # Market data, EMA signals, fundamentals
│   ├── news_fetcher.py         # NewsAPI sentiment + Claude scoring
│   ├── tax_engine.py           # Tax liability, wash sales, loss harvesting
│   ├── zakat_calculator.py     # Nisab, zakat, dividend purification
│   ├── trading_bot.py          # Core strategy engine + daily cycle
│   ├── portfolio_manager.py    # Position tracking + sizing
│   ├── portfolio_allocator.py  # Dollar-to-allocation recommender
│   ├── notifier.py             # Telegram bot with approval buttons
│   ├── scheduler.py            # APScheduler daily/weekly/quarterly jobs
│   ├── api_server.py           # FastAPI REST API (11 endpoints)
│   └── agents/
│       ├── sheikh_agent.py     # Islamic finance scholar AI
│       ├── finance_agent.py    # CFA-level quantitative analyst AI
│       ├── accountant_agent.py # Tax attorney AI
│       └── orchestrator.py     # Final decision maker
├── frontend/
│   └── src/
│       ├── App.jsx             # React Router with 8 pages
│       ├── layout/             # TopBar, Sidebar, Layout wrapper
│       ├── pages/              # Dashboard, Portfolio, Screener, etc.
│       ├── components/         # ComplianceBadge, KPICard, EMAChart, etc.
│       ├── hooks/              # usePortfolio, useApi, useMarketHours
│       ├── constants/          # Theme colors
│       └── utils/              # Currency/percentage formatters
├── tests/
│   ├── test_screener.py        # Shariah screener tests
│   ├── test_bot_signals.py     # EMA crossover signal tests
│   ├── test_tax_engine.py      # Tax calculation tests
│   └── test_agents.py          # AI pipeline tests (mocked)
├── data/                       # Trade logs, portfolio state, decisions
├── .env.example                # All configuration variables
├── requirements.txt            # Python dependencies
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Charles Schwab developer account ([developer.schwab.com](https://developer.schwab.com))
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- Telegram bot token (via [@BotFather](https://t.me/BotFather))
- NewsAPI key ([newsapi.org](https://newsapi.org))

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys — at minimum:
#   SCHWAB_APP_KEY, SCHWAB_APP_SECRET
#   ANTHROPIC_API_KEY
#   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
#   NEWS_API_KEY
#   API_SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 2. Install Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 3. Run

```bash
# Terminal 1: Start API server
cd backend
python api_server.py

# Terminal 2: Start frontend dashboard
cd frontend
npm run dev
# Open http://localhost:3000

# Terminal 3: Run trading bot (paper mode)
cd backend
python trading_bot.py --dry-run

# Production: Start scheduler (runs bot + API together)
cd backend
python scheduler.py
```

### 4. Portfolio Allocator

```bash
# CLI: Get allocation for $500 with moderate risk
python backend/portfolio_allocator.py 500 moderate

# API (requires API key):
curl -X POST "http://localhost:8000/api/allocate?amount=500&risk_profile=moderate" \
     -H "X-API-Key: YOUR_API_SECRET_KEY"

# Also available in the dashboard UI on the Portfolio page
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
                  ┌──────────────┐     ┌──────────────┐
                  │ Orchestrator │────>│  React UI    │
                  └──────────────┘     └──────────────┘
```

### Agent Pipeline Flow

1. **Sheikh Agent** evaluates Shariah compliance (HALAL/DOUBTFUL/HARAM)
   - If HARAM: pipeline stops immediately, no further analysis
   - If DOUBTFUL: continues but flags for manual review
2. **Finance Agent** analyzes EMA signals, news sentiment, valuations, macro conditions
3. **Accountant Agent** evaluates tax impact, wash sale risk, holding period optimization
4. **Orchestrator** synthesizes all three opinions and makes the final decision

### Decision Hierarchy

1. Sheikh verdict = HARAM -> **REJECT immediately**
2. Sheikh verdict = DOUBTFUL -> **MANUAL_REVIEW** (user approval required)
3. Finance signal = SELL (confidence > 60%) -> **SELL** (after tax check)
4. Finance signal = BUY + Tax = PROCEED -> **EXECUTE**
5. Tax says WAIT (< 30 days to long-term) -> **HOLD**
6. Default -> **HOLD**

## Shariah Screening (AAOIFI Standards)

The screener applies five financial screens based on AAOIFI Islamic finance standards. The 30% thresholds derive from the hadith of Sa'd ibn Abi Waqqas: *"One third, and one third is much"* (Al-Bukhari #5659).

| Screen | What It Tests | Threshold |
|--------|---------------|-----------|
| Primary Business Activity | Core revenue from halal activities only | 0% tolerance for haram core business |
| Secondary Activity | Incidental haram revenue (e.g., hotel minibars) | < 5% of total revenue |
| Interest-Bearing Debt | Total interest debt / market cap | < 30% of market cap |
| Interest-Bearing Deposits | Cash in interest accounts / total equity | < 30% of equity |
| Purification (Tazkiya) | % of dividends from haram income to donate | Calculate exact amount |

### Auto-Excluded Industries

Conventional banking/insurance, alcohol, gambling/casinos, tobacco, pornography, pork products.

### Pre-Screened Halal Universe

**ETFs:** SPUS, HLAL, MNZL

**Stocks:** NVDA, AAPL, MSFT, GOOGL, AMZN, META, TSLA, ORCL, AMD, QCOM, AVGO, ADBE, JNJ, LLY, ABBV, MRK, HD, AMGN

## Risk Profiles (Portfolio Allocator)

| Profile | ETFs | Stocks | Cash Reserve | Max Single Stock | Best For |
|---------|------|--------|-------------|-----------------|----------|
| Conservative | 60% | 30% | 10% | 10% | Capital preservation |
| Moderate | 40% | 50% | 10% | 15% | Balanced growth |
| Aggressive | 20% | 70% | 10% | 20% | Maximum growth |

## API Endpoints

All POST endpoints require authentication via `X-API-Key` header.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/status` | No | Bot status, auth status, last run time |
| GET | `/api/portfolio` | No | Portfolio value, cash, P&L |
| GET | `/api/holdings` | No | All positions with compliance badges |
| GET | `/api/trades` | No | Last 50 trades from trade log |
| GET | `/api/compliance/{ticker}` | No | On-demand Shariah screen |
| GET | `/api/price/{ticker}` | No | Current price + EMA20 + EMA50 + news score |
| GET | `/api/tax` | No | YTD gains, estimated tax liability |
| GET | `/api/decisions` | No | Last 20 agent pipeline decisions |
| POST | `/api/allocate` | Yes | Portfolio allocation recommendation |
| POST | `/api/bot/toggle` | Yes | Toggle dry run / live trading |
| POST | `/api/approve/{trade_id}` | Yes | Approve a pending trade |

## Security

The system has been through a comprehensive security audit. Key protections:

- **API Authentication** -- Protected endpoints require `X-API-Key` header (HMAC-compared)
- **Input Validation** -- Strict regex on ticker symbols, range checks on quantities
- **Token Security** -- Schwab OAuth token file set to 0600 permissions (owner-only)
- **Prompt Injection Defense** -- News headlines sanitized before AI agent processing
- **AI Output Validation** -- Agent responses validated with field whitelisting
- **CORS Hardening** -- Configurable origins, restricted methods/headers
- **Telegram Verification** -- Chat ID checked on all approval callbacks
- **Error Sanitization** -- Internal details never leaked in API responses
- **Localhost Binding** -- API server binds to 127.0.0.1 by default

### Recommended Production Hardening

- Deploy behind TLS-terminating reverse proxy (nginx/Caddy)
- Pin all dependency versions in requirements.txt
- Add rate limiting via `slowapi`
- Set up file-based locking on `run_daily_cycle()` to prevent race conditions

## Safety Rules

- `DRY_RUN=True` by default -- never auto-changed
- 30 days of paper trading required before going live
- Stop-loss at -8% (auto-executes without approval)
- Minimum 10% cash reserve enforced on every trade
- All decisions logged to `decisions.log` (append-only, never truncated)
- Wash sale detection before any loss realization
- Sheikh Agent runs FIRST -- if HARAM, pipeline stops immediately
- Purification amount calculated on every dividend

## Testing

```bash
# Run all tests
pytest tests/ -v

# Individual test suites
pytest tests/test_screener.py -v      # Shariah compliance screening
pytest tests/test_bot_signals.py -v   # EMA crossover signals
pytest tests/test_tax_engine.py -v    # Tax calculations
pytest tests/test_agents.py -v        # AI agent pipeline (mocked)
```

## Environment Variables

See `.env.example` for all configuration. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `SCHWAB_APP_KEY` | Yes | Schwab API application key |
| `SCHWAB_APP_SECRET` | Yes | Schwab API secret |
| `ANTHROPIC_API_KEY` | Yes | Claude API key for AI agents |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Your personal Telegram chat ID |
| `NEWS_API_KEY` | Yes | NewsAPI.org API key |
| `API_SECRET_KEY` | Yes | Secret for API endpoint authentication |
| `DRY_RUN` | No | Paper trading mode (default: True) |
| `AUTO_EXECUTE` | No | Auto-execute small trades (default: False) |
| `USER_INCOME_BRACKET` | No | Federal tax bracket (default: 22) |
| `USER_STATE` | No | State for tax calculations (default: CA) |

## Scheduled Jobs

| Schedule | Job | Description |
|----------|-----|-------------|
| Mon-Fri 9:35 AM ET | Daily trading cycle | Scan watchlist, run agent pipeline |
| Mon-Fri 4:05 PM ET | Daily summary | Portfolio recap via Telegram |
| Monday 8:00 AM ET | Token check | Warn if Schwab token expiring soon |
| Jan/Apr/Jul/Oct 1st | Compliance rescreen | Full portfolio Shariah re-evaluation |
| March 1st | Zakat reminder | Annual zakat calculation notification |

## Tech Stack

**Backend:** Python 3.10+ | FastAPI | schwab-py | yfinance | Anthropic SDK | APScheduler | python-telegram-bot

**Frontend:** React 18 | Vite | Tailwind CSS | Recharts | Framer Motion | Lucide React | React Router

**AI:** Claude Sonnet (claude-sonnet-4-20250514) via Anthropic API

## Legal & Religious Disclaimers

- This system is for **personal use and educational purposes only**
- It does **not** constitute licensed financial or investment advice
- **Consult a qualified financial advisor** before deploying real funds
- **Consult a qualified Islamic scholar** (sheikh/mufti) for your personal fatwa on stock investing
- Tax estimates are approximate -- **consult a licensed CPA** for your tax situation
- Past performance of any ETF or stock does **not** guarantee future results
- All investments carry **risk of loss** including loss of principal
- The AI agents provide analysis, not rulings -- scholarly human oversight is essential

## License

Private / Personal Use

---

*Built with tawakkul (trust in Allah). May your rizq be halal and barakah.*
