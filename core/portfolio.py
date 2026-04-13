"""庫存管理頁面 — 成本均 + 自動損平價"""

import streamlit as st
import pandas as pd
import yfinance as yf
import json
from pathlib import Path

from core.data import fetch_name_tw, fetch_name_us, load_watchlist, get_all_codes

APP_DIR = Path(__file__).parent.parent
PORTFOLIO_FILE = APP_DIR / "portfolio.json"

# 台股賣出手續費率
TW_SELL_FEE = 0.001425   # 券商手續費 0.1425%
TW_SELL_TAX = 0.003       # 證交稅 0.3%


# ═══════════════════════════════════════════════════════════
# 資料層
# ═══════════════════════════════════════════════════════════

def _load():
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 自動遷移交易紀錄格式 → 簡單格式
        migrated = False
        for h in data:
            if "transactions" in h:
                txns = h.pop("transactions")
                total_shares = 0
                total_cost = 0.0
                for t in txns:
                    if t["type"] == "buy":
                        total_shares += t["shares"]
                        total_cost += t["shares"] * t["price"]
                    else:
                        total_shares -= t["shares"]
                h["shares"] = total_shares
                h["avg_cost"] = round(total_cost / total_shares, 2) if total_shares > 0 else 0
                migrated = True
        if migrated:
            # 移除已清倉的
            data = [h for h in data if h.get("shares", 0) > 0]
            with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    return []


def _save(holdings):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(holdings, f, ensure_ascii=False, indent=2)


def _get_name(code, market):
    return fetch_name_tw(code) if market == "tw" else fetch_name_us(code)


def _breakeven(avg_cost, market):
    """從成本均計算損平價（含賣出手續費）"""
    if market == "tw":
        return avg_cost / (1 - TW_SELL_FEE - TW_SELL_TAX)
    return avg_cost  # 美股免手續費


def _net_sell_price(price, market):
    """賣出後實際拿到的每股淨額"""
    if market == "tw":
        return price * (1 - TW_SELL_FEE - TW_SELL_TAX)
    return price


def _get_watchlist_codes(market):
    """從自選股清單取得股票代碼供建議"""
    path = APP_DIR / f"stocks_{market}.json"
    data = load_watchlist(path)
    return get_all_codes(data)


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_price(code, market):
    """取得最新收盤價"""
    if market == "tw":
        for sfx in (".TW", ".TWO"):
            try:
                df = yf.Ticker(f"{code}{sfx}").history(period="5d")
                if not df.empty:
                    return float(df["Close"].iloc[-1])
            except Exception:
                continue
    else:
        try:
            df = yf.Ticker(code).history(period="5d")
            if not df.empty:
                return float(df["Close"].iloc[-1])
        except Exception:
            pass
    return None


# ═══════════════════════════════════════════════════════════
# 頁面渲染
# ═══════════════════════════════════════════════════════════

def render_portfolio_page():
    holdings = _load()

    # ── 側邊欄 ──
    with st.sidebar:
        # ── 新增庫存 ──
        with st.expander("➕ 新增庫存"):
            mkt = st.radio(
                "市場", ["tw", "us"], horizontal=True, key="pf_mkt",
                format_func=lambda x: "🇹🇼 台股" if x == "tw" else "🇺🇸 美股",
            )

            # 自選股建議
            wl_codes = _get_watchlist_codes(mkt)
            options = ["手動輸入"] + [
                f"{c} {_get_name(c, mkt)}" for c in wl_codes
            ]
            selected = st.selectbox("從自選股選擇", options, key="pf_wl_sel")

            if selected == "手動輸入":
                code = st.text_input("股票代碼", key="pf_code")
            else:
                code = selected.split(" ")[0]
                st.caption(f"已選：{selected}")

            shares = st.number_input("持股數量", min_value=1, step=1, value=1000, key="pf_shares")
            avg_cost = st.number_input("成本均", min_value=0.01, step=0.01, value=100.0, key="pf_cost")

            if st.button("加入庫存", use_container_width=True, key="pf_add") and code:
                code = code.strip().upper() if mkt == "us" else code.strip()
                exists = any(h["code"] == code and h["market"] == mkt for h in holdings)
                if exists:
                    st.warning(f"{code} 已在庫存中，請用編輯功能修改")
                else:
                    holdings.append({
                        "code": code, "market": mkt,
                        "shares": int(shares), "avg_cost": float(avg_cost),
                    })
                    _save(holdings)
                    st.success(f"已新增 {code} {_get_name(code, mkt)}")
                    st.rerun()

        # ── 編輯庫存 ──
        if holdings:
            with st.expander("✏️ 編輯庫存"):
                opts = {
                    f"{h['code']} {_get_name(h['code'], h['market'])} "
                    f"({'台股' if h['market']=='tw' else '美股'})": i
                    for i, h in enumerate(holdings)
                }
                sel = st.selectbox("選擇", list(opts.keys()), key="pf_edit_sel",
                                   label_visibility="collapsed")
                idx = opts[sel]
                h = holdings[idx]
                new_shares = st.number_input("持股數量", value=h["shares"], min_value=0,
                                             step=1, key="pf_edit_shares")
                new_cost = st.number_input("成本均", value=h["avg_cost"], min_value=0.0,
                                           step=0.01, key="pf_edit_cost")
                if st.button("更新", use_container_width=True, key="pf_edit_btn"):
                    holdings[idx]["shares"] = int(new_shares)
                    holdings[idx]["avg_cost"] = float(new_cost)
                    _save(holdings)
                    st.success("已更新")
                    st.rerun()

            # ── 移除庫存 ──
            with st.expander("➖ 移除庫存"):
                rm_opts = {
                    f"{h['code']} {_get_name(h['code'], h['market'])} "
                    f"({'台股' if h['market']=='tw' else '美股'})": i
                    for i, h in enumerate(holdings)
                }
                rm_sel = st.selectbox("選擇", list(rm_opts.keys()), key="pf_rm_sel",
                                      label_visibility="collapsed")
                if st.button("移除", use_container_width=True, key="pf_rm_btn"):
                    holdings.pop(rm_opts[rm_sel])
                    _save(holdings)
                    st.rerun()

    # ── 主頁面 ──
    if not holdings:
        st.info("尚無庫存資料，請在側邊欄新增持股")
        return

    rows = []
    total_cost = 0.0
    total_value = 0.0
    has_price_error = False

    progress = st.progress(0, text="載入庫存資料 ...")
    for i, h in enumerate(holdings):
        progress.progress((i + 1) / len(holdings))
        code, market = h["code"], h["market"]
        shares, avg_cost = h["shares"], h["avg_cost"]
        name = _get_name(code, market)
        price = _fetch_price(code, market)
        be = _breakeven(avg_cost, market)
        cost = shares * avg_cost
        total_cost += cost

        if price is not None and shares > 0:
            net_price = _net_sell_price(price, market)
            pl = shares * (net_price - avg_cost)
            total_value += shares * net_price
            pl_pct = (net_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
            rows.append({
                "市場": "🇹🇼" if market == "tw" else "🇺🇸",
                "代碼": code,
                "名稱": name,
                "持股": shares,
                "成本均": round(avg_cost, 2),
                "損平價": round(be, 2),
                "現價": round(price, 2),
                "成本": round(cost),
                "市值": round(shares * price),
                "損益": round(pl),
                "報酬%": round(pl_pct, 1),
            })
        else:
            has_price_error = True
            rows.append({
                "市場": "🇹🇼" if market == "tw" else "🇺🇸",
                "代碼": code,
                "名稱": name,
                "持股": shares,
                "成本均": round(avg_cost, 2),
                "損平價": round(be, 2),
                "現價": None,
                "成本": round(cost),
                "市值": None,
                "損益": None,
                "報酬%": None,
            })
    progress.empty()

    # 總覽指標
    total_pl = total_value - total_cost
    total_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("總成本", f"{total_cost:,.0f}")
    c2.metric("總市值（扣手續費）", f"{total_value:,.0f}")
    c3.metric("總損益", f"{total_pl:+,.0f}", delta=f"{total_pct:+.1f}%")
    c4.metric("持股檔數", f"{len(holdings)}")

    st.divider()

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("報酬%", ascending=False, na_position="last")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "持股": st.column_config.NumberColumn(format="%d"),
                "成本均": st.column_config.NumberColumn(format="%.2f"),
                "損平價": st.column_config.NumberColumn(format="%.2f"),
                "現價": st.column_config.NumberColumn(format="%.2f"),
                "成本": st.column_config.NumberColumn(format="%d"),
                "市值": st.column_config.NumberColumn(format="%d"),
                "損益": st.column_config.NumberColumn(format="%d"),
                "報酬%": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    if has_price_error:
        st.caption("⚠️ 部分股票無法取得即時價格")
