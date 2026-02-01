#!/usr/bin/env python3
"""
一鍵抓取所有市場資料
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
    pass  # dotenv 未安裝時跳過

# 將 src 加入 path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetchers import (
    YahooFetcher,
    TradingViewFetcher,
    GoodinfoFetcher,
    CMoneyFetcher,
    FinvizFetcher,
    FinMindFetcher,
    EconomicCalendarFetcher,
    TwIndustryFetcher,
    RevenueHighlightsFetcher,
)

# 嘗試載入 Futu (可選)
try:
    from fetchers import FutuFetcher
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False


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
    print("📥 週報資料抓取")
    print(f"⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 建立輸出目錄
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(__file__).parent.parent / "data" / "raw" / date_str
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
    print("📊 美股資料")
    print("─" * 40)

    # 1. Yahoo Finance (美股)
    print("\n📊 抓取 Yahoo Finance 資料...")
    try:
        yahoo = YahooFetcher()
        results['yahoo'] = yahoo.fetch_all(us_symbols, output_dir)
        status = "✅ 成功" if results['yahoo'].get('success') else "❌ 失敗"
        print(f"   {status}")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")
        results['yahoo'] = {"success": False, "error": str(e)}

    # 2. Futu (如有)
    if FUTU_AVAILABLE:
        print("\n📈 抓取 Futu 資料...")
        try:
            futu = FutuFetcher()
            futu_symbols = [f"US.{s}" for s in us_symbols]
            results['futu'] = futu.fetch_all(futu_symbols, output_dir)
            status = "✅ 成功" if results['futu'].get('success') else "⚠️ 未連接"
            print(f"   {status}")
        except Exception as e:
            print(f"   ⚠️ 跳過 (OpenD 未運行)")
            results['futu'] = {"success": False, "error": str(e)}

    # 3. TradingView 截圖
    print("\n📸 抓取 TradingView 圖表...")
    try:
        tv = TradingViewFetcher()
        results['tradingview'] = tv.fetch_all(output_dir)
        status = "✅ 成功" if results['tradingview'].get('success') else "⚠️ 部分成功"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['tradingview'] = {"success": False, "error": str(e)}

    # 4. Finviz (美股篩選)
    print("\n🔍 抓取 Finviz 資料...")
    try:
        finviz = FinvizFetcher()
        results['finviz'] = finviz.fetch_all(output_dir)
        status = "✅ 成功" if results['finviz'].get('success') else "⚠️ 部分成功"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['finviz'] = {"success": False, "error": str(e)}

    # ========== 總經事件 ==========
    print("\n" + "─" * 40)
    print("🌍 總經事件")
    print("─" * 40)

    # 5. Finnhub 經濟日曆
    print("\n📅 抓取經濟日曆...")
    try:
        econ = EconomicCalendarFetcher()
        results['economic_calendar'] = econ.fetch_all(output_dir)
        status = "✅ 成功" if results['economic_calendar'].get('success') else "⚠️ 跳過"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['economic_calendar'] = {"success": False, "error": str(e)}

    # ========== 台股資料 ==========
    print("\n" + "─" * 40)
    print("🇹🇼 台股資料")
    print("─" * 40)

    # 6. FinMind API (台股主要資料源 - 價格、法人、融資券)
    print("\n📊 抓取 FinMind 台股資料...")
    try:
        finmind = FinMindFetcher()
        results['finmind'] = finmind.fetch_all(tw_symbols, output_dir)
        status = "✅ 成功" if results['finmind'].get('success') else "⚠️ 部分成功"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['finmind'] = {"success": False, "error": str(e)}

    # 7. Goodinfo (台股基本面補充)
    print("\n📈 抓取 Goodinfo 台股資料...")
    try:
        goodinfo = GoodinfoFetcher()
        results['goodinfo'] = goodinfo.fetch_all(tw_symbols, output_dir)
        status = "✅ 成功" if results['goodinfo'].get('success') else "⚠️ 部分成功"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['goodinfo'] = {"success": False, "error": str(e)}

    # 8. CMoney/FinMind (台股籌碼)
    print("\n💰 抓取 CMoney/FinMind 籌碼資料...")
    try:
        cmoney = CMoneyFetcher()
        results['cmoney'] = cmoney.fetch_all(tw_symbols, output_dir)
        status = "✅ 成功" if results['cmoney'].get('success') else "⚠️ 部分成功"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['cmoney'] = {"success": False, "error": str(e)}

    # 9. 台股產業族群表現
    print("\n🏭 分析台股產業族群...")
    try:
        industry = TwIndustryFetcher()
        results['tw_industry'] = industry.fetch_all(output_dir)
        status = "✅ 成功" if results['tw_industry'].get('success') else "⚠️ 部分成功"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['tw_industry'] = {"success": False, "error": str(e)}

    # 10. 營收亮點
    print("\n💹 偵測營收亮點...")
    try:
        revenue = RevenueHighlightsFetcher()
        results['tw_revenue'] = revenue.fetch_all(tw_symbols, output_dir)
        status = "✅ 成功" if results['tw_revenue'].get('success') else "⚠️ 部分成功"
        print(f"   {status}")
    except Exception as e:
        print(f"   ⚠️ 跳過: {e}")
        results['tw_revenue'] = {"success": False, "error": str(e)}

    # ========== 彙總結果 ==========
    print("\n" + "=" * 60)
    print("📋 抓取結果彙總")
    print("=" * 60)

    success_count = sum(1 for r in results.values() if r.get('success'))
    total_count = len(results)

    print(f"\n成功: {success_count}/{total_count}")
    print(f"輸出目錄: {output_dir}")
    print("\n各資料源狀態:")

    # 分類顯示
    us_sources = ['yahoo', 'futu', 'tradingview', 'finviz']
    macro_sources = ['economic_calendar']
    tw_sources = ['finmind', 'goodinfo', 'cmoney', 'tw_industry', 'tw_revenue']

    print("\n  美股:")
    for source in us_sources:
        if source in results:
            icon = "✅" if results[source].get('success') else "❌"
            print(f"    {icon} {source}")

    print("\n  總經:")
    for source in macro_sources:
        if source in results:
            icon = "✅" if results[source].get('success') else "❌"
            print(f"    {icon} {source}")

    print("\n  台股:")
    for source in tw_sources:
        if source in results:
            icon = "✅" if results[source].get('success') else "❌"
            print(f"    {icon} {source}")

    print("\n" + "=" * 60)
    print(f"⏰ 完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
