# CLAUDE.md — Project Context for Claude Code Sessions

> **NOTE:** This file is a living document. Update it as the project evolves.
> Last updated: 2026-03-17.

## Project Overview

Halal Trader — Automated Shariah-compliant stock trading SaaS. Connects to
Charles Schwab, screens stocks against AAOIFI Islamic finance standards, uses a
four-agent AI pipeline (Sheikh, Finance, Accountant, Orchestrator) powered by
Claude, and delivers a premium React dashboard.

## Local Development Setup (Free, No API Keys)

### Prerequisites

- Python 3.11+, Node.js 18+, Git

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

### Minimal .env (backend/.env)

```env
DRY_RUN=true
DATABASE_URL=sqlite+aiosqlite:///./test.db
JWT_SECRET=change-me-before-production
# ANTHROPIC_API_KEY=sk-ant-...   # optional: enables AI agents
```

### Quick Smoke Tests (no API keys needed)

```bash
cd backend
python shariah_screener.py       # AAOIFI 5-screen compliance test
python zakat_calculator.py       # Zakat + purification self-test
```

### Run Backend API

```bash
cd backend
uvicorn main:app --reload --port 8000   # Swagger: http://localhost:8000/docs
```

### Run Trading Bot (paper mode, needs Schwab creds)

```bash
cd backend
python trading_bot.py --dry-run
```

### Run Tests

```bash
pytest tests/ -v
```

## Key Architecture Decisions

### Shariah Compliance Gate

- **Only HALAL proceeds to auto-execution.** Both HARAM and DOUBTFUL are
  hard-gated in code (not just prompt instructions).
- Sheikh agent failure defaults to **HARAM** per *istishab al-asl* (unknown =
  impermissible until proven halal).
- All five AAOIFI screens use **33.33% (one-third)** threshold with **market
  cap** as denominator (per AAOIFI SS 21, hadith of Sa'd — Bukhari #2742).

### Agent Pipeline

1. Sheikh Agent (Haiku) — Shariah compliance verdict
2. Finance Agent (Sonnet) — quantitative analysis
3. Accountant Agent (Sonnet) — tax optimization
4. Orchestrator (Sonnet) — final decision synthesis

### Screening Thresholds (AAOIFI)

| Screen | Denominator | Fail Threshold | Warn Threshold |
|--------|-------------|----------------|----------------|
| Debt ratio | Market cap | > 33.33% | > 30% |
| Cash/deposits | Market cap | > 33.33% | > 30% |
| Receivables | Market cap | > 33.33% | > 30% |
| Haram revenue | Total revenue | > 5% | > 0% |
| Purification | Fraction (0.0–1.0) | N/A (calculated) | N/A |

### Purification

- Uses **interest income** (haram earnings), NOT interest expense.
- Stored as a **fraction (0.0–1.0)** across all modules (screener + zakat
  calculator). The zakat_calculator validates `0 <= pct <= 1`.

## Project Structure

```
backend/
  shariah_screener.py     — AAOIFI 5-screen compliance engine
  trading_bot.py          — Core strategy engine + daily cycle
  zakat_calculator.py     — Nisab, zakat, dividend purification
  data_fetcher.py         — Market data, EMA signals, fundamentals
  news_fetcher.py         — NewsAPI sentiment + Claude scoring
  tax_engine.py           — Tax liability, wash sales, loss harvesting
  portfolio_manager.py    — Position tracking + sizing
  notifier.py             — Telegram bot with approval buttons
  main.py                 — FastAPI app entry point
  agents/
    sheikh_agent.py       — Islamic finance scholar AI (Haiku)
    finance_agent.py      — CFA-level quantitative analyst AI (Sonnet)
    accountant_agent.py   — Tax attorney AI (Sonnet)
    orchestrator.py       — Final decision maker (Sonnet)
    base_agent.py         — Shared Anthropic API call helper
    batch_screener.py     — Batch ticker screening
  auth/                   — JWT auth + dependencies
  payments/               — Stripe subscription router
  screener/               — Screener API endpoint (30-day cache)
  middleware/              — AI rate limiter

frontend/src/
  pages/                  — Landing, Dashboard, Portfolio, Screener, etc.
  components/             — ComplianceBadge, KPICard, EMAChart, etc.
  hooks/                  — usePortfolio, useApi, useMarketHours
  layout/                 — TopBar, Sidebar, Layout wrapper

tests/                    — pytest test suites
data/                     — Trade logs, portfolio state, decisions
```

## Known Issues / TODO

- Secondary activity screen (5% haram revenue) is a placeholder — needs a real
  revenue segmentation data source (Zoya API or FinancialModelingPrep).
- ETFs (SPUS, HLAL, MNZL) are screened at fund level, not at holdings level.
- No quarterly re-screening scheduler for existing holdings.
- No formal wakalah (agency) consent flow for auto-execution.
- No proactive purification notification when dividends are received.
- No Shariah Supervisory Board engaged for independent certification.
- Landing page "15-25% Target Returns" claim should be removed (misleading).
- Batch screener sends only ticker to Sheikh agent (no financial data).

## API Keys Reference

| Key | Required For | Free Tier |
|-----|-------------|-----------|
| `ANTHROPIC_API_KEY` | AI agents | Trial credits at console.anthropic.com |
| `SCHWAB_APP_KEY` + `SECRET` | Trading | Free developer account |
| `TELEGRAM_BOT_TOKEN` | Notifications | Free via @BotFather |
| `NEWS_API_KEY` | Sentiment | Free tier at newsapi.org |
| `STRIPE_SECRET_KEY` | Payments | Test mode is free |
| `ZOYA_API_KEY` | Enriched screening | Optional |
| `JWT_SECRET` | Auth | Generate locally |

## Commands Cheat Sheet

```bash
# Screener smoke test
python backend/shariah_screener.py

# Zakat smoke test
python backend/zakat_calculator.py

# Backend API
cd backend && uvicorn main:app --reload --port 8000

# Frontend dev server
cd frontend && npm run dev

# Trading bot (paper)
cd backend && python trading_bot.py --dry-run

# Go-live readiness check
cd backend && python trading_bot.py --check-readiness

# Tests
pytest tests/ -v
```
