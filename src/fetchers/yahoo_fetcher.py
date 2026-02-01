"""
Yahoo Finance 資料抓取模組 (使用 yfinance)
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class YahooFetcher:
    """Yahoo Finance 資料抓取器"""

    # 美股三大指數
    US_INDICES = {
        '^GSPC': 'S&P 500',
        '^IXIC': 'NASDAQ',
        '^DJI': 'Dow Jones',
    }

    # 美股板塊 ETF
    SECTOR_ETFS = {
        'XLK': 'Technology',
        'XLF': 'Financial',
        'XLE': 'Energy',
        'XLV': 'Healthcare',
        'XLI': 'Industrial',
        'XLC': 'Communication',
        'XLY': 'Consumer Discretionary',
        'XLP': 'Consumer Staples',
        'XLU': 'Utilities',
        'XLRE': 'Real Estate',
        'XLB': 'Materials',
    }

    def __init__(self):
        if not YFINANCE_AVAILABLE:
            print("[Yahoo] yfinance 未安裝，請執行 pip install yfinance")

    def get_quote(self, symbol: str) -> dict:
        """取得股票即時報價"""
        if not YFINANCE_AVAILABLE:
            return {"error": "yfinance 未安裝"}

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                "symbol": symbol,
                "name": info.get('shortName', ''),
                "price": info.get('regularMarketPrice'),
                "change": info.get('regularMarketChange'),
                "change_pct": info.get('regularMarketChangePercent'),
                "volume": info.get('regularMarketVolume'),
                "market_cap": info.get('marketCap'),
                "pe_ratio": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "dividend_yield": info.get('dividendYield'),
                "52w_high": info.get('fiftyTwoWeekHigh'),
                "52w_low": info.get('fiftyTwoWeekLow'),
            }
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

    def get_history(
        self,
        symbol: str,
        period: str = "3mo",
        interval: str = "1d"
    ) -> list[dict]:
        """
        取得歷史價格

        Args:
            symbol: 股票代碼
            period: 期間 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 間隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            list[dict]: 歷史價格列表
        """
        if not YFINANCE_AVAILABLE:
            return []

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            df = df.reset_index()
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            return df.to_dict('records')
        except Exception as e:
            return [{"error": str(e)}]

    def get_us_indices(self) -> dict:
        """取得美股三大指數"""
        result = {}
        for symbol, name in self.US_INDICES.items():
            data = self.get_quote(symbol)
            data['index_name'] = name
            result[symbol] = data
        return result

    def get_sector_performance(self) -> dict:
        """取得板塊表現"""
        result = {}
        for symbol, name in self.SECTOR_ETFS.items():
            data = self.get_quote(symbol)
            data['sector_name'] = name
            result[symbol] = data

        # 按漲跌幅排序
        sorted_sectors = sorted(
            result.items(),
            key=lambda x: x[1].get('change_pct', 0) or 0,
            reverse=True
        )
        return dict(sorted_sectors)

    def get_stock_fundamentals(self, symbol: str) -> dict:
        """取得股票基本面數據"""
        if not YFINANCE_AVAILABLE:
            return {"error": "yfinance 未安裝"}

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,
                "name": info.get('shortName', ''),
                # 估值指標
                "pe_ratio": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "peg_ratio": info.get('pegRatio'),
                "pb_ratio": info.get('priceToBook'),
                "ps_ratio": info.get('priceToSalesTrailing12Months'),
                # 獲利能力
                "profit_margin": info.get('profitMargins'),
                "operating_margin": info.get('operatingMargins'),
                "roe": info.get('returnOnEquity'),
                "roa": info.get('returnOnAssets'),
                # 成長指標
                "revenue_growth": info.get('revenueGrowth'),
                "earnings_growth": info.get('earningsGrowth'),
                # 股息
                "dividend_yield": info.get('dividendYield'),
                "payout_ratio": info.get('payoutRatio'),
                # 其他
                "beta": info.get('beta'),
                "market_cap": info.get('marketCap'),
            }
        except Exception as e:
            return {"symbol": symbol, "error": str(e)}

    def fetch_all(self, symbols: list[str], output_dir: Path) -> dict:
        """
        抓取所有資料並儲存

        Args:
            symbols: 股票代碼列表
            output_dir: 輸出目錄

        Returns:
            dict: 抓取結果摘要
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "yahoo_finance",
            "success": False,
            "data": {}
        }

        try:
            # 美股指數
            result["data"]["us_indices"] = self.get_us_indices()

            # 板塊表現
            result["data"]["sectors"] = self.get_sector_performance()

            # 個股報價
            result["data"]["quotes"] = {}
            for symbol in symbols:
                result["data"]["quotes"][symbol] = self.get_quote(symbol)

            # 個股基本面
            result["data"]["fundamentals"] = {}
            for symbol in symbols:
                result["data"]["fundamentals"][symbol] = self.get_stock_fundamentals(symbol)

            # 個股歷史價格
            result["data"]["history"] = {}
            for symbol in symbols:
                result["data"]["history"][symbol] = self.get_history(symbol, "3mo", "1d")

            result["success"] = True

            # 儲存到檔案
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "yahoo_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    # 測試用
    fetcher = YahooFetcher()

    # 測試取得指數
    print("=== US Indices ===")
    print(json.dumps(fetcher.get_us_indices(), indent=2))

    # 測試板塊表現
    print("\n=== Sector Performance ===")
    sectors = fetcher.get_sector_performance()
    for symbol, data in sectors.items():
        print(f"{data.get('sector_name')}: {data.get('change_pct', 0):.2f}%")
