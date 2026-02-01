#!/bin/bash
# Weekly Market Report - 環境安裝腳本

set -e

echo "========================================"
echo "📦 Weekly Market Report 環境設定"
echo "========================================"

# 檢查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $PYTHON_VERSION"

# 建立虛擬環境
if [ ! -d "venv" ]; then
    echo ""
    echo "📁 建立虛擬環境..."
    python3 -m venv venv
fi

# 啟動虛擬環境
echo ""
echo "🔌 啟動虛擬環境..."
source venv/bin/activate

# 安裝依賴
echo ""
echo "📥 安裝 Python 依賴..."
pip install --upgrade pip
pip install -r requirements.txt

# 安裝 Playwright 瀏覽器
echo ""
echo "🌐 安裝 Playwright 瀏覽器..."
playwright install chromium

# 複製環境變數範本
if [ ! -f "config/.env" ]; then
    echo ""
    echo "📝 建立環境變數檔案..."
    cp config/.env.example config/.env
    echo "   請編輯 config/.env 填入 API keys"
fi

# 建立資料目錄
echo ""
echo "📂 建立資料目錄..."
mkdir -p data/{raw,processed,archives}

# 安裝 Skills 到 Claude Code
echo ""
echo "🔧 安裝 Claude Code Skills..."
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
if [ -d "$CLAUDE_SKILLS_DIR" ]; then
    cp -v skills/*.md "$CLAUDE_SKILLS_DIR/"
    echo "   Skills 已安裝到 $CLAUDE_SKILLS_DIR"
else
    echo "   ⚠️ Claude Code skills 目錄不存在"
    echo "   請手動複製 skills/*.md 到適當位置"
fi

echo ""
echo "========================================"
echo "✅ 設定完成！"
echo "========================================"
echo ""
echo "下一步："
echo "1. 編輯 config/.env 填入 API keys"
echo "2. 編輯 config/watchlist.yaml 設定觀察清單"
echo "3. 執行 /market-data-fetch 測試資料抓取"
echo ""
