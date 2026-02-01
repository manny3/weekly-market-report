#!/usr/bin/env python3
"""
日報資料抓取腳本
週一至週五執行，抓取前一交易日行情 + 市場新聞
"""
import sys
from datetime import datetime
from pathlib import Path

# 載入環境變數
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "config" / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

# 將 src 加入 path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetchers import (
    YahooFetcher,
    FinMindFetcher,
    FinnhubNewsFetcher,
    CnyesNewsFetcher,
)


def load_watchlist() -> dict:
    """載入觀察清單"""
    import yaml
    config_path = Path(__file__).parent.parent / "config" / "watchlist.yaml"

    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {"us_stocks": {"core": []}, "tw_stocks": {"core": []}}


def main():
    print("=" * 60)
    print("📈 每日市場速報 - 資料抓取")
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 建立輸出目錄 (daily 子目錄)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(__file__).parent.parent / "data" / "raw" / date_str / "daily"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 載入觀察清單
    watchlist = load_watchlist()
    us_symbols = [s['symbol'] for s in watchlist.get('us_stocks', {}).get('core', [])]
    us_symbols += [s['symbol'] for s in watchlist.get('us_stocks', {}).get('swing', [])]
    tw_symbols = [s['symbol'] for s in watchlist.get('tw_stocks', {}).get('core', [])]
    tw_symbols += [s['symbol'] for s in watchlist.get('tw_stocks', {}).get('swing', [])]

    results = {}

    # ========== 美股資料 ==========
    print("\n" + "─" * 40)
    print("📊 美股行情 (前一交易日)")
    print("─" * 40)

    # 1. Yahoo Finance - 指數 + 板塊
    print("\n📊 抓取 Yahoo Finance 資料...")
    try:
        yahoo = YahooFetcher()
        results['yahoo'] = yahoo.fetch_all(us_symbols, output_dir)
        status = "✅ 成功" if results['yahoo'].get('success') else "❌ 失敗"
        print(f"   {status}")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        results['yahoo'] = {"success": False, "error": str(e)}

    # ========== 台股資料 ==========
    print("\n" + "─" * 40)
    print("🇹🇼 台股行情 (前一交易日)")
    print("─" * 40)

    # 2. FinMind - 台股價格 (只需最近 5 天)
    print("\n📊 抓取 FinMind 台股資料...")
    try:
        finmind = FinMindFetcher()
        results['finmind'] = finmind.fetch_all(tw_symbols, output_dir)
        status = "✅ 成功" if results['finmind'].get('success') else "⚠️ 部分成功"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['finmind'] = {"success": False, "error": str(e)}

    # ========== 新聞 ==========
    print("\n" + "─" * 40)
    print("📰 市場新聞")
    print("─" * 40)

    # 3. Finnhub - 美股新聞
    print("\n🇺🇸 抓取美股新聞 (Finnhub)...")
    try:
        finnhub_news = FinnhubNewsFetcher()
        results['finnhub_news'] = finnhub_news.fetch_all(output_dir, count=5)
        status = "✅ 成功" if results['finnhub_news'].get('success') else "❌ 失敗"
        print(f"   {status}")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        results['finnhub_news'] = {"success": False, "error": str(e)}

    # 4. 鉅亨網 - 台股新聞
    print("\n🇹🇼 抓取台股新聞 (鉅亨網)...")
    try:
        cnyes_news = CnyesNewsFetcher()
        results['cnyes_news'] = cnyes_news.fetch_all(output_dir, count=5)
        status = "✅ 成功" if results['cnyes_news'].get('success') else "❌ 失敗"
        print(f"   {status}")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        results['cnyes_news'] = {"success": False, "error": str(e)}

    # ========== 彙總結果 ==========
    print("\n" + "=" * 60)
    print("📋 日報資料抓取結果")
    print("=" * 60)

    success_count = sum(1 for r in results.values() if r.get('success'))
    total_count = len(results)

    print(f"\n成功: {success_count}/{total_count}")
    print(f"輸出目錄: {output_dir}")
    print("\n各資料源狀態:")

    source_labels = {
        'yahoo': '美股行情 (Yahoo)',
        'finmind': '台股行情 (FinMind)',
        'finnhub_news': '美股新聞 (Finnhub)',
        'cnyes_news': '台股新聞 (鉅亨網)',
    }

    for key, label in source_labels.items():
        if key in results:
            icon = "✅" if results[key].get('success') else "❌"
            print(f"  {icon} {label}")

    print("\n" + "=" * 60)
    print(f"⏰ 完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
