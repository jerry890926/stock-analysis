"""資料存取：股票清單 I/O、行情抓取、名稱查詢"""

import json
from pathlib import Path

import streamlit as st
import yfinance as yf
import pandas as pd
import twstock


# ═══════════════════════════════════════════════════════════
# 股票清單 I/O
# ═══════════════════════════════════════════════════════════

def load_watchlist(filepath):
    """載入分組股票清單"""
    filepath = Path(filepath)
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_watchlist(filepath, data):
    """儲存分組股票清單"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_codes(data):
    """取得所有不重複的股票代碼"""
    seen = set()
    result = []
    for codes in data.values():
        for c in codes:
            if c not in seen:
                seen.add(c)
                result.append(c)
    return result


# ═══════════════════════════════════════════════════════════
# 台股
# ═══════════════════════════════════════════════════════════

def fetch_name_tw(code):
    """取得台灣股票中文名稱（twstock 本地資料庫）"""
    info = twstock.codes.get(code)
    return info.name if info else code


def validate_tw(code):
    """驗證台股代碼是否存在"""
    return twstock.codes.get(code) is not None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_tw(code, period="3mo"):
    """取得台股 60 分鐘 K 線（自動嘗試上市 .TW / 上櫃 .TWO）"""
    for sfx in (".TW", ".TWO"):
        try:
            t = yf.Ticker(f"{code}{sfx}")
            df = t.history(period=period, interval="60m")
            if not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════
# 美股
# ═══════════════════════════════════════════════════════════

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_name_us(code):
    """取得美股名稱（yfinance，快取 24 小時）"""
    try:
        info = yf.Ticker(code).info
        return info.get("shortName", info.get("longName", code))
    except Exception:
        return code


def validate_us(code):
    """簡易驗證美股代碼格式"""
    return bool(code) and len(code) <= 10


@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_us(code, period="3mo"):
    """取得美股 60 分鐘 K 線"""
    try:
        t = yf.Ticker(code)
        df = t.history(period=period, interval="60m")
        if not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()
