# 股票分析系統

台股 / 美股技術分析工具，基於 60 分鐘 K 線 + 60MA + KD(60,3,3) 策略，提供買賣訊號判斷與庫存管理。

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)

## 功能

### 自選股總覽
- 分組管理股票清單（新增 / 移除 / 群組分類）
- 一覽所有自選股的現價、60MA、KD 值與訊號狀態

### 個股技術分析
- 60 分鐘 K 線圖 + 60MA 均線
- KD(60,3,3) 隨機指標（台灣慣用算法）
- 自動標記買賣訊號與四大停利訊號
- 可調整資料期間（1 / 3 / 6 個月）與固定停利目標

### 訊號判斷邏輯

| 訊號 | 條件 |
|------|------|
| 🟢 買進區 | 股價 > 60MA 且 K > 60 |
| 🟡 轉強中 | 股價 > 60MA 且 K > 50（但 K ≤ 60） |
| ⚪ 觀望 | 股價 > 60MA 且 K ≤ 50 |
| 🟠 轉弱中 | 股價 < 60MA 且 K ≥ 50 |
| 🔴 賣出區 | 股價 < 60MA 且 K < 50 |

### 四大停利
1. **固定停利** — 達到自訂獲利百分比
2. **止漲訊號** — KD 高檔死亡交叉（K > 80 後 K 跌破 D）
3. **籌碼凌亂換標的** — 爆量長上影線 / 爆量長黑 K
4. **跌破 60MA** — 股價跌破 60 分鐘線均線

### 庫存管理
- 輸入持股數量與成本均，自動計算損平價（含賣出手續費 0.1425% + 證交稅 0.3%）
- 即時抓取現價，顯示損益與報酬率
- 支援從自選股清單快速新增

## 安裝與執行

```bash
# 安裝依賴
pip install streamlit yfinance pandas numpy plotly twstock

# 啟動
streamlit run app.py
```

## 專案結構

```
├── app.py                 # 入口：市場切換（台股/美股/庫存）
├── core/
│   ├── analysis.py        # KD 計算、買賣訊號、停利訊號
│   ├── chart.py           # Plotly K 線圖 + KD 圖
│   ├── data.py            # 行情抓取、股票名稱查詢、清單 I/O
│   ├── page.py            # 共用頁面渲染器（自選股 + 個股分析）
│   └── portfolio.py       # 庫存管理（損平價自動計算）
├── stocks_tw.json         # 台股自選股清單
├── stocks_us.json         # 美股自選股清單
└── 進場與停利策略.md       # 策略說明文件
```

## 股票種類

| | 台股 | 美股 | 加密貨幣 |
|--|------|------|------|
| K 線顏色 | 紅漲綠跌 | 綠漲紅跌 | 🚧 Under Construction |
| 股票名稱 | twstock 本地資料庫 | yfinance API | 🚧 Under Construction |
| 代碼格式 | 數字（如 2330） | 英文（如 NVDA） | 🚧 Under Construction |
| 損平價手續費 | 手續費 + 證交稅 | （沒在玩美股，可以給點建議） | 🚧 Under Construction |
