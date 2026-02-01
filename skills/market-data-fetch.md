---
name: market-data-fetch
description: 抓取台股與美股市場資料，為週報做準備
---

# 市場資料抓取

你是週報系統的資料抓取助手。執行此 skill 時，請依照以下步驟操作：

## 執行步驟

### 1. 確認執行時機
```
現在是適合抓取資料的時間嗎？
- 美股：週五收盤後 (台灣週六早上) 最佳
- 台股：週五收盤後
```

### 2. 執行資料抓取腳本
```bash
cd ~/weekly-market-report
python scripts/fetch_all.py
```

### 3. 檢查抓取結果
- 確認 `data/raw/{日期}/` 目錄已建立
- 檢查各資料檔案是否存在且有內容：
  - `yahoo_data.json` - 美股指數與板塊
  - `futu_data.json` - 即時報價 (如有連接 OpenD)
  - `goodinfo_data.json` - 台股基本面
  - `tradingview_metadata.json` - 圖表截圖

### 4. 回報結果

向使用者回報：
```
📥 資料抓取完成

時間：{抓取時間}
狀態：
✅ Yahoo Finance - 美股指數、板塊、個股
✅ TradingView - 圖表截圖 {N} 張
⚠️ Goodinfo - 台股資料 (部分成功)
❌ Futu - 未連接 OpenD

下一步：週日下午使用 /weekly-report 產出週報
```

## 錯誤處理

如果抓取失敗：
1. 檢查網路連線
2. 確認 API key 設定正確 (`config/.env`)
3. 個別重試失敗的資料源

## 相關 Skills
- `/weekly-report` - 產出週報
- `/trade-plan` - 交易計畫
