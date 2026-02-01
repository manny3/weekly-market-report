# Weekly Market Report System

每週市場分析報告自動化系統 - 台股 & 美股

## 功能

- 📊 **自動資料抓取**：整合 Yahoo Finance、FinMind、Finnhub、Goodinfo、Finviz、TradingView
- 📈 **多維度分析**：大盤趨勢、板塊輪動、產業強弱、營收亮點、經濟日曆
- 📝 **智能報告產出**：AI 協助分析，人工審核確認
- 🚀 **社群自動發布**：透過 Playwright MCP 發布到 Threads 和 X (Twitter)

## 系統需求

### 最低需求

| 項目 | 需求 |
|------|------|
| Python | 3.11+ |
| 記憶體 | 8GB (建議 16GB) |
| 磁碟空間 | 1GB |
| 網路 | 穩定連線 |

### 作業系統相容性

| 系統 | 狀態 | 備註 |
|------|------|------|
| macOS 13+ (Ventura) | ✅ 完整支援 | 推薦 |
| macOS 12 (Monterey) | ✅ 支援 | 見下方注意事項 |
| macOS 11 (Big Sur) | ⚠️ 未測試 | 應可運行 |
| Ubuntu 22.04+ | ✅ 支援 | |
| Windows 10/11 | ⚠️ 部分支援 | Futu API 需調整 |

### macOS 12 Monterey 注意事項

適用於 MacBook Pro 2015 等只能升級到 macOS 12 的機型：

1. **Playwright WebKit 限制**
   - Playwright v1.45 是最後支援 macOS 12 WebKit 的版本
   - 本專案使用 Chromium，不受影響
   - 建議鎖定版本：`playwright>=1.40.0,<1.50.0`

2. **記憶體使用**
   - 8GB RAM 較緊，建議發布時關閉其他應用程式
   - 16GB RAM 可順暢運行

3. **長期維護**
   - macOS 12 已進入延長支援期
   - 短期內（1-2 年）所有套件仍相容

## 快速開始

### 1. 環境設定

```bash
# 使用 Homebrew 安裝 Python 3.11
brew install python@3.11

# 或使用 pyenv
brew install pyenv
pyenv install 3.11.4
```

### 2. 安裝專案

```bash
# Clone 專案
git clone https://github.com/yourusername/weekly-market-report.git
cd weekly-market-report

# 建立虛擬環境
python3.11 -m venv venv
source venv/bin/activate

# 更新 pip 並安裝依賴
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 安裝 Playwright 瀏覽器
playwright install chromium
```

### 3. 設定環境變數

```bash
# 複製範本
cp config/.env.example config/.env

# 編輯 .env 填入 API keys
```

### 4. 安裝 Claude Code Skills (選用)

```bash
cp skills/*.md ~/.claude/skills/
```

## 使用方式

### Claude Code Skills

| 指令 | 功能 | 執行時機 |
|------|------|----------|
| `/market-data-fetch` | 抓取所有市場資料 | 週六晚 / 週日早 |
| `/weekly-report` | 產出週報 + 發布社群 | 週日下午 |
| `/trade-plan` | 規劃交易計畫 | 需要時 |

### 手動執行

```bash
# 啟動虛擬環境
source venv/bin/activate

# 抓取資料
python scripts/fetch_all.py

# 資料會存放在 data/raw/{日期}/ 目錄
```

## 資料夾結構

```
weekly-market-report/
├── config/              # 設定檔
│   ├── .env.example     # 環境變數範本
│   ├── config.yaml      # 主設定檔
│   └── watchlist.yaml   # 觀察清單
├── src/
│   ├── fetchers/        # 資料抓取模組 (10 個)
│   ├── analyzers/       # 分析模組
│   ├── publishers/      # 發布模組 (Notion, Threads, X)
│   ├── templates/       # 輸出模板
│   └── utils/           # 工具函數
├── data/
│   ├── raw/             # 原始資料 (按日期)
│   ├── processed/       # 處理後資料
│   └── archives/        # 歷史存檔
├── skills/              # Claude Code Skills
├── scripts/             # 執行腳本
└── tests/               # 測試
```

## 資料來源

| 來源 | 資料類型 | 需要 API Key |
|------|----------|--------------|
| Yahoo Finance | 美股指數、板塊、個股 | 否 |
| FinMind | 台股行情、營收、產業 | 是 (免費) |
| Finnhub | 經濟日曆 (Fed, CPI, PMI) | 是 (免費) |
| Goodinfo | 台股基本面 | 否 |
| Finviz | 美股篩選器 | 否 |
| TradingView | 圖表截圖 | 否 (選用登入) |
| Futu OpenD | 即時報價 | 選用 |

## 社群發布

本專案使用 **Playwright MCP 瀏覽器自動化** 進行社群發布：

### X (Twitter)

- 使用 Playwright 操作瀏覽器（X API v2 需付費）
- 支援串推：透過 compose dialog「加入貼文」功能
- 憑證：`.env` 中的 `X_USERNAME` / `X_PASSWORD`

### Threads

- 必須透過 Instagram OAuth 登入
- 流程：threads.com → 點擊「使用 Instagram 帳號繼續」→ IG 登入
- 憑證：`.env` 中的 `THREADS_USERNAME` / `THREADS_PASSWORD`（Instagram 帳密）

## API Keys 申請

| 服務 | 申請網址 | 備註 |
|------|----------|------|
| Finnhub | https://finnhub.io/ | 免費 60 calls/min |
| FinMind | https://finmindtrade.com/ | 免費註冊 |
| Notion | https://developers.notion.com/ | 需建立 Integration |
| Futu OpenD | https://www.futunn.com/download/OpenAPI | 選用 |

## 常見問題

### Q: Playwright 安裝失敗？

```bash
# 確保有安裝 Chromium
playwright install chromium

# macOS 可能需要
xcode-select --install
```

### Q: 發布到 Threads 顯示「密碼錯誤」？

Threads 不支援直接登入，必須點擊「使用 Instagram 帳號繼續」進行 OAuth 登入。

### Q: 發布到 X 按鈕被擋住？

使用 JavaScript 強制點擊：
```javascript
document.querySelector('[data-testid="tweetButton"]').click()
```

### Q: 8GB RAM 夠用嗎？

可以運行，但建議：
- 發布時關閉其他應用程式
- 避免同時開多個瀏覽器實例

## 開發

```bash
# 執行測試
pytest tests/

# 程式碼格式化
black src/
```

## License

MIT

## 免責聲明

⚠️ 本系統產出之內容為個人分析筆記，非投資建議。投資有風險，請自行評估。
