"""共用頁面渲染器 — 台股與美股共用同一套 UI 邏輯"""

import streamlit as st
import pandas as pd

from core.analysis import analyze, current_status, signal_label
from core.chart import build_chart
from core.data import load_watchlist, save_watchlist, get_all_codes
from core.institutional import fetch_institutional, fetch_margin


def render_market_page(market_key, watchlist_path, fetch_data_fn, fetch_name_fn,
                       validate_fn, tw_colors=True):
    """
    渲染完整的市場分析頁面（側邊欄 + 主頁面）。

    Args:
        market_key:     "tw" 或 "us"，用於 session_state key 命名空間
        watchlist_path: JSON 清單檔路徑
        fetch_data_fn:  function(code, period) -> DataFrame
        fetch_name_fn:  function(code) -> str
        validate_fn:    function(code) -> bool
        tw_colors:      True=紅漲綠跌（台股），False=綠漲紅跌（美股）
    """
    page_key = f"{market_key}_subpage"
    if page_key not in st.session_state:
        st.session_state[page_key] = "home"

    # ═══ 側邊欄 ═══
    with st.sidebar:
        data = load_watchlist(watchlist_path)
        groups = list(data.keys())

        # ── 新增股票 ──
        with st.expander("➕ 新增股票"):
            if not groups:
                st.caption("請先建立群組")
            else:
                add_group = st.selectbox("加入群組", groups, key=f"{market_key}_add_grp")
                add_code = st.text_input("股票代碼", key=f"{market_key}_add_code")
                if st.button("加入", use_container_width=True, key=f"{market_key}_add_btn") and add_code:
                    code = add_code.strip().upper() if market_key == "us" else add_code.strip()
                    if code in data[add_group]:
                        st.warning("此代碼已在該群組中")
                    elif not validate_fn(code):
                        st.error(f"找不到代碼 {code}")
                    else:
                        data[add_group].append(code)
                        save_watchlist(watchlist_path, data)
                        st.success(f"已新增 {code} {fetch_name_fn(code)} → {add_group}")
                        st.rerun()

        # ── 移除股票 ──
        all_codes = get_all_codes(data)
        if all_codes:
            with st.expander("➖ 移除股票"):
                rm_opts = {f"{c} {fetch_name_fn(c)}": c for c in all_codes}
                rm_sel = st.selectbox("選擇股票", list(rm_opts.keys()),
                                      key=f"{market_key}_rm_sel", label_visibility="collapsed")
                if st.button("移除", use_container_width=True, key=f"{market_key}_rm_btn"):
                    code = rm_opts[rm_sel]
                    for g in data:
                        if code in data[g]:
                            data[g].remove(code)
                    save_watchlist(watchlist_path, data)
                    st.rerun()

        # ── 群組管理 ──
        with st.expander("📁 管理群組"):
            new_grp = st.text_input("新群組名稱", key=f"{market_key}_new_grp")
            if st.button("建立群組", use_container_width=True, key=f"{market_key}_grp_btn") and new_grp:
                new_grp = new_grp.strip()
                if new_grp in data:
                    st.warning("此群組已存在")
                else:
                    data[new_grp] = []
                    save_watchlist(watchlist_path, data)
                    st.rerun()
            if groups:
                st.divider()
                del_grp = st.selectbox("刪除群組", groups, key=f"{market_key}_del_grp")
                if st.button("刪除群組", use_container_width=True, key=f"{market_key}_del_btn"):
                    if data[del_grp]:
                        st.warning(f"「{del_grp}」內還有 {len(data[del_grp])} 檔股票，請先移除")
                    else:
                        del data[del_grp]
                        save_watchlist(watchlist_path, data)
                        st.rerun()

        st.divider()

        # ── 分析設定 ──
        all_codes = get_all_codes(data)
        if not all_codes:
            st.info("請先新增股票")
            st.stop()

        labels = {f"{c} {fetch_name_fn(c)}": c for c in all_codes}
        sel_label = st.selectbox("分析標的", list(labels.keys()), key=f"{market_key}_sel")
        sel_code = labels[sel_label]

        if st.button("前往個股分析", use_container_width=True, key=f"{market_key}_goto"):
            st.session_state[page_key] = "analysis"
            st.rerun()

        period = st.select_slider(
            "資料期間", ["1mo", "3mo", "6mo"], value="3mo",
            format_func=lambda x: {"1mo": "1 個月", "3mo": "3 個月", "6mo": "6 個月"}[x],
            key=f"{market_key}_period",
        )
        fixed_pct = st.slider("固定停利目標 (%)", 5, 50, 20, 5, key=f"{market_key}_pct")

        st.divider()
        with st.expander("📖 策略速查"):
            st.markdown("""
**買進** 股價 > 60MA 且 K > 60 → 🟢\n
**賣出** 股價 < 60MA 且 K < 50 → 🔴\n
**四大停利**
1. 固定停利（自訂 %）
2. 止漲訊號（KD 高檔死叉）
3. 籌碼凌亂換標的（爆量長上影/長黑K）
4. 跌破 60MA
            """)

    # ═══ 主頁面 ═══

    # 頁面切換
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 自選股", use_container_width=True,
                     type="primary" if st.session_state[page_key] == "home" else "secondary",
                     key=f"{market_key}_nav_home"):
            st.session_state[page_key] = "home"
            st.rerun()
    with col2:
        if st.button("📊 個股分析", use_container_width=True,
                     type="primary" if st.session_state[page_key] == "analysis" else "secondary",
                     key=f"{market_key}_nav_analysis"):
            st.session_state[page_key] = "analysis"
            st.rerun()
    st.divider()

    # 內容
    if st.session_state[page_key] == "home":
        _render_home(data, fetch_data_fn, fetch_name_fn, fixed_pct, market_key)
    else:
        _render_analysis(sel_code, period, fixed_pct, fetch_data_fn, fetch_name_fn, tw_colors)


# ─── 子頁面 ──────────────────────────────────────────────

def _render_home(data, fetch_data_fn, fetch_name_fn, fixed_pct, market_key):
    """自選股總覽"""
    for group_name, codes in data.items():
        if not codes:
            continue
        st.subheader(group_name)
        rows = []
        progress = st.progress(0, text=f"載入 {group_name} ...")
        for i, code in enumerate(codes):
            progress.progress((i + 1) / len(codes))
            name = fetch_name_fn(code)
            try:
                raw = fetch_data_fn(code, "3mo")
                if raw.empty:
                    rows.append({"代碼": code, "名稱": name,
                                 "現價": "-", "60MA": "-", "K": "-", "D": "-",
                                 "訊號": "⚠️ 無資料"})
                    continue
                d = analyze(raw, fixed_pct)
                s = current_status(d)
                rows.append({
                    "代碼": code, "名稱": name,
                    "現價": f"{s['close']:.2f}", "60MA": f"{s['ma60']:.2f}",
                    "K": f"{s['k']:.1f}", "D": f"{s['d']:.1f}",
                    "訊號": signal_label(s),
                })
            except Exception:
                rows.append({"代碼": code, "名稱": name,
                             "現價": "-", "60MA": "-", "K": "-", "D": "-",
                             "訊號": "⚠️ 錯誤"})
        progress.empty()
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_analysis(sel_code, period, fixed_pct, fetch_data_fn, fetch_name_fn, tw_colors):
    """個股分析"""
    display_name = fetch_name_fn(sel_code)
    st.markdown(f"### {sel_code} {display_name}")

    with st.spinner(f"載入 {sel_code} {display_name} ..."):
        raw = fetch_data_fn(sel_code, period)

    if raw.empty:
        st.error(f"無法取得 {sel_code} 的 60 分鐘資料，請確認股票代碼是否正確。")
        return

    df = analyze(raw, fixed_pct)
    s = current_status(df)

    # 狀態面板
    cols = st.columns(5)
    cols[0].metric("現價", f"{s['close']:.2f}")
    cols[1].metric("60MA", f"{s['ma60']:.2f}")
    cols[2].metric("K", f"{s['k']:.1f}")
    cols[3].metric("D", f"{s['d']:.1f}")
    cols[4].markdown(f"### {signal_label(s)}")

    checks = [
        f"{'✅' if s['above_ma'] else '❌'} 股價 {'>' if s['above_ma'] else '<'} 60MA",
        f"{'✅' if s['k50'] else '❌'} K {'>' if s['k50'] else '<'} 50（轉強）",
        f"{'✅' if s['k60'] else '❌'} K {'>' if s['k60'] else '<'} 60（買進）",
    ]
    st.markdown(" ｜ ".join(checks))

    chart_title = f"{sel_code} {display_name} — 分析"
    st.plotly_chart(build_chart(df, chart_title, fixed_pct, tw_colors), use_container_width=True)

    # 法人進出 / 資券變化（台股限定）
    if tw_colors:
        st.subheader("每日籌碼")
        tab1, tab2 = st.tabs(["法人進出", "資券變化"])

        with tab1:
            with st.spinner("載入法人進出資料..."):
                inst_df = fetch_institutional(sel_code)
            if not inst_df.empty:
                st.dataframe(
                    inst_df, use_container_width=True, hide_index=True,
                    column_config={
                        "外資": st.column_config.NumberColumn(format="%d 張"),
                        "投信": st.column_config.NumberColumn(format="%d 張"),
                        "自營商": st.column_config.NumberColumn(format="%d 張"),
                        "合計": st.column_config.NumberColumn(format="%d 張"),
                    },
                )
            else:
                st.info("暫時無法取得法人進出資料")

        with tab2:
            with st.spinner("載入資券變化資料..."):
                margin_df = fetch_margin(sel_code)
            if not margin_df.empty:
                st.dataframe(
                    margin_df, use_container_width=True, hide_index=True,
                    column_config={
                        "融資餘額": st.column_config.NumberColumn(format="%d"),
                        "融資增減": st.column_config.NumberColumn(format="%+d"),
                        "融券餘額": st.column_config.NumberColumn(format="%d"),
                        "融券增減": st.column_config.NumberColumn(format="%+d"),
                        "資券互抵": st.column_config.NumberColumn(format="%d"),
                    },
                )
            else:
                st.info("暫時無法取得資券變化資料")

    # 訊號紀錄
    st.subheader("訊號紀錄")
    sig_map = [
        ("buy", "🟢 買進"), ("sell", "🔴 賣出"),
        ("sp_break", "🔴 跌破60MA"), ("sp_mess", "⚠️ 籌碼凌亂換標的"),
        ("sp_kd", "🟠 止漲(KD死叉)"), ("sp_fixed", f"💰 固定停利{fixed_pct}%"),
    ]
    records = []
    for idx, row in df.iterrows():
        for col_name, label in sig_map:
            if row[col_name]:
                records.append({
                    "時間": idx, "訊號": label,
                    "收盤": f"{row['Close']:.2f}",
                    "K": f"{row['K']:.1f}", "D": f"{row['D']:.1f}",
                })
    if records:
        rec_df = pd.DataFrame(records).sort_values("時間", ascending=False).head(30)
        st.dataframe(rec_df, use_container_width=True, hide_index=True)
    else:
        st.info("此期間內無訊號產生")
