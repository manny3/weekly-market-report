"""
個股篩選模組
"""
from pathlib import Path
import json
import yaml


class StockScanner:
    """個股篩選器"""

    def __init__(self, data_dir: Path = None, config_dir: Path = None):
        self.data_dir = data_dir or Path("./data/raw")
        self.config_dir = config_dir or Path("./config")

    def load_watchlist(self) -> dict:
        """載入觀察清單"""
        watchlist_file = self.config_dir / "watchlist.yaml"
        if watchlist_file.exists():
            with open(watchlist_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def load_criteria(self) -> dict:
        """載入篩選條件"""
        watchlist = self.load_watchlist()
        return watchlist.get('screening_criteria', {})

    def scan_us_stocks(self) -> list[dict]:
        """篩選美股"""
        # 載入資料
        dirs = sorted(self.data_dir.glob("*"))
        if not dirs:
            return []

        latest_dir = dirs[-1]
        yahoo_file = latest_dir / "yahoo_data.json"

        if not yahoo_file.exists():
            return []

        with open(yahoo_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        fundamentals = data.get('data', {}).get('fundamentals', {})
        quotes = data.get('data', {}).get('quotes', {})
        criteria = self.load_criteria()

        results = []
        for symbol, fund in fundamentals.items():
            if 'error' in fund:
                continue

            quote = quotes.get(symbol, {})

            # 套用篩選條件
            passed = True
            reasons = []

            # 基本面條件
            if criteria.get('fundamental'):
                pe = fund.get('pe_ratio')
                roe = fund.get('roe')
                rev_growth = fund.get('revenue_growth')

                if pe and criteria['fundamental'].get('max_pe_ratio'):
                    if pe > criteria['fundamental']['max_pe_ratio']:
                        passed = False
                        reasons.append(f"PE {pe:.1f} > {criteria['fundamental']['max_pe_ratio']}")

                if roe and criteria['fundamental'].get('min_roe'):
                    if roe * 100 < criteria['fundamental']['min_roe']:
                        passed = False
                        reasons.append(f"ROE {roe*100:.1f}% < {criteria['fundamental']['min_roe']}%")

            if passed:
                results.append({
                    "symbol": symbol,
                    "name": fund.get('name', ''),
                    "price": quote.get('price'),
                    "change_pct": quote.get('change_pct'),
                    "pe_ratio": fund.get('pe_ratio'),
                    "roe": fund.get('roe'),
                    "revenue_growth": fund.get('revenue_growth'),
                })

        return results

    def generate_watchlist_summary(self) -> str:
        """產生觀察清單摘要"""
        watchlist = self.load_watchlist()
        scanned = self.scan_us_stocks()

        lines = ["📋 觀察清單", ""]

        # 美股
        lines.append("【美股】")
        us_stocks = watchlist.get('us_stocks', {})
        for category in ['core', 'swing']:
            stocks = us_stocks.get(category, [])
            if stocks:
                lines.append(f"\n{category.upper()}:")
                for stock in stocks:
                    symbol = stock.get('symbol')
                    notes = stock.get('notes', '')
                    # 找對應的掃描結果
                    scan_data = next((s for s in scanned if s['symbol'] == symbol), None)
                    if scan_data:
                        price = scan_data.get('price', 'N/A')
                        change = scan_data.get('change_pct', 0) or 0
                        lines.append(f"  • {symbol}: ${price} ({change:+.2f}%) - {notes}")
                    else:
                        lines.append(f"  • {symbol}: - {notes}")

        return "\n".join(lines)
