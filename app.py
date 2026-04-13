"""股票分析系統 — 台股 / 美股"""

import streamlit as st
from pathlib import Path

from core.page import render_market_page
from core.portfolio import render_portfolio_page
from core.data import (
    fetch_data_tw, fetch_name_tw, validate_tw,
    fetch_data_us, fetch_name_us, validate_us,
)

APP_DIR = Path(__file__).parent

st.set_page_config(page_title="股票分析系統", page_icon="📈", layout="wide")
st.title("📈 股票分析系統")

# ── 市場切換（側邊欄頂部） ──
with st.sidebar:
    market = st.radio(
        "市場", ["🇹🇼 台股", "🇺🇸 美股", "📦 庫存"],
        horizontal=True, label_visibility="collapsed",
    )

# ── 根據選擇渲染對應頁面 ──
if "台股" in market:
    render_market_page(
        market_key="tw",
        watchlist_path=APP_DIR / "stocks_tw.json",
        fetch_data_fn=fetch_data_tw,
        fetch_name_fn=fetch_name_tw,
        validate_fn=validate_tw,
        tw_colors=True,
    )
elif "美股" in market:
    render_market_page(
        market_key="us",
        watchlist_path=APP_DIR / "stocks_us.json",
        fetch_data_fn=fetch_data_us,
        fetch_name_fn=fetch_name_us,
        validate_fn=validate_us,
        tw_colors=False,
    )
else:
    render_portfolio_page()
