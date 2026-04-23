"""技術指標計算與訊號判斷"""

import pandas as pd
import numpy as np


def calc_kd(close, high, low, n=60, kp=3, dp=3):
    """KD 隨機指標（台灣慣用算法）"""
    lo = low.rolling(n, min_periods=1).min()
    hi = high.rolling(n, min_periods=1).max()
    denom = hi - lo
    rsv = np.where(denom > 0, (close.values - lo.values) / denom.values * 100, 50)

    k = np.empty(len(close))
    d = np.empty(len(close))
    k[0] = d[0] = 50.0
    kw, dw = 1.0 / kp, 1.0 / dp
    for i in range(1, len(close)):
        k[i] = (1 - kw) * k[i - 1] + kw * rsv[i]
        d[i] = (1 - dw) * d[i - 1] + dw * k[i]
    return pd.Series(k, index=close.index), pd.Series(d, index=close.index)


def analyze(df, fixed_pct=20):
    """執行分析，回傳含訊號的 DataFrame"""
    df = df.copy()

    df["MA60"] = df["Close"].rolling(60, min_periods=1).mean()
    df["K"], df["D"] = calc_kd(df["Close"], df["High"], df["Low"])

    # 買進訊號：站上 60MA 且 K > 60
    buy_cond = (df["Close"] > df["MA60"]) & (df["K"] > 60)
    df["buy"] = buy_cond & ~buy_cond.shift(1, fill_value=False)

    # 賣出訊號：跌破 60MA 且 K < 50
    sell_cond = (df["Close"] < df["MA60"]) & (df["K"] < 50)
    df["sell"] = sell_cond & ~sell_cond.shift(1, fill_value=False)

    # 停利 1：跌破 60MA
    df["sp_break"] = (
        (df["Close"] < df["MA60"])
        & (df["Close"].shift(1) >= df["MA60"].shift(1))
    )

    # 停利 2：籌碼凌亂換標的（爆量 + 長上影線 or 長黑 K）
    avg_vol = df["Volume"].rolling(20, min_periods=1).mean()
    rng = (df["High"] - df["Low"]).replace(0, np.nan)
    upper_shadow = df["High"] - df[["Open", "Close"]].max(axis=1)
    body = (df["Close"] - df["Open"]).abs()
    long_upper = (upper_shadow / rng) > 0.5
    big_black = (df["Close"] < df["Open"]) & ((body / rng) > 0.6)
    df["sp_mess"] = (df["Volume"] > avg_vol * 2) & (long_upper | big_black)

    # 停利 3：止漲訊號（KD 高檔死亡交叉）
    df["sp_kd"] = (
        (df["K"].shift(1) > df["D"].shift(1))
        & (df["K"] < df["D"])
        & (df["K"].shift(1) > 80)
    )

    # 停利 4：固定停利
    df["sp_fixed"] = False
    pct = fixed_pct / 100.0
    in_pos = False
    entry = 0.0
    sp_fixed_col = df.columns.get_loc("sp_fixed")
    for i in range(len(df)):
        if df["buy"].iat[i]:
            in_pos = True
            entry = df["Close"].iat[i]
        if in_pos and df["High"].iat[i] >= entry * (1 + pct):
            df.iat[i, sp_fixed_col] = True
            in_pos = False

    return df


def current_status(df):
    """取得最新一根 K 棒的狀態"""
    r = df.iloc[-1]
    return {
        "close": r["Close"],
        "ma60": r["MA60"],
        "k": r["K"],
        "d": r["D"],
        "above_ma": r["Close"] > r["MA60"],
        "k50": r["K"] > 50,
        "k60": r["K"] > 60,
        "k80": r["K"] > 80,
        "buy_active": r["Close"] > r["MA60"] and r["K"] > 60,
        "sell_active": r["Close"] < r["MA60"] and r["K"] < 50,
    }


def signal_label(s):
    """根據狀態回傳訊號文字"""
    if s["above_ma"] and s["k80"]:
        return "🔥 過熱區"
    if s["buy_active"]:
        return "🟢 買進區"
    if s["above_ma"] and s["k50"]:
        return "🟡 轉強中"
    if s["sell_active"]:
        return "🔴 賣出區"
    if not s["above_ma"] and s["k50"]:
        return "🟠 轉弱中"
    return "⚪ 觀望"
