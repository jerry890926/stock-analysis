"""Plotly 圖表建構"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_chart(df, title, fixed_pct=20, tw_colors=True):
    """
    建立 K 線 + KD 分析圖表。
    tw_colors=True: 紅漲綠跌（台股慣例）
    tw_colors=False: 綠漲紅跌（美股慣例）
    """
    if tw_colors:
        up_color, down_color = "#EF5350", "#26A69A"
    else:
        up_color, down_color = "#26A69A", "#EF5350"

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.06, row_heights=[0.7, 0.3],
        subplot_titles=["60 分鐘 K 線 ＋ 60MA", "KD (60, 3, 3)"],
    )

    # K 線
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="K線",
        increasing_line_color=up_color, decreasing_line_color=down_color,
        increasing_fillcolor=up_color, decreasing_fillcolor=down_color,
    ), row=1, col=1)

    # 60MA
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA60"], name="60MA",
        line=dict(color="#FF9800", width=2),
    ), row=1, col=1)

    # 訊號標記
    signal_markers = [
        ("buy",      "買進",                  "triangle-up",   "#FFD600", "Low",  0.99),
        ("sell",     "賣出",                  "triangle-down", "#F44336", "High", 1.01),
        ("sp_break", "跌破60MA",              "triangle-down", "#7B1FA2", "High", 1.015),
        ("sp_mess",  "籌碼凌亂換標的",         "x",             "#E91E63", "High", 1.02),
        ("sp_kd",    "止漲(KD死叉)",          "diamond",       "#00BCD4", "High", 1.025),
        ("sp_fixed", f"固定停利{fixed_pct}%",  "star",          "#4CAF50", "High", 1.03),
    ]
    for col, label, sym, color, ref_col, mult in signal_markers:
        pts = df[df[col]]
        if not pts.empty:
            fig.add_trace(go.Scatter(
                x=pts.index, y=pts[ref_col] * mult,
                mode="markers", name=label,
                marker=dict(symbol=sym, size=12, color=color,
                            line=dict(width=1, color="#333")),
            ), row=1, col=1)

    # 最近一次買進訊號的停利參考線
    buys = df[df["buy"]]
    if not buys.empty:
        last_entry = buys.iloc[-1]["Close"]
        target = last_entry * (1 + fixed_pct / 100)
        fig.add_hline(
            y=last_entry, row=1, col=1,
            line=dict(color="#FFD600", width=1, dash="dot"),
            annotation_text=f"買入 {last_entry:.1f}",
        )
        fig.add_hline(
            y=target, row=1, col=1,
            line=dict(color="#4CAF50", width=1, dash="dash"),
            annotation_text=f"停利目標 {target:.1f} (+{fixed_pct}%)",
        )

    # KD
    fig.add_trace(go.Scatter(
        x=df.index, y=df["K"], name="K",
        line=dict(color="#2196F3", width=1.5),
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["D"], name="D",
        line=dict(color="#FF5722", width=1.5),
    ), row=2, col=1)

    fig.add_hline(y=50, row=2, col=1,
                  line=dict(color="gray", width=1, dash="dot"),
                  annotation_text="K=50 轉強")
    fig.add_hline(y=60, row=2, col=1,
                  line=dict(color="#FF9800", width=1, dash="dash"),
                  annotation_text="K=60 買進")
    fig.add_hline(y=80, row=2, col=1,
                  line=dict(color="#EF5350", width=1, dash="dot"),
                  annotation_text="K=80 過熱")

    fig.update_layout(
        title=title, height=780,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        margin=dict(l=50, r=30, t=80, b=30),
    )
    fig.update_yaxes(title_text="股價", row=1, col=1)
    fig.update_yaxes(title_text="KD", range=[0, 100], row=2, col=1)

    return fig
