"""台股法人進出 / 資券變化資料（TWSE / TPEX）"""

import streamlit as st
import pandas as pd
import requests
import twstock
import time
from datetime import datetime, timedelta

_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _is_twse(code):
    """判斷是否為上市股票"""
    info = twstock.codes.get(code)
    if info:
        return info.market == "上市"
    return True


def _roc_date(dt):
    """轉換為民國年格式 YYY/MM/DD"""
    return f"{dt.year - 1911}/{dt.month:02d}/{dt.day:02d}"


def _parse_int(s):
    """解析 TWSE 數字字串 '1,234' → 1234"""
    try:
        return int(str(s).replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return 0


def _recent_weekdays(n=15):
    """取得最近 n 個工作日日期（往前推）"""
    dates = []
    d = datetime.now()
    while len(dates) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            dates.append(d)
    return dates


# ── TWSE API ──

@st.cache_data(ttl=86400, show_spinner=False)
def _twse_t86(date_str):
    """三大法人買賣超日報"""
    url = (f"https://www.twse.com.tw/rwd/zh/fund/T86"
           f"?date={date_str}&selectType=ALL&response=json")
    try:
        r = requests.get(url, headers=_HEADERS, timeout=10)
        j = r.json()
        if j.get("stat") == "OK" and "data" in j:
            return j["data"]
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def _twse_margin(date_str):
    """融資融券餘額"""
    url = (f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
           f"?date={date_str}&selectType=ALL&response=json")
    try:
        r = requests.get(url, headers=_HEADERS, timeout=10)
        j = r.json()
        if j.get("stat") == "OK" and "tables" in j:
            for table in j["tables"]:
                if "data" in table and len(table["data"]) > 10:
                    return table["data"]
    except Exception:
        pass
    return None


# ── TPEX API ──

@st.cache_data(ttl=86400, show_spinner=False)
def _tpex_institutional(roc_date):
    """三大法人買賣超日報（上櫃）"""
    url = (f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/"
           f"3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={roc_date}")
    try:
        r = requests.get(url, headers=_HEADERS, timeout=10)
        j = r.json()
        if "aaData" in j and j["aaData"]:
            return j["aaData"]
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def _tpex_margin(roc_date):
    """融資融券餘額（上櫃）"""
    url = (f"https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/"
           f"margin_bal_result.php?l=zh-tw&o=json&d={roc_date}")
    try:
        r = requests.get(url, headers=_HEADERS, timeout=10)
        j = r.json()
        if "aaData" in j and j["aaData"]:
            return j["aaData"]
    except Exception:
        pass
    return None


# ── Public API ──

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_institutional(code, n_days=5):
    """取得法人進出資料（近 n 個交易日）"""
    is_twse = _is_twse(code)
    dates = _recent_weekdays(n_days * 3)
    rows = []

    for dt in dates:
        if len(rows) >= n_days:
            break

        if is_twse:
            data = _twse_t86(dt.strftime("%Y%m%d"))
        else:
            data = _tpex_institutional(_roc_date(dt))

        if data is None:
            continue

        for row in data:
            if row[0].strip() == code:
                try:
                    if is_twse:
                        # T86: [4]外陸資買賣超 [7]外資自營商買賣超 [10]投信 [11]自營商合計 [18]三大法人
                        foreign = _parse_int(row[4]) + _parse_int(row[7])
                        trust = _parse_int(row[10])
                        dealer = _parse_int(row[11])
                        total = _parse_int(row[18])
                    else:
                        foreign = _parse_int(row[4])
                        trust = _parse_int(row[10])
                        dealer = _parse_int(row[13]) + _parse_int(row[16])
                        total = _parse_int(row[17])
                    rows.append({
                        "日期": f"{dt.month}/{dt.day}",
                        "外資": foreign // 1000,
                        "投信": trust // 1000,
                        "自營商": dealer // 1000,
                        "合計": total // 1000,
                    })
                except (IndexError, ValueError):
                    pass
                break

        time.sleep(0.3)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_margin(code, n_days=5):
    """取得資券變化資料（近 n 個交易日）"""
    is_twse = _is_twse(code)
    dates = _recent_weekdays(n_days * 3)
    rows = []

    for dt in dates:
        if len(rows) >= n_days:
            break

        if is_twse:
            data = _twse_margin(dt.strftime("%Y%m%d"))
        else:
            data = _tpex_margin(_roc_date(dt))

        if data is None:
            continue

        for row in data:
            if row[0].strip() == code:
                try:
                    if is_twse:
                        margin_prev = _parse_int(row[5])
                        margin_bal = _parse_int(row[6])
                        short_prev = _parse_int(row[11])
                        short_bal = _parse_int(row[12])
                        offset = _parse_int(row[14])
                    else:
                        margin_prev = _parse_int(row[2])
                        margin_bal = _parse_int(row[6])
                        short_prev = _parse_int(row[10])
                        short_bal = _parse_int(row[14])
                        offset = _parse_int(row[18])
                    margin_chg = margin_bal - margin_prev
                    short_chg = short_bal - short_prev
                    rows.append({
                        "日期": f"{dt.month}/{dt.day}",
                        "融資餘額": margin_bal,
                        "融資增減": margin_chg,
                        "融券餘額": short_bal,
                        "融券增減": short_chg,
                        "資券互抵": offset,
                    })
                except (IndexError, ValueError):
                    pass
                break

        time.sleep(0.3)

    return pd.DataFrame(rows) if rows else pd.DataFrame()
