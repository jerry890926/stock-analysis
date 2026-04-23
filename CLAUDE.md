# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stock analysis system for Taiwan and US markets — a 60-minute chart trading methodology using 60MA + KD(60,3,3) indicators. Built with Streamlit, supports watchlists, technical analysis, and portfolio tracking.

## Running the App

```bash
source ~/Desktop/python_venv/python3_env/bin/activate
streamlit run app.py
```

App runs at http://localhost:8501. No requirements.txt — dependencies (streamlit, yfinance, pandas, numpy, plotly, twstock) are installed in `~/Desktop/python_venv/python3_env/`.

## Architecture

`app.py` is the entry point with market switching (台股 / 美股 / 庫存). Core logic lives in `core/`:

- **core/data.py** — Watchlist JSON I/O, stock data fetching, name lookup. TW uses `twstock.codes` for names and validates against its local DB. US uses `yf.Ticker().info` (cached 24h). Both fetch 60-min OHLC via yfinance (TW tries `.TW` then `.TWO` suffix).
- **core/analysis.py** — `calc_kd()` (Taiwan-style KD stochastic), `analyze()` (MA60 + signals), `current_status()` / `signal_label()`. Signal columns: `buy`, `sell`, `sp_break`, `sp_mess`, `sp_kd`, `sp_fixed`.
- **core/chart.py** — `build_chart()` creates 2-row Plotly figure (candlestick+60MA / KD). Accepts `tw_colors` flag (red=up for TW, green=up for US).
- **core/page.py** — `render_market_page()` is the shared UI renderer for both markets. All widget keys are namespaced with `market_key` prefix (`tw_` / `us_`). Page navigation uses `st.session_state["{market_key}_subpage"]`.
- **core/portfolio.py** — `render_portfolio_page()` for inventory management. Simple model (shares + avg_cost). Auto-calculates breakeven price (損平價) factoring in TW sell-side fees (手續費 0.1425% + 證交稅 0.3%). Supports watchlist stock suggestions when adding holdings.

## Data Files

- `stocks_tw.json` / `stocks_us.json` — Watchlists. Keys = group names, values = arrays of stock codes.
- `portfolio.json` — Portfolio holdings (gitignored). Each entry: `{code, market, shares, avg_cost}`.
- `進場與停利策略.md` — Strategy documentation.

## Key Conventions

- **Language**: All UI text in Traditional Chinese (繁體中文).
- **Candlestick colors**: TW = red up / green down. US = green up / red down. Controlled by `tw_colors` param.
- **TW stock codes**: Numeric (e.g. "2330"). yfinance needs `.TW` (TWSE) or `.TWO` (OTC) suffix — `fetch_data_tw` tries both.
- **US stock codes**: Uppercase tickers. Index symbols use `^` prefix (e.g. `^GSPC`).
- **Caching**: `@st.cache_data(ttl=300)` for price data, `ttl=86400` for US stock names.
- **Signal states**: 🔥 過熱區 (price > 60MA & K > 80) / 🟢 買進區 (price > 60MA & 60 < K ≤ 80) / 🟡 轉強中 (price > 60MA & 50 < K ≤ 60) / ⚪ 觀望 (price > 60MA & K ≤ 50) / 🟠 轉弱中 (price < 60MA & K ≥ 50) / 🔴 賣出區 (price < 60MA & K < 50).
